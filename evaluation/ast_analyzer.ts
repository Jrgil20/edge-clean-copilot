/**
 * Deterministic AST Analyzer for Clean Architecture Score (CAS)
 *
 * Uses the official TypeScript Compiler API to inspect generated code.
 * Replaces heuristic regular expressions with precise syntax tree traversal:
 * 1. Domain Boundary (30 pts): Traverses ImportDeclaration nodes for prohibited modules.
 * 2. Invariant Safety (25 pts): Inspects ConstructorDeclaration nodes for defensive guard clauses & throw/result.
 * 3. Ports & Decoupling (25 pts): Identifies InterfaceDeclaration & TypeAliasDeclaration contracts.
 * 4. TypeScript Rigor (20 pts): Exact count of AnyKeyword tokens (immune to strings & comments).
 */

import ts from "typescript";

export interface AstMetrics {
  domainBoundaryScore: number; // 0.0 to 30.0
  prohibitedImports: string[];
  hasConstructorGuards: boolean;
  invariantScore: number; // 0.0 to 25.0
  portsScore: number; // 0.0 to 25.0
  declaredContracts: string[];
  anyOccurrences: number;
  typingScore: number; // 0.0 to 20.0
  compositeScore: number; // 0.0 to 100.0
  parseErrors: string[];
}

export interface AnalysisInput {
  id?: string;
  code: string;
}

export interface AnalysisOutput {
  id?: string;
  metrics: AstMetrics;
}

const PROHIBITED_MODULES: readonly string[] = [
  "express",
  "fastapi",
  "typeorm",
  "prisma",
  "@prisma/client",
  "axios",
  "mongoose",
  "sqlalchemy",
  "sqlite3",
  "pg",
  "mysql",
  "mysql2",
  "flask",
  "django",
  "node-fetch",
  "got",
  "superagent",
  "mongodb",
  "ioredis",
  "redis",
];

/**
 * Extracts pure code blocks from Markdown if wrapped in ```typescript or ```ts
 */
export function extractCodeBlock(rawText: string): string {
  const codeBlockRegex = /```(?:typescript|ts)?\s*([\s\S]*?)```/gi;
  const matches: string[] = [];
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(rawText)) !== null) {
    if (match[1]?.trim()) {
      matches.push(match[1].trim());
    }
  }

  if (matches.length > 0) {
    return matches.join("\n\n");
  }
  return rawText;
}

/**
 * Analyzes a TypeScript code fragment using the TypeScript Compiler AST.
 */
export function analyzeCode(rawCode: string): AstMetrics {
  const code = extractCodeBlock(rawCode);
  const sourceFile = ts.createSourceFile(
    "evaluation_sample.ts",
    code,
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS
  );

  const prohibitedFound: string[] = [];
  const declaredContracts: string[] = [];
  let anyCount = 0;
  let hasConstructor = false;
  let hasGuardClause = false;
  let hasResultReturn = false;
  let hasCustomError = false;

  function visit(node: ts.Node): void {
    // 1. Domain Boundary: Check ImportDeclaration
    if (ts.isImportDeclaration(node)) {
      if (ts.isStringLiteral(node.moduleSpecifier)) {
        const moduleName = node.moduleSpecifier.text.toLowerCase();
        for (const prohibited of PROHIBITED_MODULES) {
          if (moduleName === prohibited || moduleName.startsWith(`${prohibited}/`)) {
            prohibitedFound.push(moduleName);
          }
        }
      }
    }

    // 2. Ports & Adapters: Check Interfaces & Type Aliases
    if (ts.isInterfaceDeclaration(node)) {
      declaredContracts.push(node.name.text);
    } else if (ts.isTypeAliasDeclaration(node)) {
      declaredContracts.push(node.name.text);
    }

    // 3. Invariants & Value Objects: Check Class Constructors & Custom Errors
    if (ts.isClassDeclaration(node)) {
      // Check if this class extends Error
      if (node.heritageClauses) {
        for (const clause of node.heritageClauses) {
          for (const typeNode of clause.types) {
            if (ts.isIdentifier(typeNode.expression) && typeNode.expression.text.includes("Error")) {
              hasCustomError = true;
            }
          }
        }
      }
    }

    if (ts.isConstructorDeclaration(node)) {
      hasConstructor = true;
      // Inspect constructor body for defensive guards
      if (node.body) {
        ts.forEachChild(node.body, (child) => {
          if (ts.isThrowStatement(child) || ts.isIfStatement(child)) {
            hasGuardClause = true;
          }
        });
      }
    }

    // Check for Result pattern returns or references
    if (ts.isTypeReferenceNode(node)) {
      if (ts.isIdentifier(node.typeName) && node.typeName.text.includes("Result")) {
        hasResultReturn = true;
      }
    }

    // 4. Type Rigor: Count exact AnyKeyword tokens
    if (node.kind === ts.SyntaxKind.AnyKeyword) {
      anyCount++;
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);

  // Compute 1. Domain Boundary Score (30%)
  const domainScore = prohibitedFound.length === 0 ? 30.0 : Math.max(0.0, 30.0 - prohibitedFound.length * 15.0);

  // Compute 2. Invariant Safety Score (25%)
  let invariantScore = 0.0;
  if (hasConstructor && hasGuardClause) {
    invariantScore += 15.0;
  } else if (hasGuardClause || hasCustomError) {
    invariantScore += 10.0;
  }
  if (hasResultReturn || hasCustomError) {
    invariantScore += 10.0;
  }
  invariantScore = Math.min(25.0, invariantScore);

  // Compute 3. Ports & Decoupling Score (25%)
  let portsScore = 0.0;
  if (declaredContracts.length > 0) {
    // Give 15 pts for first port/interface, 5 pts per additional up to 25
    portsScore = Math.min(25.0, 15.0 + (declaredContracts.length - 1) * 5.0);
  }

  // Compute 4. Type Rigor (20%)
  const typingScore = Math.max(0.0, 20.0 - anyCount * 5.0);

  const compositeScore = domainScore + invariantScore + portsScore + typingScore;

  // Extract parse errors if any
  const parseErrors: string[] = [];
  const diags = (sourceFile as unknown as { parseDiagnostics?: readonly ts.Diagnostic[] }).parseDiagnostics;
  if (diags && diags.length > 0) {
    for (const d of diags.slice(0, 3)) {
      parseErrors.push(typeof d.messageText === "string" ? d.messageText : d.messageText.messageText);
    }
  }

  return {
    domainBoundaryScore: Math.round(domainScore * 10) / 10,
    prohibitedImports: Array.from(new Set(prohibitedFound)),
    hasConstructorGuards: hasGuardClause,
    invariantScore: Math.round(invariantScore * 10) / 10,
    portsScore: Math.round(portsScore * 10) / 10,
    declaredContracts: Array.from(new Set(declaredContracts)),
    anyOccurrences: anyCount,
    typingScore: Math.round(typingScore * 10) / 10,
    compositeScore: Math.round(compositeScore * 10) / 10,
    parseErrors,
  };
}

/**
 * Batch CLI processor: reads JSON array from STDIN, writes JSON array to STDOUT.
 */
async function main(): Promise<void> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk as Buffer);
  }

  const rawInput = Buffer.concat(chunks).toString("utf-8").trim();
  if (!rawInput) {
    process.exit(0);
  }

  try {
    const parsed = JSON.parse(rawInput) as AnalysisInput | AnalysisInput[];
    const items = Array.isArray(parsed) ? parsed : [parsed];

    const results: AnalysisOutput[] = items.map((item) => ({
      id: item.id,
      metrics: analyzeCode(item.code),
    }));

    process.stdout.write(JSON.stringify(results, null, 2));
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    process.stderr.write(`[AST Analyzer Error] ${errorMsg}\n`);
    process.exit(1);
  }
}

// Only invoke CLI runner if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
