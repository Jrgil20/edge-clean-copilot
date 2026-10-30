#!/usr/bin/env python3
"""Fine-tune Small Language Models with LoRA for Clean Architecture

Parameterized, recipe-driven training harness for open-weight SLMs.
Supports:
- Model Recipe Registry (`training/recipes/*.yaml` or `*.json`)
- Dynamic collator with Completion-Only Loss Masking (`response_template`)
- Fail-fast linear layer validation across model architectures
- Wall-clock burst execution cap (--max-time-minutes)
- Direct 16-bit weight consolidation (--merge) for llama.cpp GGUF conversion
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure training directory is in path for recipe imports
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from recipes.schema import load_recipe, ModelRecipe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune Small Language Models with LoRA for Clean Architecture."
    )
    parser.add_argument(
        "--recipe",
        type=str,
        default=str(SCRIPT_DIR / "recipes" / "qwen2.5-coder-1.5b.yaml"),
        help="Path to declarative Model Recipe (.yaml or .json). Default: recipes/qwen2.5-coder-1.5b.yaml"
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default=None,
        help="Override Hugging Face base model repository or local path."
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(Path(__file__).parent.parent / "dataset" / "train.jsonl"),
        help="Path to JSONL dataset formatted in ChatML."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path(__file__).parent / "output"),
        help="Directory to save LoRA adapters and checkpoints."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute exactly 1 training step on CPU/GPU to validate the pipeline."
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Override number of full training epochs."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override per-device batch size."
    )
    parser.add_argument(
        "--grad-accum",
        type=int,
        default=None,
        help="Override gradient accumulation steps."
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=None,
        help="Override learning rate for AdamW optimizer."
    )
    parser.add_argument(
        "--max-seq-len",
        type=int,
        default=None,
        help="Override maximum sequence token length."
    )
    parser.add_argument(
        "--lora-r",
        type=int,
        default=None,
        help="Override LoRA rank dimension."
    )
    parser.add_argument(
        "--lora-alpha",
        type=int,
        default=None,
        help="Override LoRA scaling factor alpha."
    )
    parser.add_argument(
        "--lora-dropout",
        type=float,
        default=None,
        help="Override LoRA dropout rate."
    )
    parser.add_argument(
        "--max-time-minutes",
        type=float,
        default=None,
        help="Maximum training time in minutes before stopping gracefully (e.g. 5.0)."
    )
    parser.add_argument(
        "--memory-fraction",
        type=float,
        default=0.70,
        help="Defensive CUDA memory fraction limit (0.0 to 1.0, default: 0.70 to preserve 30 percent for lab workloads)."
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge LoRA adapters into base model weights after training."
    )
    return parser.parse_args()


class ChatDataset:
    """PyTorch-compatible dataset for ChatML JSONL samples."""

    def __init__(self, tokenized_samples: List[Dict[str, List[int]]]):
        self.samples = tokenized_samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, List[int]]:
        return self.samples[idx]


def collate_fn_factory(pad_token_id: int, response_token_ids: Optional[List[int]] = None):
    """Creates a collate function that pads dynamically and applies completion-only loss masking."""
    import torch

    def collate_fn(batch: List[Dict[str, List[int]]]) -> Dict[str, torch.Tensor]:
        max_len = max(len(item["input_ids"]) for item in batch)
        input_ids_list = []
        attention_mask_list = []
        labels_list = []

        for item in batch:
            input_ids = item["input_ids"]
            padding_len = max_len - len(input_ids)

            padded_input_ids = input_ids + [pad_token_id] * padding_len
            padded_mask = [1] * len(input_ids) + [0] * padding_len

            # Build labels with optional completion-only masking
            labels = list(input_ids)
            if response_token_ids and len(response_token_ids) > 0:
                resp_len = len(response_token_ids)
                found_idx = -1
                for i in range(len(input_ids) - resp_len + 1):
                    if input_ids[i : i + resp_len] == response_token_ids:
                        found_idx = i + resp_len
                        break

                if found_idx != -1:
                    # Mask everything before the assistant response
                    for k in range(found_idx):
                        labels[k] = -100

            # Mask out padding tokens with -100
            padded_labels = labels + [-100] * padding_len

            input_ids_list.append(padded_input_ids)
            attention_mask_list.append(padded_mask)
            labels_list.append(padded_labels)

        return {
            "input_ids": torch.tensor(input_ids_list, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask_list, dtype=torch.long),
            "labels": torch.tensor(labels_list, dtype=torch.long),
        }

    return collate_fn


def load_dataset(
    dataset_path: str,
    tokenizer: Any,
    max_seq_len: int,
    dry_run: bool = False,
    response_template: Optional[str] = None
):
    """Loads ChatML JSONL, tokenizes via chat template, and configures loss masking."""
    import torch
    from torch.utils.data import DataLoader

    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {dataset_path}")

    # Encode response template for completion-only loss masking
    response_token_ids = None
    if response_template:
        response_token_ids = tokenizer.encode(response_template, add_special_tokens=False)
        print(f"Completion loss masking active. Template: {repr(response_template)} -> Token IDs: {response_token_ids}")

    tokenized_samples: List[Dict[str, List[int]]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            messages = entry.get("messages", [])

            formatted_text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
            )

            tokens = tokenizer(
                formatted_text,
                truncation=True,
                max_length=max_seq_len,
                add_special_tokens=False,
            )
            tokenized_samples.append({"input_ids": tokens["input_ids"]})

            if dry_run and len(tokenized_samples) >= 2:
                break

    print(f"Loaded {len(tokenized_samples)} samples from {dataset_path}")

    pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    collate = collate_fn_factory(pad_id, response_token_ids=response_token_ids)
    dataset = ChatDataset(tokenized_samples)
    return DataLoader(dataset, batch_size=2 if dry_run else 1, shuffle=not dry_run, collate_fn=collate)


def validate_target_modules(model: Any, target_modules: List[str]) -> List[str]:
    """Validates that target modules exist in the model architecture (fail-fast guard)."""
    named_linear_modules = {name.split(".")[-1] for name, _ in model.named_modules()}
    matched = [m for m in target_modules if m in named_linear_modules]
    if not matched:
        raise ValueError(
            f"[FATAL ARCHITECTURE ERROR] None of the specified target_modules {target_modules} "
            f"exist in the target model.\n"
            f"Available modules detected: {sorted(list(named_linear_modules))[:25]}"
        )
    return matched


def train_loop(
    model: Any,
    dataloader: Any,
    optimizer: Any,
    device: Any,
    epochs: int,
    grad_accum: int,
    dry_run: bool = False,
    max_time_minutes: float = None,
):
    """Executes native training loop with optional graceful time-capping."""
    import torch

    model.train()
    step = 0
    total_loss = 0.0
    start_time = time.time()
    max_seconds = (max_time_minutes * 60.0) if max_time_minutes else None

    print("\nStarting LoRA Fine-Tuning Optimization Loop...")
    if max_seconds:
        print(f"Hardware burst watch-dog: Will stop gracefully after {max_time_minutes:.1f} minutes.")

    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_idx, batch in enumerate(dataloader):
            # Check elapsed time
            elapsed = time.time() - start_time
            if max_seconds and elapsed >= max_seconds:
                print(f"\n[ALERT] Time limit of {max_time_minutes:.1f}m reached ({elapsed/60.0:.2f}m elapsed). Stopping gracefully.")
                return

            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels,
            )
            loss = outputs.loss / grad_accum
            loss.backward()

            total_loss += loss.item()
            epoch_loss += loss.item()

            if (batch_idx + 1) % grad_accum == 0 or (batch_idx + 1) == len(dataloader):
                optimizer.step()
                optimizer.zero_grad()
                step += 1

                if step % 5 == 0 or dry_run:
                    current_lr = optimizer.param_groups[0]["lr"]
                    print(
                        f"Epoch [{epoch+1}/{epochs}] Step {step} | "
                        f"Loss: {loss.item() * grad_accum:.4f} | LR: {current_lr:.2e} | "
                        f"Elapsed: {elapsed:.1f}s"
                    )

            if dry_run and step >= 1:
                print(f"\n[OK] Dry-run verification completed successfully at step {step}.")
                return


def main():
    args = parse_args()

    # 1. Load Model Recipe with Hierarchical Overrides
    recipe_path = Path(args.recipe)
    if recipe_path.exists():
        print(f"--> Ingesting Model Recipe: {recipe_path.resolve()}")
        recipe = load_recipe(recipe_path)
    else:
        raise FileNotFoundError(f"Recipe file not found: {args.recipe}")

    # Hierarchical override: CLI flags take precedence over Recipe defaults
    model_id = args.model_id or recipe.model_id
    epochs = args.epochs or recipe.num_train_epochs
    batch_size = args.batch_size or recipe.batch_size
    grad_accum = args.grad_accum or recipe.grad_accum_steps
    lr = args.lr or recipe.learning_rate
    max_seq_len = args.max_seq_len or recipe.max_seq_len
    lora_r = args.lora_r or recipe.r
    lora_alpha = args.lora_alpha or recipe.lora_alpha
    lora_dropout = args.lora_dropout or recipe.lora_dropout
    target_modules = recipe.target_modules

    print(f"\n========================================================")
    print(f"  EDGE CLEAN COPILOT — RECIPE-DRIVEN LoRA HARNESS")
    print(f"========================================================")
    print(f"  Recipe Name       : {recipe_path.name}")
    print(f"  Architecture      : {recipe.architecture_family.upper()}")
    print(f"  Base Model        : {model_id}")
    print(f"  LoRA Targets      : {', '.join(target_modules)}")
    print(f"  Rank / Alpha / Drop: r={lora_r}, alpha={lora_alpha}, dropout={lora_dropout}")
    print(f"  Epochs / Batch    : {epochs} epochs | batch={batch_size} (accum={grad_accum})")
    print(f"  Learning Rate     : {lr}")
    print(f"  Recommended Quant : {recipe.recommended_quant}")
    print(f"========================================================\n")

    # 2. Imports of heavy ML libraries after arg parsing
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, TaskType

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Compute Device: {device}")

    # Defensive hardware limits: preserve headroom for concurrent lab workloads
    if torch.cuda.is_available() and args.memory_fraction:
        fraction = max(0.1, min(1.0, float(args.memory_fraction)))
        torch.cuda.set_per_process_memory_fraction(fraction, device=0)
        print(f"Defensive hardware guard: CUDA memory fraction capped at {fraction*100:.0f}% (preserving {100-fraction*100:.0f}% for lab).")

    # Bound CPU threads so Grace CPU cores aren't saturated
    torch.set_num_threads(min(8, os.cpu_count() or 4))

    # Precision resolution
    if recipe.torch_dtype == "bfloat16" and torch.cuda.is_available() and torch.cuda.is_bf16_supported():
        torch_dtype = torch.bfloat16
    elif recipe.torch_dtype == "float16" and torch.cuda.is_available():
        torch_dtype = torch.float16
    else:
        torch_dtype = torch.float32

    # 3. Tokenizer Setup
    print(f"Loading tokenizer: {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=recipe.trust_remote_code)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 4. Dataset Loading with Completion Loss Masking
    dataloader = load_dataset(
        args.dataset,
        tokenizer,
        max_seq_len,
        dry_run=args.dry_run,
        response_template=recipe.response_template
    )

    # 5. Model Loading
    print(f"Loading base model: {model_id} (dtype: {torch_dtype})...")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        trust_remote_code=recipe.trust_remote_code,
    ).to(device)

    # 6. Fail-Fast Module Validation
    valid_modules = validate_target_modules(model, target_modules)
    print(f"Validated LoRA target modules: {valid_modules}")

    # 7. Configure LoRA PEFT Model
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=valid_modules,
        bias=recipe.bias,
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    # 8. Run Native Optimization Loop
    train_loop(
        model=model,
        dataloader=dataloader,
        optimizer=optimizer,
        device=device,
        epochs=epochs,
        grad_accum=grad_accum,
        dry_run=args.dry_run,
        max_time_minutes=args.max_time_minutes,
    )

    # 9. Save Trained LoRA Adapters
    output_path = Path(args.output_dir)
    adapter_path = output_path / "lora_adapters"
    adapter_path.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving LoRA adapters to: {adapter_path}")
    model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))

    # 10. Optional Weight Merge for GGUF Quantization
    if args.merge:
        print("\nMerging LoRA adapter weights into base model...")
        merged_model = model.merge_and_unload()
        merged_path = output_path / "merged_model"
        merged_path.mkdir(parents=True, exist_ok=True)
        print(f"Saving merged 16-bit model to: {merged_path}")
        merged_model.save_pretrained(str(merged_path))
        tokenizer.save_pretrained(str(merged_path))
        print("Model merged successfully. Ready for llama.cpp GGUF conversion.")

    print("\n[SUCCESS] Pipeline finished.")


if __name__ == "__main__":
    main()
