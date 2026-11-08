"""Zero-dependency tests: python3 -m unittest discover -s evaluation/tests -v"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EVAL_DIR))
import eval_benchmark as eb  # noqa: E402


class DegenerateOutputTests(unittest.TestCase):
    def test_empty_and_refusal_are_degenerate(self):
        self.assertTrue(eb.is_degenerate_output(""))
        self.assertTrue(eb.is_degenerate_output("I cannot help with that request, sorry."))

    def test_code_with_declaration_is_not_degenerate(self):
        code = "export class Order { constructor(private readonly id: string) {} }"
        self.assertFalse(eb.is_degenerate_output(code))

    def test_empty_output_scores_fifty_floor(self):
        # Documents metric finding F9: do-nothing output earns 50/100.
        self.assertEqual(eb.evaluate_code_sample("")["total_score"], 50)


class ReportMetaTests(unittest.TestCase):
    def test_offline_report_has_meta_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            subprocess.run(
                [sys.executable, str(EVAL_DIR / "eval_benchmark.py"),
                 "--cases", str(EVAL_DIR / "test_benchmark_cases.jsonl"),
                 "--no-ast", "--model-name", "unit", "--output", str(out)],
                check=True, capture_output=True,
            )
            report = json.loads(out.read_text())
        self.assertEqual(report["meta"]["model_name"], "unit")
        self.assertEqual(report["meta"]["mode"], "offline")
        self.assertEqual(report["meta"]["engine"], "regex")
        self.assertIn("degenerate_samples", report["meta"])
        self.assertIn("average_score", report)  # pre-existing key preserved


if __name__ == "__main__":
    unittest.main()
