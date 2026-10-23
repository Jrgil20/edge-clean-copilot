# Edge Clean Copilot — LoRA Training & GGUF Quantization Pipeline

Modular LoRA fine-tuning and quantization pipeline for Small Language Models (Qwen-2.5-Coder-1.5B/3B) using native PyTorch, Hugging Face `peft`, and `llama.cpp`.

---

## 1. Architecture & Execution Modes

The training script supports dual-mode execution to enforce our **Cold Staging, Hot Burst** methodology:

| Mode | Command Flag | Target Hardware | Purpose |
| :--- | :--- | :--- | :--- |
| **Cold Staging (Dry-Run)** | `--dry-run` | Local Laptop / CPU | Validates dataset tokenization, tensor shapes, gradient calculation, and LoRA weight saving in 1 step. |
| **Hot Burst (Full Training)** | `--train` (default) | NVIDIA DGX Spark (GB10) | Full multi-epoch fine-tuning using `bfloat16`, AdamW optimizer, and gradient accumulation. |

---

## 2. Recipe-Driven LoRA Training CLI

The training harness is decoupled from specific model architectures via **[Model Recipes](recipes/README.md)**. Target linear projections, precision, response delimiters, and default hyperparameters are declared in YAML/JSON.

```bash
# Execute training using a declarative Model Recipe:
python3 train_lora.py \
  --recipe "recipes/qwen2.5-coder-1.5b.yaml" \
  --max-time-minutes 15.0 \
  --merge

# Optional: Override any recipe parameter via CLI flags:
python3 train_lora.py \
  --recipe "recipes/llama-3.2-3b.yaml" \
  --lora-r 32 \
  --max-time-minutes 20.0 \
  --merge
```

### Key Arguments:
- `--recipe`: Path to declarative Model Recipe (default: `recipes/qwen2.5-coder-1.5b.yaml`). See [recipes/README.md](recipes/README.md).
- `--dry-run`: Runs exactly 1 training step on CPU/GPU to verify the pipeline without downloading or running full models.
- `--merge`: Automatically executes `model.merge_and_unload()` after training to save consolidated 16-bit weights ready for `llama.cpp` GGUF quantization.
- `--model-id`: Overrides base model repository (defaults to recipe `model_id`).
- `--dataset`: Path to ChatML JSONL dataset (default: `../dataset/train.jsonl`).
- `--max-time-minutes`: Defensive time cutoff preventing sudden termination in shared compute environments.

---

## 3. Workflow to GGUF Export

```
[train.jsonl (138 samples)]
        │
        ▼ (train_lora.py)
[LoRA Adapter: adapter_model.safetensors]
        │
        ▼ (--merge)
[Merged Model: ./output/merged_model]
        │
        ▼ (convert_to_gguf.sh)
[F16 GGUF: ./output/gguf/clean-copilot-1.5b-f16.gguf] (~3.1 GB)
        │
        ▼ (llama-quantize)
[GGUF Model: clean-copilot-1.5b-q4_k_m.gguf] (~0.9 GB, Ready for edge CPU inference)
```

---

## 4. Automated One-Click GGUF Quantization (`convert_to_gguf.sh`)

After training with `--merge`, execute the automated quantization script:

```bash
# Standard 4-bit edge target (Q4_K_M)
./convert_to_gguf.sh

# Generate full multi-quantization matrix (Q4_K_M, Q5_K_M, Q8_0) and clean F16
./convert_to_gguf.sh --all --clean-f16
```

### Quantization Sizing Matrix:

| Quant Format | Output File Size (1.5B) | Target RAM | Speed on Standard CPU | Quality Retention |
| :--- | :--- | :--- | :--- | :--- |
| **Q4_K_M (Default)** | **~0.9 GB** | **~1.5 GB** | **45–70 tokens/s** | **>96.5%** |
| **Q5_K_M** | ~1.1 GB | ~1.8 GB | 35–55 tokens/s | >98.0% |
| **Q8_0** | ~1.6 GB | ~2.5 GB | 25–40 tokens/s | >99.5% |
| **F16 (Unquantized)** | ~3.1 GB | ~4.5 GB | 10–18 tokens/s | 100% (Baseline) |
