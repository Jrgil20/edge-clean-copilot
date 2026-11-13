"""Regression tests: the train/holdout split must never share a user prompt."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "split_dataset.py"


def sample(prompt: str, answer: str) -> dict:
    return {"messages": [
        {"role": "system", "content": "s"},
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": answer},
    ]}


def user_prompts(path: Path) -> set:
    return {
        next(m["content"] for m in json.loads(line)["messages"] if m["role"] == "user")
        for line in path.read_text().splitlines() if line.strip()
    }


class SplitDatasetTest(unittest.TestCase):
    def run_split(self, rows):
        tmp = Path(tempfile.mkdtemp())
        seed, gen = tmp / "seed.jsonl", tmp / "gen.jsonl"
        seed.write_text("")
        gen.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        out_t, out_e = tmp / "t.jsonl", tmp / "e.jsonl"
        subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "--seed-file", str(seed), "--generated-file", str(gen),
             "--train-output", str(out_t), "--eval-output", str(out_e), "--eval-target-count", "4"],
            check=True, capture_output=True,
        )
        return out_t, out_e

    def test_no_prompt_shared_between_train_and_holdout(self):
        rows = [sample(f"prompt {i % 6}", f"answer {i}") for i in range(24)]
        out_t, out_e = self.run_split(rows)
        self.assertFalse(user_prompts(out_t) & user_prompts(out_e))

    def test_holdout_prefers_small_prompt_groups_and_never_exceeds_target(self):
        # One prompt with 10 rows plus five single-row prompts, all in the same category.
        rows = [sample("big prompt", f"answer {i}") for i in range(10)]
        rows += [sample(f"small prompt {i}", "answer") for i in range(5)]
        out_t, out_e = self.run_split(rows)
        held = [l for l in out_e.read_text().splitlines() if l.strip()]
        self.assertLessEqual(len(held), 4)
        self.assertNotIn("big prompt", user_prompts(out_e))
        self.assertIn("big prompt", user_prompts(out_t))

    def test_drops_answers_with_unbalanced_code_fence(self):
        rows = [sample("a", "ok ```ts\nx\n```"), sample("b", "cut ```ts\nx"), sample("c", "fine"), sample("d", "fine too")]
        out_t, out_e = self.run_split(rows)
        self.assertNotIn("b", user_prompts(out_t) | user_prompts(out_e))


TS_AVAILABLE = (
    __import__("shutil").which("node") is not None
    and (Path(__file__).resolve().parent.parent / "cli" / "node_modules" / "typescript").exists()
)


@unittest.skipUnless(TS_AVAILABLE, "needs node and `pnpm install` in cli/")
class QualityGateTest(unittest.TestCase):
    ROWS = [
        sample("good", "```typescript\nexport const n: number = 1;\n```"),
        sample("uses any", "```typescript\nexport const n: any = 1;\n```"),
        sample("type error", "```typescript\nexport const n: number = 'x';\n```"),
        sample("prose only", "Split the class: the domain must not import the ORM."),
    ]

    def run_with(self, *extra):
        tmp = Path(tempfile.mkdtemp())
        seed, gen = tmp / "seed.jsonl", tmp / "gen.jsonl"
        seed.write_text("")
        gen.write_text("\n".join(json.dumps(r) for r in self.ROWS) + "\n")
        out_t, out_e = tmp / "t.jsonl", tmp / "e.jsonl"
        subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "--seed-file", str(seed), "--generated-file", str(gen),
             "--authored-file", str(tmp / "none.jsonl"), "--claude-file", str(tmp / "none.jsonl"), "--train-output", str(out_t), "--eval-output", str(out_e),
             "--eval-target-count", "0", *extra],
            check=True, capture_output=True,
        )
        return user_prompts(out_t) | user_prompts(out_e)

    def test_drops_explicit_any_and_type_errors(self):
        self.assertEqual(self.run_with(), {"good", "prose only"})

    def test_no_verify_keeps_them(self):
        self.assertEqual(self.run_with("--no-verify"), {"good", "uses any", "type error", "prose only"})


class ClassifierTest(unittest.TestCase):
    def classify(self, prompt: str) -> str:
        import importlib.util
        spec = importlib.util.spec_from_file_location("split_dataset", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.classify_sample(sample(prompt, "x"))

    def test_substrings_do_not_trigger_port_adapter(self):
        self.assertEqual(self.classify("Refactor this code that does an import and builds a report"), "ARCH_REFACTOR")

    def test_whole_words_still_match(self):
        self.assertEqual(self.classify("Create a port and an adapter for storage"), "PORT_ADAPTER")
        self.assertEqual(self.classify("Critique this class with SOLID"), "SOLID_CRITIQUE")


if __name__ == "__main__":
    unittest.main()
