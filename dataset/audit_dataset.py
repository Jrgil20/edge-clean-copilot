#!/usr/bin/env python3
"""
Dataset audit: duplicate and near-duplicate prompts, train/eval leakage and answer quality.

Zero-dependency (the optional type-check needs Node and `pnpm install` in cli/).
Read-only. Usage:
    python3 audit_dataset.py                 # leakage + answer quality report
    python3 audit_dataset.py --typecheck     # also type-check answers with tsc
    python3 audit_dataset.py --typecheck --list-failures
    python3 audit_dataset.py --strict        # exit 1 if eval overlaps train (exact or near-duplicate code)
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
TYPECHECK_HELPER = HERE / "typecheck_answers.mjs"
CODE_BLOCK = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)
TS_BLOCK = re.compile(r"```(?:typescript|ts)\s*\n(.*?)```", re.S | re.I)
EXPLICIT_ANY = re.compile(r":\s*any\b|<any>|\bas\s+any\b|\bany\[\]")


def load(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def user_prompt(row) -> str:
    return next((m["content"] for m in row["messages"] if m["role"] == "user"), "")


def answer_of(row) -> str:
    return next((m["content"] for m in reversed(row["messages"]) if m["role"] == "assistant"), "")


def code_of(prompt: str) -> str:
    match = CODE_BLOCK.search(prompt)
    return (match.group(1) if match else prompt).strip()


def has_code_block(prompt: str) -> bool:
    return CODE_BLOCK.search(prompt) is not None


def shingles(code: str, size: int = 5) -> frozenset:
    """Sets of `size` consecutive tokens (identifiers, numbers, symbols); whitespace and layout are ignored."""
    tokens = re.findall(r"\w+|[^\w\s]", code)
    if len(tokens) < size:
        return frozenset({tuple(tokens)}) if tokens else frozenset()
    return frozenset(tuple(tokens[i:i + size]) for i in range(len(tokens) - size + 1))


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def near_duplicates(left, right, threshold: float, same: bool = False):
    """Pairs (i, j, score) whose prompt code blocks are near-duplicates.

    Only prompts with a fenced code block are compared (prose prompts built from a
    template would all look alike). Identical code is a score of 1.0. With `same`,
    `left` and `right` are the same list and each unordered pair is reported once,
    skipping pairs with the exact same prompt (those are already counted as duplicates).
    """
    def prepared(rows):
        return [(i, user_prompt(r), shingles(code_of(user_prompt(r))))
                for i, r in enumerate(rows) if has_code_block(user_prompt(r))]
    lhs, rhs = prepared(left), prepared(right)
    pairs = []
    for i, prompt_i, sh_i in lhs:
        for j, prompt_j, sh_j in rhs:
            if same and (j <= i or prompt_i == prompt_j):
                continue
            score = jaccard(sh_i, sh_j)
            if score >= threshold:
                pairs.append((i, j, score))
    return pairs


def is_truncated(answer: str) -> bool:
    """An odd number of code fences means the answer stops inside a code block."""
    return answer.count("```") % 2 == 1


def ts_code(answer: str) -> str:
    """All closed TypeScript blocks of an answer, joined; empty if there are none."""
    return "\n\n".join(block.strip() for block in TS_BLOCK.findall(answer) if block.strip())


def has_explicit_any(code: str) -> bool:
    return bool(EXPLICIT_ANY.search(code))


def typecheck(snippets):
    """Runs the Node helper on {id: code}. Returns {id: result}, or None if unavailable."""
    if not snippets:
        return {}
    node = shutil.which("node")
    if node is None:
        print("typecheck: skipped (node not found)", file=sys.stderr)
        return None
    payload = json.dumps([{"id": k, "code": v} for k, v in snippets.items()])
    proc = subprocess.run([node, str(TYPECHECK_HELPER)], input=payload, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"typecheck: skipped ({proc.stderr.strip() or 'helper failed'})", file=sys.stderr)
        return None
    return {r["id"]: r for r in json.loads(proc.stdout)}


def quality_report(name: str, rows, run_typecheck: bool, list_failures: bool) -> None:
    answers = [answer_of(r) for r in rows]
    codes = {str(i): ts_code(a) for i, a in enumerate(answers, 1)}
    with_ts = {k: v for k, v in codes.items() if v}

    print(f"\n[{name}] answer quality")
    print(f"  truncated answers     : {sum(map(is_truncated, answers))}/{len(rows)}")
    print(f"  explicit any in code  : {sum(has_explicit_any(c) for c in with_ts.values())}/{len(with_ts)}")
    if not run_typecheck:
        return

    results = typecheck(with_ts)
    if results is None:
        return
    syntax = [k for k, r in results.items() if r["syntaxErrors"]]
    failed = [k for k, r in results.items() if r["syntaxErrors"] or r["typeErrors"]]
    print(f"  rows with TS code     : {len(with_ts)}/{len(rows)}")
    print(f"  syntax errors         : {len(syntax)}/{len(with_ts)}")
    print(f"  type-check passes     : {len(with_ts) - len(failed)}/{len(with_ts)} (strict, unresolved names ignored)")
    top = Counter(c for k in failed for c in results[k]["codes"]).most_common(5)
    if top:
        print("  most common errors    : " + ", ".join(f"TS{c} x{n}" for c, n in top))
    if list_failures:
        for k in sorted(failed, key=int):
            codes_str = ",".join(f"TS{c}" for c in results[k]["codes"])
            print(f"    row {k:>4}: {codes_str}  {user_prompt(rows[int(k) - 1])[:70]!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--train", default=str(HERE / "train.jsonl"))
    parser.add_argument("--eval", default=str(HERE / "eval_holdout.jsonl"))
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if eval prompts or prompt code overlap train (exactly or near-duplicate)")
    parser.add_argument("--near-dup-threshold", type=float, default=0.8,
                        help="Jaccard similarity of 5-token shingles of prompt code that counts as near-duplicate (default 0.8)")
    parser.add_argument("--typecheck", action="store_true", help="type-check answers with tsc (needs node + cli/node_modules)")
    parser.add_argument("--list-failures", action="store_true", help="with --typecheck, list rows that fail")
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
    eval_near = near_duplicates(held, train, args.near_dup_threshold)
    eval_near_rows = sorted({i for i, _, _ in eval_near})
    train_near = near_duplicates(train, train, args.near_dup_threshold, same=True)
    print(f"eval code near-dup    : {len(eval_near_rows)}/{len(held)} (prompt code similarity >= {args.near_dup_threshold})")
    print(f"train near-dup pairs  : {len(train_near)} (distinct prompts with similar code)")
    for i, j, score in sorted(train_near, key=lambda p: -p[2])[:3]:
        print(f"  {score:.2f} {user_prompt(train[i])[:44]!r} ~ {user_prompt(train[j])[:44]!r}")
    print("most repeated train prompts:")
    for prompt, count in train_prompts.most_common(3):
        print(f"  {count}x {prompt[:90]!r}")

    quality_report("train", train, args.typecheck, args.list_failures)
    quality_report("eval", held, args.typecheck, args.list_failures)

    leaked = eval_prompt_hits > 0 or eval_code_hits > 0 or len(eval_near_rows) > 0
    print("\nRESULT:", "LEAKAGE" if leaked else "clean")
    return 1 if (leaked and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
