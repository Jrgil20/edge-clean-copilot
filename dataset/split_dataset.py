#!/usr/bin/env python3
"""Dataset Splitter & Stratifier for Edge Clean Copilot

Unifies seed_examples.jsonl and generated_examples.jsonl and splits them
into train.jsonl and eval_holdout.jsonl with reproducible stratification (seed=42).
Splits by normalized user prompt so no prompt appears in both train and holdout.
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any

def classify_sample(sample: Dict[str, Any]) -> str:
    """Classifies a ChatML sample into its architectural category based on user prompt content."""
    user_content = ""
    for msg in sample.get("messages", []):
        if msg.get("role") == "user":
            user_content = msg.get("content", "").lower()
            break

    if "aaa" in user_content or "arrange-act-assert" in user_content or "unit test" in user_content:
        return "AAA_TEST"
    elif "port" in user_content or "adapter" in user_content or "gateway" in user_content:
        return "PORT_ADAPTER"
    elif "value object" in user_content or "entity" in user_content or "money" in user_content or "email" in user_content:
        return "ENTITY_VALUE_OBJECT"
    elif "use case" in user_content or "usecase" in user_content:
        return "USE_CASE"
    elif "solid" in user_content or "critique" in user_content or "srp" in user_content:
        return "SOLID_CRITIQUE"
    else:
        return "ARCH_REFACTOR"

def main():
    parser = argparse.ArgumentParser(description="Stratified dataset splitter for Edge Clean Copilot.")
    parser.add_argument("--seed-file", type=str, default=str(Path(__file__).parent / "seed_examples.jsonl"))
    parser.add_argument("--generated-file", type=str, default=str(Path(__file__).parent / "generated_examples.jsonl"))
    parser.add_argument("--train-output", type=str, default=str(Path(__file__).parent / "train.jsonl"))
    parser.add_argument("--eval-output", type=str, default=str(Path(__file__).parent / "eval_holdout.jsonl"))
    parser.add_argument("--eval-target-count", type=int, default=30, help="Target count for holdout evaluation set.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic reproducibility.")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # 1. Load and deduplicate samples
    all_samples: List[Dict[str, Any]] = []
    seen_prompts = set()

    for file_path in [Path(args.seed_file), Path(args.generated_file)]:
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
                key = (user_text, assistant_text)
                if key in seen_prompts:
                    continue
                seen_prompts.add(key)
                all_samples.append(item)

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
