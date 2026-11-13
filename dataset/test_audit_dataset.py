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
