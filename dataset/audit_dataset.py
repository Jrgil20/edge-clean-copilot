#!/usr/bin/env python3
"""
Dataset audit: duplicate prompts and train/eval leakage.

Zero-dependency. Read-only. Usage:
    python3 audit_dataset.py            # print report
    python3 audit_dataset.py --strict   # exit 1 if eval overlaps train
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE_BLOCK = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)


def load(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def user_prompt(row) -> str:
    return next((m["content"] for m in row["messages"] if m["role"] == "user"), "")


def code_of(prompt: str) -> str:
    match = CODE_BLOCK.search(prompt)
    return (match.group(1) if match else prompt).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", default=str(HERE / "train.jsonl"))
    parser.add_argument("--eval", default=str(HERE / "eval_holdout.jsonl"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    train, held = load(Path(args.train)), load(Path(args.eval))
    train_prompts = Counter(user_prompt(r) for r in train)
    train_code = {code_of(user_prompt(r)) for r in train}

    eval_prompt_hits = sum(user_prompt(r) in train_prompts for r in held)
    eval_code_hits = sum(code_of(user_prompt(r)) in train_code for r in held)

    print(f"train rows            : {len(train)}")
    print(f"train unique prompts  : {len(train_prompts)}")
    print(f"train duplicate rows  : {len(train) - len(train_prompts)}")
    print(f"eval rows             : {len(held)}")
    print(f"eval prompts in train : {eval_prompt_hits}/{len(held)}")
    print(f"eval code in train    : {eval_code_hits}/{len(held)}")
    print("most repeated train prompts:")
    for prompt, count in train_prompts.most_common(3):
        print(f"  {count}x {prompt[:90]!r}")

    leaked = eval_prompt_hits > 0 or eval_code_hits > 0
    print("RESULT:", "LEAKAGE" if leaked else "clean")
    return 1 if (leaked and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
