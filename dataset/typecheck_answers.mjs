#!/usr/bin/env node
/**
 * Type-checks TypeScript snippets in isolation with the compiler from cli/node_modules.
 *
 * stdin : JSON array of {"id": string, "code": string}
 * stdout: JSON array of {"id", "syntaxErrors", "typeErrors", "codes"}
 *
 * Snippets are fragments, so diagnostics about unresolved modules and names
 * (missing imports, test globals, other files) are ignored, imports are
 * blanked, and implicit-any on callback parameters passed to a call is ignored
 * (real library typings would type them). Everything else under
 * `strict: true` counts as a type error.
 */
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(here, "..", "cli", "package.json"));

let ts;
try {
  ts = require("typescript");
} catch {
  process.stderr.write("typescript not found: run `pnpm install` in cli/\n");
  process.exit(2);
}

// Cannot find name / module / namespace, missing test or node typings.
export const IGNORED_CODES = new Set([2304, 2307, 2503, 2552, 2580, 2582, 2591, 2593, 2792, 2875, 7016]);

const OPTIONS = {
  strict: true,
  noEmit: true,
  target: ts.ScriptTarget.ES2022,
  module: ts.ModuleKind.ESNext,
  lib: ["lib.es2022.d.ts", "lib.dom.d.ts"],
  skipLibCheck: true,
  types: [],
  experimentalDecorators: true,
};

/**
 * Blanks out import declarations and `export ... from` re-exports.
 * Answers often hold several files in one block that import each other; the
 * imports cannot be resolved here and would collide with the local declarations.
 * Names declared in the snippet still resolve; external ones become ignored
 * "cannot find name" diagnostics. An imported name that matches a lib global
 * (Express `Request`/`Response`, NestJS `Body`) would silently resolve to the
 * DOM type instead, so it is shadowed with an untyped local declaration.
 * Newlines are kept so positions stay stable.
 */
export function stripImports(code) {
  const sf = ts.createSourceFile("strip.ts", code, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  let out = code;
  const ranges = sf.statements
    .filter(
      (s) =>
        ts.isImportDeclaration(s) ||
        ts.isImportEqualsDeclaration(s) ||
        (ts.isExportDeclaration(s) && s.moduleSpecifier !== undefined)
    )
    .map((s) => [s.getStart(sf), s.getEnd()])
    .reverse();
  for (const [start, end] of ranges) {
    out = out.slice(0, start) + out.slice(start, end).replace(/[^\n]/g, " ") + out.slice(end);
  }
  const local = new Set(sf.statements.flatMap(declaredNames));
  const shadows = [...importedNames(sf)]
    .filter((name) => !local.has(name) && libGlobals().has(name))
    .map((name) => `type ${name}<A = any, B = any, C = any, D = any> = any;\ndeclare const ${name}: any;\n`);
  // Keep the snippet a module so top-level names do not merge with globals.
  return out + "\n" + shadows.join("") + "export {};\n";
}

/** Names brought in by import declarations (default, named, namespace, import =). */
function importedNames(sf) {
  const names = new Set();
  for (const s of sf.statements) {
    if (ts.isImportEqualsDeclaration(s)) names.add(s.name.text);
    if (!ts.isImportDeclaration(s) || !s.importClause) continue;
    const clause = s.importClause;
    if (clause.name) names.add(clause.name.text);
    const bindings = clause.namedBindings;
    if (bindings && ts.isNamespaceImport(bindings)) names.add(bindings.name.text);
    if (bindings && ts.isNamedImports(bindings)) for (const el of bindings.elements) names.add(el.name.text);
  }
  return names;
}

/** Top-level names a statement declares (its own sibling "files" in the same block). */
function declaredNames(s) {
  if (ts.isVariableStatement(s)) {
    return s.declarationList.declarations.flatMap((d) => (ts.isIdentifier(d.name) ? [d.name.text] : []));
  }
  return s.name && ts.isIdentifier(s.name) ? [s.name.text] : [];
}

let LIB_GLOBALS;
/** Global value and type names visible to a snippet (lib.es2022 + lib.dom), computed once. */
function libGlobals() {
  if (LIB_GLOBALS) return LIB_GLOBALS;
  const fileName = "/virtual/globals.ts";
  const host = ts.createCompilerHost(OPTIONS);
  const baseGetSourceFile = host.getSourceFile;
  host.getSourceFile = (f, lang) => (f === fileName ? ts.createSourceFile(f, "export {};", lang, true) : baseGetSourceFile(f, lang));
  const program = ts.createProgram([fileName], OPTIONS, host);
  const checker = program.getTypeChecker();
  const sf = program.getSourceFile(fileName);
  const flags = ts.SymbolFlags.Value | ts.SymbolFlags.Type;
  LIB_GLOBALS = new Set(checker.getSymbolsInScope(sf, flags).map((sym) => sym.name));
  return LIB_GLOBALS;
}

// "Parameter implicitly has an 'any' type" / same for binding elements.
const IMPLICIT_ANY_PARAM = new Set([7006, 7031]);

/**
 * True when an implicit-any diagnostic sits on a parameter of a callback passed
 * as a call argument (e.g. `app.put('/x', (req, res) => ...)`). With real
 * library typings those parameters are contextually typed; here the callee is
 * unresolved, so the diagnostic says nothing about the snippet itself.
 */
function isCallbackParameter(sourceFile, position) {
  let node = findNode(sourceFile, position);
  while (node && !ts.isParameter(node)) node = node.parent;
  const fn = node?.parent;
  if (!fn || !(ts.isArrowFunction(fn) || ts.isFunctionExpression(fn))) return false;
  let outer = fn.parent;
  while (outer && ts.isParenthesizedExpression(outer)) outer = outer.parent;
  return !!outer && (ts.isCallExpression(outer) || ts.isNewExpression(outer)) && outer.arguments?.includes(fn);
}

function findNode(node, position) {
  for (const child of node.getChildren()) {
    if (child.getStart() <= position && position < child.getEnd()) return findNode(child, position);
  }
  return node;
}

// Parsed lib.*.d.ts files, shared by every snippet: parsing them dominates run time.
const LIB_CACHE = new Map();

function check(id, rawCode) {
  const code = stripImports(rawCode);
  const fileName = `/virtual/snippet_${id}.ts`;
  const host = ts.createCompilerHost(OPTIONS);
  const baseGetSourceFile = host.getSourceFile;
  host.getSourceFile = (f, lang) => {
    if (f === fileName) return ts.createSourceFile(f, code, lang, true);
    if (!LIB_CACHE.has(f)) LIB_CACHE.set(f, baseGetSourceFile(f, lang));
    return LIB_CACHE.get(f);
  };
  const baseFileExists = host.fileExists;
  host.fileExists = (f) => f === fileName || baseFileExists(f);
  const baseReadFile = host.readFile;
  host.readFile = (f) => (f === fileName ? code : baseReadFile(f));

  const program = ts.createProgram([fileName], OPTIONS, host);
  const syntax = program.getSyntacticDiagnostics();
  const semantic = program
    .getSemanticDiagnostics()
    .filter((d) => d.file && d.file.fileName === fileName && !IGNORED_CODES.has(d.code))
    .filter((d) => !(IMPLICIT_ANY_PARAM.has(d.code) && isCallbackParameter(d.file, d.start)));
  return {
    id,
    syntaxErrors: syntax.length,
    typeErrors: semantic.length,
    codes: [...new Set([...syntax, ...semantic].map((d) => d.code))].sort((a, b) => a - b),
  };
}

const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const items = JSON.parse(Buffer.concat(chunks).toString("utf-8") || "[]");
process.stdout.write(JSON.stringify(items.map((it) => check(String(it.id), String(it.code)))));
