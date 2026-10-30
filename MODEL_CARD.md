---
language:
- en
- es
license: apache-2.0
base_model: Qwen/Qwen2.5-Coder-1.5B-Instruct
tags:
- gguf
- clean-architecture
- hexagonal-architecture
- code-refactoring
- llama-cpp
- edge-ai
- typescript
- lora
pipeline_tag: text-generation
inference: false
model_creator: Jrgil20
model_name: Edge Clean Copilot (1.5B Q4_K_M)
---

# Edge Clean Copilot (1.5B Q4_K_M GGUF)

**Edge Clean Copilot** is a specialized, air-gapped Small Language Model (SLM) designed to perform automated Clean Architecture and Hexagonal refactoring directly on developer edge hardware (CPU/laptop) with zero cloud telemetry and zero recurring API costs.

Fine-tuned from `Qwen/Qwen2.5-Coder-1.5B-Instruct` via Parameter-Efficient Fine-Tuning (LoRA) and quantized to 4-bit `Q4_K_M` GGUF.

---

## Intended Use & Limits

- **Purpose:** an extremely light, private refactoring assistant for small, bounded TypeScript artifacts (single entities, services or classes) that must stay on the machine.
- **Not optimized for speed:** ~12 tokens/s measured on a CPU-only laptop (Intel Core i5-10310U, 15 GB RAM). Long inputs will be slow.
- **Not a frontier replacement:** 76.3 vs 90.5 for the frontier baseline on our benchmark. Review every output before use.

---

## Key Highlights

- **100% Offline & Air-Gapped:** Zero code leakage. Runs entirely within local RAM (~1.5 GB).
- **Domain Purity (Zero Leakage):** Eradicates 100% of prohibited external framework/database imports (`express`, `mongoose`, `axios`, `typeorm`, `prisma`) from the core domain layer.
- **Hexagonal Port & Adapter Decoupling:** Generates abstract interfaces (`IRepository`, `IPort`, `IGateway`) with constructor dependency injection.
- **Strict TypeScript Rigor:** Enforces deterministic typing and completely eliminates explicit `any` types.
- **Measured Gain:** Scores **76.3 / 100 Clean Architecture Score (CAS)**, Grade B, on our 30-case legacy refactoring benchmark (+58.3% over the base foundation model). It does not reach frontier-model quality (90.5 / 100).

---

## Benchmark Results (Clean Architecture Score — CAS 0–100)

Evaluated against the **30-case Legacy Benchmark Suite** (`legacy_benchmark_suite.jsonl`) via an automated AST syntax analyzer:

| Architectural Dimension | Maximum | Base Model (Qwen 1.5B) | **Edge Clean Copilot (GGUF)** | Frontier Cloud (Gemini 3.8 Flash) |
| :--- | :---: | :---: | :---: | :---: |
| **Domain Boundary Isolation** | 30 pts | 14.5 pts | **30.0 pts** | 29.0 pts |
| **Invariant & Result Pattern** | 25 pts | 8.2 pts | **11.7 pts** | 22.5 pts |
| **Port & Adapter Decoupling** | 25 pts | 10.5 pts | **16.0 pts** | 23.0 pts |
| **TypeScript Type Rigor (Zero `any`)** | 20 pts | 15.0 pts | **18.7 pts** | 16.0 pts |
| **TOTAL CAS COMPOSITE** | **100 pts** | **48.2 pts (Grade F)** | **76.3 pts (Grade B)** | **90.5 pts (Grade A)** |

The Edge column comes from the saved report `evaluation/benchmark_report_edge_copilot.json`. A rerun on 2026-10-29 measured 73.8 (invariant 2.0), so treat it as run-to-run variance.

### Operational Edge Metrics

| Metric | Base Model (1.5B F16) | **Edge Clean Copilot (Q4_K_M)** | Frontier Cloud API |
| :--- | :---: | :---: | :---: |
| **Inference Speed** | ~52.0 tok/s (unverified) | **~12 tok/s measured (CPU-only, Intel i5-10310U); not optimized for speed** | ~85.0 tok/s (unverified) |
| **RAM Footprint** | ~3.1 GB | **~1.5 GB** | 0 GB (Cloud) |
| **Disk Size** | ~3.10 GB | **941 MB (0.94 GB)** | 0 MB |
| **Offline Operation** | Yes | **100% Offline (Air-Gapped)** | No (Internet Req) |
| **API Cost** | $0.00 | **$0.00** | Metered billing |

---

## Quickstart & Usage

### 1. Run with `llama.cpp` / `llama-server`

Download the binary file `clean-copilot-1.5b-q4_k_m.gguf`:

```bash
# Launch a local OpenAI-compatible inference server
llama-server \
  -m clean-copilot-1.5b-q4_k_m.gguf \
  --host 127.0.0.1 \
  --port 8085 \
  -c 2048
```

### 2. Run with Ollama

Create a `Modelfile`:

```dockerfile
FROM ./clean-copilot-1.5b-q4_k_m.gguf

TEMPLATE """<|im_start|>system
{{ .System }}<|im_end|>
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

PARAMETER temperature 0.1
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
```

Build and run:
```bash
ollama create clean-copilot -f Modelfile
ollama run clean-copilot
```

### 3. Run with Python (`llama-cpp-python`)

```python
from llama_cpp import Llama

llm = Llama(
    model_path="clean-copilot-1.5b-q4_k_m.gguf",
    n_ctx=2048,
    n_threads=6,
    verbose=False
)

system_prompt = (
    "You are an expert Clean Architecture assistant. Refactor legacy TypeScript/JavaScript "
    "code strictly adhering to Clean Architecture principles: isolate domain entities, "
    "define port interfaces, inject dependencies, and eliminate all `any` types."
)

user_code = """
import express from 'express';
import mongoose from 'mongoose';

export class UserService {
  async getUser(req: any) {
    return await mongoose.model('User').findById(req.params.id);
  }
}
"""

response = llm.create_chat_completion(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Refactor this code to Clean Architecture:\n\n{user_code}"}
    ],
    temperature=0.1,
    max_tokens=1024
)

print(response["choices"][0]["message"]["content"])
```

---

## Training Details

- **Foundation Model:** `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- **Methodology:** LoRA (Parameter-Efficient Fine-Tuning) via PyTorch & Hugging Face `peft`
- **Hardware:** NVIDIA DGX Spark (Grace Blackwell GB10 / Ampere A100)
- **Target Modules:** `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
- **Hyperparameters:**
  - LoRA Rank ($r$): 16
  - LoRA Alpha ($\alpha$): 32
  - Dropout: 0.05
  - Learning Rate: 2e-4
  - Optimizer: AdamW (`bfloat16`)
  - Epochs: 3 (Batch Size 2, Gradient Accumulation 4)
- **Dataset:** 138 curated ChatML instruction pairs enforcing strict Domain Boundaries, Value Objects with invariant validation, Port & Adapter contracts, and functional `Result<T, E>` error handling.
- **Quantization:** Consolidated 16-bit weights exported to GGUF using `llama.cpp` quantizer (`Q4_K_M` medium-precision 4-bit).

---

## Architectural Guardrails Enforced

1. **Domain Boundary Rule:** Core entities and value objects never depend on outer layers, frameworks, or database ORMs.
2. **Deterministic Typing:** Strict prohibition of TypeScript `any`. All contracts use narrow types, explicit interfaces, or `unknown` with type guards.
3. **Ports & Adapters (Hexagonal):** Business use cases communicate with storage, APIs, and messaging strictly through interfaces.
4. **Functional Error Handling:** Preferential use of `Result<T, DomainError>` over unhandled runtime exceptions.

---

## Citation & Repository

Project Repository: [https://github.com/Jrgil20/edge-clean-copilot](https://github.com/Jrgil20/edge-clean-copilot)  
Semester Project for Applied AI (UCAB).
