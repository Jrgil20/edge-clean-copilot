"""Tests for status.py: it reports only what it checks. Run: python3 -m unittest test_status.py -v"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import status  # noqa: E402


def write_lines(path: Path, n: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps({"i": i}) + "\n" for i in range(n)))


class StatusReportTest(unittest.TestCase):
    def test_reads_cas_from_the_attributed_spark_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cas = root / "evaluation" / "reports" / "spark-20990101T000000Z" / "cas"
            cas.mkdir(parents=True)
            (cas / "report_ecc-ft.json").write_text(json.dumps({"meta": {"model_name": "ecc-ft"}, "average_score": 74.83, "total_samples": 30}))
            (cas / "report_qwen-base.json").write_text(json.dumps({"meta": {"model_name": "qwen-base"}, "average_score": 58.0, "total_samples": 30}))
            text = "\n".join(status.build_report(root))
        self.assertIn("ecc-ft", text)
        self.assertIn("74.83", text)
        self.assertIn("qwen-base", text)
        self.assertIn("58.0", text)

    def test_reports_missing_artifacts_instead_of_claiming_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = "\n".join(status.build_report(Path(tmp)))
        self.assertIn("GGUF model             : not found", text)
        self.assertIn("no attributed report found", text)
        self.assertNotIn("100%", text)
        self.assertNotIn("VERIFIED", text)

    def test_finds_the_gguf_and_lists_both_dataset_splits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gguf = root / "models" / "clean-copilot-1.5b-q4_k_m.gguf"
            gguf.parent.mkdir()
            gguf.write_bytes(b"\0" * 2048)
            write_lines(root / "dataset" / "train.jsonl", 153)
            write_lines(root / "dataset" / "eval_holdout.jsonl", 30)
            write_lines(root / "dataset" / "published_model_train.jsonl", 138)
            write_lines(root / "dataset" / "published_model_holdout.jsonl", 30)
            text = "\n".join(status.build_report(root))
        self.assertIn("models/clean-copilot-1.5b-q4_k_m.gguf", text)
        self.assertIn("153 train / 30 holdout", text)
        self.assertIn("138 train / 30 holdout", text)
        self.assertIn("published model was trained on", text)

    def test_never_prints_hardcoded_cluster_state(self):
        out = subprocess.run([sys.executable, str(ROOT / "status.py")], capture_output=True, text=True, check=True).stdout
        self.assertNotIn("Curfew", out)
        self.assertNotIn("73%", out)


if __name__ == "__main__":
    unittest.main()
