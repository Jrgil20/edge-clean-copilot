# Model Recipes Registry

> **Authoritative Specification:** Model Configuration Registry for Edge Clean Copilot

This directory contains declarative configuration recipes (`.yaml` or `.json`) defining foundation model identity, LoRA target modules, tokenization response templates, precision, and training hyperparameters for the training harness.

---

## 1. Directory Structure

```
training/recipes/
├── schema.py                   # Dataclass ModelRecipe & agnostic loader
├── qwen2.5-coder-1.5b.yaml     # Baseline 1.5B model (Canonical)
├── llama-3.2-3b.yaml           # Llama 3.2 3B model
├── gemma-2-2b.yaml             # Google Gemma 2 2B model
└── README.md                   # This specification
```

---

## 2. Recipe Schema Fields

| Field | Type | Description |
|---|---|---|
| `model_id` | `str` | Hugging Face model identifier (e.g. `Qwen/Qwen2.5-Coder-1.5B-Instruct`). |
| `architecture_family` | `str` | Architectural lineage (`qwen2`, `llama3`, `gemma2`, `deepseek`). |
| `target_modules` | `list[str]` | Exact linear projection names to apply LoRA adapters to. |
| `response_template` | `str` | Delimiter preceding the assistant response for completion-only loss masking. |
| `torch_dtype` | `str` | Precision tensor type (`bfloat16`, `float16`, `float32`). |
| `r` / `lora_alpha` | `int` | LoRA rank dimension and scaling factor. |
| `recommended_quant` | `str` | Target GGUF quantization format (`Q4_K_M`, `Q8_0`). |

---

## 3. How to Register a New Model

1. Create a new YAML file `training/recipes/<model-name>.yaml`.
2. Inspect the model's named modules to verify projection names (`q_proj`, `k_proj`, etc.).
3. Identify the model's chat template assistant header for `response_template`.
4. Run dry-run verification:
   ```bash
   python3 proyecto/training/train_lora.py --recipe proyecto/training/recipes/<model-name>.yaml --dry-run
   ```
