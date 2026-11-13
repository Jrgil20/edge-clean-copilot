#!/usr/bin/env python3
"""Dataset Splitter & Stratifier for Edge Clean Copilot

Unifies seed, generated, hand-authored and Claude-authored examples and splits them
into train.jsonl and eval_holdout.jsonl with reproducible stratification (seed=42).
Splits by normalized user prompt so no prompt appears in both train and holdout.

Quality gate (before splitting): drops answers that are truncated (unbalanced
code fence), contain explicit `any`, or whose TypeScript fails an isolated
strict type-check (see audit_dataset.py / typecheck_answers.mjs). The
type-check needs Node and `pnpm install` in cli/; use --no-verify to skip the
`any` and type-check filters.
"""

import argparse
import json
import re
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_dataset import answer_of, has_explicit_any, ts_code, typecheck  # noqa: E402


def verify_samples(samples: List[Dict[str, Any]]):
    """Splits samples into (kept, dropped_any, dropped_typecheck). Raises if tsc is unavailable."""
    codes = {str(i): ts_code(answer_of(s)) for i, s in enumerate(samples)}
    with_any = {k for k, c in codes.items() if c and has_explicit_any(c)}
    to_check = {k: c for k, c in codes.items() if c and k not in with_any}
    results = typecheck(to_check)
    if results is None:
        raise RuntimeError("type-check unavailable: install Node and run `pnpm install` in cli/, or pass --no-verify")
    failed = {k for k, r in results.items() if r["syntaxErrors"] or r["typeErrors"]}
    kept = [s for i, s in enumerate(samples) if str(i) not in with_any | failed]
    dropped_any = [samples[int(k)] for k in sorted(with_any, key=int)]
    dropped_tc = [samples[int(k)] for k in sorted(failed, key=int)]
    return kept, dropped_any, dropped_tc


def classify_sample(sample: Dict[str, Any]) -> str:
    """Classifies a ChatML sample into its architectural category based on user prompt content."""
    user_content = ""
    for msg in sample.get("messages", []):
        if msg.get("role") == "user":
            user_content = msg.get("content", "").lower()
            break
    # Classify by the instruction only: identifiers inside the input code
    # (`email`, `process.env.PORT`) say nothing about the task.
    user_content = re.sub(r"```.*?```", " ", user_content, flags=re.S)
    # "Ports & Adapters" names the target architecture (it is the CLI's own
    # refactor prompt), not a request to design a port.
    user_content = re.sub(r"\bports\s*(?:&|and)\s*adapters\b", " ", user_content)

    def has(*patterns: str) -> bool:
        # Whole-word matching: "import"/"report" must not match "port"
        return any(re.search(rf"\b{p}\b", user_content) for p in patterns)

    if has("aaa", "arrange-act-assert", "unit tests?"):
        return "AAA_TEST"
    elif has("ports?", "adapters?", "gateways?"):
        return "PORT_ADAPTER"
    elif has("value objects?", "entity", "entities", "money", "email"):
        return "ENTITY_VALUE_OBJECT"
    elif has("use cases?", "usecases?"):
        return "USE_CASE"
    elif has("solid", "critique", "srp"):
        return "SOLID_CRITIQUE"
    else:
        return "ARCH_REFACTOR"

def main():
    parser = argparse.ArgumentParser(description="Stratified dataset splitter for Edge Clean Copilot.")
    parser.add_argument("--seed-file", type=str, default=str(Path(__file__).parent / "seed_examples.jsonl"))
    parser.add_argument("--generated-file", type=str, default=str(Path(__file__).parent / "generated_examples.jsonl"))
    parser.add_argument("--authored-file", type=str, default=str(Path(__file__).parent / "authored_examples.jsonl"))
    parser.add_argument("--claude-file", type=str, default=str(Path(__file__).parent / "claude_authored_examples.jsonl"),
                        help="Examples written by Claude (Opus 5.5) in a Claude Code session, kept apart for provenance.")
    parser.add_argument("--train-output", type=str, default=str(Path(__file__).parent / "train.jsonl"))
    parser.add_argument("--eval-output", type=str, default=str(Path(__file__).parent / "eval_holdout.jsonl"))
    parser.add_argument("--eval-target-count", type=int, default=15,
                        help="Maximum row count for the holdout set (whole prompt groups are never split).")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic reproducibility.")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip the explicit-any and type-check filters (truncated answers are always dropped).")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # 1. Load and deduplicate samples
    all_samples: List[Dict[str, Any]] = []
    seen_prompts = set()
    dropped_truncated = 0

    for file_path in [Path(args.seed_file), Path(args.generated_file), Path(args.authored_file), Path(args.claude_file)]:
        if not file_path.exists():
            print(f"[WARNING] File not found: {file_path}", file=sys.stderr)
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                item = json.loads(line)
                # Deduplicate by user prompt text
                user_text = ""
                for m in item.get("messages", []):
                    if m.get("role") == "user":
                        user_text = m.get("content", "").strip()
                        break
                # Deduplicate exact repeats of (prompt, answer)
                assistant_text = ""
                for m in item.get("messages", []):
                    if m.get("role") == "assistant":
                        assistant_text = m.get("content", "").strip()
                        break
                if assistant_text.count("```") % 2 != 0:
                    dropped_truncated += 1
                    continue
                key = (user_text, assistant_text)
                if key in seen_prompts:
                    continue
                seen_prompts.add(key)
                all_samples.append(item)

    print(f"Dropped (unbalanced code fence / truncated): {dropped_truncated}")
    if args.no_verify:
        print("Verification skipped (--no-verify): explicit `any` and type errors are NOT filtered.")
    else:
        try:
            all_samples, dropped_any, dropped_tc = verify_samples(all_samples)
        except RuntimeError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            sys.exit(2)
        print(f"Dropped (explicit `any` in TypeScript):      {len(dropped_any)}")
        print(f"Dropped (fails isolated tsc type-check):     {len(dropped_tc)}")
    total_samples = len(all_samples)
    print("=" * 70)
    print("        EDGE CLEAN COPILOT — STRATIFIED DATASET SPLITTER        ")
    print("=" * 70)
    print(f"Total Unified Samples:  {total_samples}")
    print(f"Target Holdout Count:   {args.eval_target_count}")
    print(f"Random Seed:            {args.seed}")
    print("-" * 70)

    # 2. Group samples by normalized user prompt so a prompt never lands on both sides
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for sample in all_samples:
        prompt_key = " ".join(
            next((m.get("content", "") for m in sample.get("messages", []) if m.get("role") == "user"), "").split()
        ).lower()
        groups[prompt_key].append(sample)

    # 3. Assign whole groups to holdout (round-robin across categories) until the target is reached
    by_category: Dict[str, List[List[Dict[str, Any]]]] = defaultdict(list)
    for key in sorted(groups):
        group = groups[key]
        by_category[classify_sample(group[0])].append(group)
    for cat_groups in by_category.values():
        rng.shuffle(cat_groups)
        # Smallest prompt groups first (stable sort keeps the random order within a size):
        # the holdout gets more distinct prompts, and large groups stay in train instead
        # of draining one category (a 13-row group once took 22 of 31 rows of a category).
        cat_groups.sort(key=len)

    train_set: List[Dict[str, Any]] = []
    eval_set: List[Dict[str, Any]] = []
    pending = {cat: list(g) for cat, g in sorted(by_category.items())}
    while pending and len(eval_set) < args.eval_target_count:
        for cat in list(pending):
            # Keep at least one group per category in train when possible
            if len(pending[cat]) <= 1:
                pending.pop(cat)
                continue
            if len(eval_set) >= args.eval_target_count:
                break
            # Groups are sorted by size, so if the smallest one overshoots the target,
            # every other group in this category would too: stop drawing from it.
            if len(eval_set) + len(pending[cat][0]) > args.eval_target_count:
                pending.pop(cat)
                continue
            eval_set.extend(pending[cat].pop(0))
            if not pending[cat]:
                pending.pop(cat)
    held = {id(x) for x in eval_set}
    train_set = [x for x in all_samples if id(x) not in held]

    print("CATEGORY DISTRIBUTION:")
    for cat, cat_groups in sorted(by_category.items()):
        total = sum(len(g) for g in cat_groups)
        n_eval = sum(1 for g in cat_groups for x in g if id(x) in held)
        print(f"  - {cat:<22}: Total={total:3d} | Train={total - n_eval:3d} | Holdout={n_eval:2d}")
    print(f"Distinct prompts: {len(groups)} (a prompt is never shared between train and holdout)")
    if len(groups) < 30:
        print("[WARNING] Fewer than 30 distinct prompts: generate more diverse data for a meaningful holdout.", file=sys.stderr)

    # 4. Shuffle final sets
    rng.shuffle(train_set)
    rng.shuffle(eval_set)

    # 5. Write outputs
    train_path = Path(args.train_output)
    eval_path = Path(args.eval_output)

    with open(train_path, "w", encoding="utf-8") as f:
        for s in train_set:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(eval_path, "w", encoding="utf-8") as f:
        for s in eval_set:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print("-" * 70)
    print(f"Training Dataset Written: {train_path} ({len(train_set)} samples, {len(train_set)/total_samples*100:.1f}%)")
    print(f"Holdout Dataset Written:  {eval_path} ({len(eval_set)} samples, {len(eval_set)/total_samples*100:.1f}%)")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
