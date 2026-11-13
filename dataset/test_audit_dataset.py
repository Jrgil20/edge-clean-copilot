"""Tests for the answer-quality checks in audit_dataset.py (stdlib unittest)."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import audit_dataset as audit  # noqa: E402

TS_AVAILABLE = shutil.which("node") is not None and (HERE.parent / "cli" / "node_modules" / "typescript").exists()


def row(prompt: str, answer: str) -> dict:
    return {"messages": [
        {"role": "system", "content": "s"},
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": answer},
    ]}


class AnswerChecksTest(unittest.TestCase):
    def test_odd_fence_count_is_truncated(self):
        self.assertTrue(audit.is_truncated("text\n```typescript\nconst a = 1;\n"))
        self.assertFalse(audit.is_truncated("```typescript\nconst a = 1;\n```"))

    def test_ts_code_joins_closed_typescript_blocks_only(self):
        answer = "```typescript\nconst a = 1;\n```\n```python\nx = 1\n```\n```ts\nconst b = 2;\n```\n```typescript\nunclosed"
        self.assertEqual(audit.ts_code(answer), "const a = 1;\n\nconst b = 2;")

    def test_explicit_any_detection(self):
        for code in ["let x: any;", "const y = z as any;", "const l: any[] = [];", "f<any>()"]:
            self.assertTrue(audit.has_explicit_any(code), code)
        for code in ["let anything: string;", "// returns any value", "const many = 1;"]:
            self.assertFalse(audit.has_explicit_any(code), code)


class NearDuplicateTest(unittest.TestCase):
    CODE = ("app.post('/orders', async (req, res) => {\n  const total = req.body.items.reduce((s, i) => s + i.price, 0);\n"
            "  if (total > 500) return res.status(422).json({ error: 'Too large' });\n  await db.insert('orders', { total });\n"
            "  res.status(201).json({ total });\n});")

    def prompt(self, instruction: str, code: str) -> str:
        return f"{instruction}\n\n```typescript\n{code}\n```"

    def test_reformatted_and_renamed_code_is_a_near_duplicate(self):
        original = row(self.prompt("Refactor this route:", self.CODE), "a")
        # Same code with different layout and one extra statement, under a different instruction
        variant = self.CODE.replace("\n  ", " ").replace("res.status(201)", "console.log(total);\n  res.status(201)")
        copy = row(self.prompt("Please clean up this handler:", variant), "b")
        pairs = audit.near_duplicates([copy], [original], 0.8)
        self.assertEqual(len(pairs), 1)

    def test_unrelated_code_and_prose_prompts_are_not_flagged(self):
        other = "class Clock { now(): Date { return new Date(); } }\nexport const clock = new Clock();"
        rows_a = [row(self.prompt("Refactor this route:", self.CODE), "a"), row("Write a use case for X", "a")]
        rows_b = [row(self.prompt("Refactor this:", other), "b"), row("Write a use case for X", "b")]
        self.assertEqual(audit.near_duplicates(rows_a, rows_b, 0.8), [])

    def test_same_list_reports_each_pair_once_and_skips_identical_prompts(self):
        a = row(self.prompt("Refactor this route:", self.CODE), "a")
        b = row(self.prompt("Clean this route:", self.CODE), "b")
        pairs = audit.near_duplicates([a, b, a], [a, b, a], 0.8, same=True)
        self.assertEqual(sorted((i, j) for i, j, _ in pairs), [(0, 1), (1, 2)])

    def test_strict_fails_on_near_duplicate_eval_code(self):
        tmp = Path(tempfile.mkdtemp())
        train, held = tmp / "t.jsonl", tmp / "e.jsonl"
        train.write_text(json.dumps(row(self.prompt("Refactor this route:", self.CODE), "a")) + "\n")
        held.write_text(json.dumps(row(self.prompt("Tidy this route up:", self.CODE + "\n// v2"), "b")) + "\n")
        proc = subprocess.run([sys.executable, str(HERE / "audit_dataset.py"), "--train", str(train), "--eval", str(held), "--strict"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("eval code near-dup    : 1/1", proc.stdout)


@unittest.skipUnless(TS_AVAILABLE, "needs node and `pnpm install` in cli/")
class TypecheckTest(unittest.TestCase):
    def test_valid_and_invalid_snippets(self):
        results = audit.typecheck({
            "ok": "export class Email { private constructor(readonly value: string) {} }",
            "bad": "const n: number = 'text';",
            "unresolved": "import { Repo } from './repo';\nexport class S { constructor(private r: Repo) {} }",
        })
        self.assertEqual(results["ok"]["typeErrors"], 0)
        self.assertGreater(results["bad"]["typeErrors"], 0)
        self.assertEqual(results["unresolved"]["typeErrors"], 0)

    def test_files_in_one_block_that_import_each_other(self):
        code = (
            "// errors.ts\nexport class DomainError extends Error {}\n"
            "// use-case.ts\nimport { DomainError } from './errors';\n"
            "export const e: DomainError = new DomainError('x');"
        )
        self.assertEqual(audit.typecheck({"multi": code})["multi"]["typeErrors"], 0)

    def test_callback_parameters_are_not_flagged_but_declared_ones_are(self):
        results = audit.typecheck({
            "callback": "app.put('/x', async (req, res) => { res.json(req.body); });",
            "function": "export function f(x) { return x; }",
            "method": "export class A { m(y) { return y; } }",
        })
        self.assertEqual(results["callback"]["typeErrors"], 0)
        self.assertGreater(results["function"]["typeErrors"], 0)
        self.assertGreater(results["method"]["typeErrors"], 0)

    def test_imported_names_that_match_lib_globals_are_not_flagged(self):
        results = audit.typecheck({
            # NestJS `Body` would otherwise resolve to the DOM `Body` interface once imports are blanked
            "imported": "import { Body, Post } from '@nestjs/common';\n"
                        "export class C { @Post() create(@Body() b: { x: number }) { return b.x; } }",
            # Express `Request`/`Response` would otherwise be the DOM fetch types (no `.header`, `.status(n)`)
            "express": "import { Request, Response } from 'express';\n"
                       "export function h(req: Request, res: Response) { res.status(401).json({ t: req.header('x') }); }",
            "not_imported": "export const b = Body;",
        })
        self.assertEqual(results["imported"]["typeErrors"], 0)
        self.assertEqual(results["express"]["typeErrors"], 0)
        self.assertGreater(results["not_imported"]["typeErrors"], 0)

    def test_cli_reports_typecheck_counts(self):
        tmp = Path(tempfile.mkdtemp())
        train, held = tmp / "t.jsonl", tmp / "e.jsonl"
        train.write_text(json.dumps(row("p1", "```typescript\nconst n: number = 'x';\n```")) + "\n")
        held.write_text(json.dumps(row("p2", "```typescript\nconst n: number = 1;\n```")) + "\n")
        out = subprocess.run(
            [sys.executable, str(HERE / "audit_dataset.py"), "--train", str(train), "--eval", str(held), "--typecheck"],
            check=True, capture_output=True, text=True,
        ).stdout
        self.assertIn("type-check passes     : 0/1", out)
        self.assertIn("type-check passes     : 1/1", out)


if __name__ == "__main__":
    unittest.main()
