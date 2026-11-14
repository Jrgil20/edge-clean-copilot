#!/usr/bin/env python3
"""
Edge Clean Copilot — Project Status Dashboard

Zero-dependency CLI that prints the state of the project as found on disk.
It reports only what it checks: files, line counts and attributed benchmark
reports. It never contacts the DGX Spark.
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
GGUF_NAME = "clean-copilot-1.5b-q4_k_m.gguf"
GGUF_CANDIDATES = (Path("models") / GGUF_NAME, Path("training") / "output" / "gguf" / GGUF_NAME)


def count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def present(path: Path) -> str:
    return "OK" if path.exists() else "MISSING"


def user_prompts(path: Path) -> list:
    """Whitespace-normalized first user prompt of every row."""
    prompts = []
    if not path.is_file():
        return prompts
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                messages = json.loads(line).get("messages", [])
            except json.JSONDecodeError:
                continue
            for m in messages:
                if isinstance(m, dict) and m.get("role") == "user":
                    prompts.append(" ".join(str(m.get("content", "")).split()))
                    break
    return prompts


def overlap(train: Path, holdout: Path) -> int:
    """Number of holdout rows whose prompt also appears in train."""
    seen = set(user_prompts(train))
    return sum(1 for prompt in user_prompts(holdout) if prompt in seen)


def find_gguf(root: Path) -> Optional[Tuple[Path, int]]:
    for rel in GGUF_CANDIDATES:
        path = root / rel
        if path.is_file():
            return rel, path.stat().st_size
    return None


def latest_spark_reports(root: Path) -> Tuple[Optional[str], List[Tuple[str, float, int]]]:
    """Returns the newest spark-* run folder and its (model, average CAS, n) rows."""
    reports_dir = root / "evaluation" / "reports"
    runs = sorted(p for p in reports_dir.glob("spark-*") if (p / "cas").is_dir()) if reports_dir.is_dir() else []
    if not runs:
        return None, []
    run = runs[-1]
    rows = []
    for report in sorted((run / "cas").glob("report_*.json")):
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = (data.get("meta") or {}).get("model_name") or report.stem.removeprefix("report_")
        rows.append((name, data.get("average_score"), data.get("total_samples")))
    return run.name, rows


def build_report(root: Path) -> List[str]:
    ds = root / "dataset"
    lines = ["=" * 70, "  EDGE CLEAN COPILOT — PROJECT STATUS (proof of concept)", "=" * 70]

    lines.append("\n[1] DATASET")
    lines.append(f"  • Seed / generated pool  : {count_lines(ds / 'seed_examples.jsonl')} / {count_lines(ds / 'generated_examples.jsonl')} rows")
    lines.append(
        f"  • Authored examples      : {count_lines(ds / 'authored_examples.jsonl')} hand-written, "
        f"{count_lines(ds / 'claude_authored_examples.jsonl')} Claude-authored"
    )
    lines.append(
        f"  • Current split          : {count_lines(ds / 'train.jsonl')} train / "
        f"{count_lines(ds / 'eval_holdout.jsonl')} holdout "
        f"({overlap(ds / 'train.jsonl', ds / 'eval_holdout.jsonl')} holdout rows with a prompt seen in train)"
    )
    lines.append(
        f"  • Published model split  : {count_lines(ds / 'published_model_train.jsonl')} train / "
        f"{count_lines(ds / 'published_model_holdout.jsonl')} holdout "
        f"({overlap(ds / 'published_model_train.jsonl', ds / 'published_model_holdout.jsonl')} holdout rows with a prompt seen in train; "
        "the published model was trained on this one, see MODEL_CARD.md)"
    )

    lines.append("\n[2] TRAINING & MODEL")
    lines.append(f"  • LoRA trainer           : {present(root / 'training' / 'train_lora.py')}")
    lines.append(f"  • GGUF converter         : {present(root / 'training' / 'convert_to_gguf.sh')}")
    gguf = find_gguf(root)
    if gguf:
        rel, size = gguf
        lines.append(f"  • GGUF model             : {rel.as_posix()} ({size / 1024 ** 3:.2f} GiB)")
    else:
        lines.append("  • GGUF model             : not found (gitignored; see training/README.md or the Hugging Face repo)")
    lines.append("  • DGX Spark              : not checked (this script never opens SSH)")

    lines.append("\n[3] CLI")
    src = root / "cli" / "src"
    lines.append(f"  • Composition root       : {present(src / 'infrastructure' / 'cli' / 'index.ts')}")
    lines.append(f"  • Use case               : {present(src / 'application' / 'use-cases' / 'RefactorCodeUseCase.ts')}")
    lines.append(f"  • llama-server adapter   : {present(src / 'infrastructure' / 'ai' / 'LlamaServerAdapter.ts')}")
    lines.append(f"  • Dependencies installed : {'yes' if (root / 'cli' / 'node_modules').is_dir() else 'no (run: cd cli && pnpm install)'}")

    lines.append("\n[4] EVALUATION")
    ev = root / "evaluation"
    lines.append(f"  • Legacy benchmark suite : {count_lines(ev / 'legacy_benchmark_suite.jsonl')} cases")
    lines.append(f"  • Control suite          : {count_lines(ev / 'test_benchmark_cases.jsonl')} cases")
    run, rows = latest_spark_reports(root)
    if rows:
        lines.append(f"  • Latest attributed run  : evaluation/reports/{run}/")
        for name, score, n in rows:
            lines.append(f"      - {name:<16} CAS {score} (n={n})")
    else:
        lines.append("  • Benchmark results      : no attributed report found in evaluation/reports/spark-*/")

    lines.append("\nRun the checks:")
    lines.append("  cd cli && pnpm test")
    lines.append("  python3 -m unittest discover -s evaluation/tests")
    lines.append("=" * 70)
    return lines


def main() -> int:
    print("\n".join(build_report(PROJECT_ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
