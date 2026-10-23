# Model Factory & Scalable SLM Specialization Architecture

> **Authoritative Technical Blueprint**  
> **Repository:** `edge-clean-copilot`  
> **Core Concept:** Decoupling foundational model evolution from domain specialization via a reproducible, hardware-aware Small Language Model (SLM) factory.

---

## 1. Architectural Vision: Moving from Checkpoints to a Model Factory

A common pitfall in applied AI engineering is treating model fine-tuning as a one-time script that produces a single static artifact. In the rapidly evolving landscape of open-weights SLMs (e.g., Qwen, Llama, Gemma, DeepSeek, SmolLM), any specific checkpoint is transient.

**Edge Clean Copilot is designed not as an isolated model, but as an industrialized Model Factory.**

The factory provides an end-to-end, automated pipeline that ingests new state-of-the-art foundation SLMs, applies domain-specific architectural adaptation (Clean Architecture and Domain-Driven Design invariants), quantizes weights for edge inference, and benchmarks the resulting model against strict determinism and software engineering quality metrics.

```
                  ┌────────────────────────────────────────────────────────┐
                  │              OPEN FOUNDATION SLMs POOL                 │
                  │ (Qwen2.5-Coder, Llama-3.2, Gemma-2, SmolLM2, DeepSeek) │
                  └───────────────────────────┬────────────────────────────┘
                                              │ Ingest Base Weights
                                              ▼
┌─────────────────────────┐       ┌───────────────────────────────┐
│ SYNTHETIC DATA FACTORY  │       │   LoRA SPECIALIZATION HARNESS │
│ • Anti-pattern tax.     │──────▶│   • Parameterized targets     │
│ • Canonical seeds       │ Pairs │   • Budget-capped (DGX Spark) │
│ • Invariant validator   │       │   • Automated weight merging  │
└─────────────────────────┘       └───────────────┬───────────────┘
                                                  │ Merged FP16 Weights
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │   EDGE QUANTIZATION ENGINE    │
                                  │   • llama.cpp conversion      │
                                  │   • GGUF formats: Q4_K_M, Q8  │
                                  └───────────────┬───────────────┘
                                                  │ Edge GGUF Artifact
                                                  ▼
┌─────────────────────────┐       ┌───────────────────────────────┐
│ HEXAGONAL CLI ADAPTER   │◀──────│   CLEAN ARCH SCORE (CAS)      │
│ • Air-gapped runtime    │ Server│   • Domain isolation (30%)    │
│ • Pure TS / Zero-any    │       │   • Result safety (25%)       │
│ • ANSI Terminal Diffs   │       │   • Ports & Adapters (25%)    │
└─────────────────────────┘       │   • Zero-any penalty (20%)    │
                                  └───────────────────────────────┘
```

---

## 2. The Five Decoupled Factory Subsystems

The factory is decomposed into five autonomous layers following Clean Architecture and Separation of Concerns:

### 2.1 Subsystem A: Domain Teacher & Synthetic Dataset Engine
- **Responsibility:** Generate, curate, and validate instruction-refactoring pairs illustrating Clean Architecture violations and their canonical resolutions.
- **Invariance:** Independent of the downstream training model. The dataset represents pure software engineering knowledge (domain isolation, value objects, ports/adapters, typed errors).
- **Core Assets:**
  - `dataset/seed_examples.jsonl`: Curated baseline pairs.
  - `dataset/validate_dataset.py`: Multi-stage syntax and structure validator.
  - `dataset/train.jsonl` & `dataset/eval_holdout.jsonl`: Deterministic splits (seed=42).

### 2.2 Subsystem B: Parameterized LoRA Training Harness
- **Responsibility:** Specialize open-weight foundations using Low-Rank Adaptation (LoRA) within controlled compute budgets.
- **Key Characteristics:**
  - **Model-Agnostic:** Target modules, hidden dimensions, and attention heads are configured dynamically via CLI arguments (`--base-model`, `--r`, `--alpha`, `--target-modules`).
  - **Burst-Safe:** Native wall-clock time caps (`--max-time-minutes`) preventing hardware preemption or thermal throttling on shared compute (e.g., DGX Spark).
  - **Atomic Merging:** Automatically merges LoRA delta weights into base weights upon completion (`--merge`).

### 2.3 Subsystem C: Quantization & Compression Engine
- **Responsibility:** Transform dense FP16 weights into edge-executable, cache-aligned GGUF binaries.
- **Quantization Matrix:**
  - `Q4_K_M`: Optimal edge default (~0.98 GB, fits in 1.5 GB RAM, high inference velocity ~58 t/s).
  - `Q8_0`: High-fidelity reference for server and developer workstation deployment.
- **Pipeline:** Automated via `training/convert_to_gguf.sh`.

### 2.4 Subsystem D: Evaluation & Architectural Calibration (CAS)
- **Responsibility:** Quantify model adherence to software engineering patterns via the **Clean Architecture Score (CAS, 0–100 points)**.
- **Evaluation Independence:** CAS tests both offline synthetic completions and live HTTP inference endpoints (`llama-server`) with zero bias toward model architecture.
- **Metric Breakdown:**
  1. *Domain Boundary Isolation (30%):* Absence of prohibited framework/ORM/HTTP imports in domain logic.
  2. *Invariant & Result Safety (25%):* Value Object integrity, defensive constructor guards, and functional `Result<T, E>`.
  3. *Port & Adapter Decoupling (25%):* Explicit interfaces and dependency injection.
  4. *Type Rigor (20%):* Explicit avoidance of `any` (-5 pts per violation) and strict TypeScript typings.

### 2.5 Subsystem E: Hexagonal Edge Client (CLI)
- **Responsibility:** Provide software developers with an air-gapped, zero-latency coding assistant that executes directly on developer laptops.
- **Design:** Written in strict TypeScript (Zero `any`), decoupling the inference protocol (`IInferenceEngine`) from the file system and CLI interface.

---

## 3. Recipe: Ingesting a New Foundation SLM

When a new foundation model is released (e.g., `Qwen/Qwen2.5-Coder-3B-Instruct`, `meta-llama/Llama-3.2-3B-Instruct`, or `google/gemma-2-2b-it`), follow this standardized sequence to produce a new specialized Edge Clean Copilot variant:

```bash
# Step 1: Pre-flight Dry-Run on DGX Spark (Validates Hugging Face download & tokenization)
python3 proyecto/training/train_lora.py \
  --base-model "Qwen/Qwen2.5-Coder-3B-Instruct" \
  --dry-run

# Step 2: Fine-Tuning Burst with Target LoRA Rank & Automatic Merge
python3 proyecto/training/train_lora.py \
  --base-model "Qwen/Qwen2.5-Coder-3B-Instruct" \
  --output-dir "output/clean-copilot-qwen3b" \
  --max-time-minutes 30.0 \
  --r 16 \
  --lora-alpha 32 \
  --merge

# Step 3: Quantize to Edge GGUF (Q4_K_M)
cd proyecto/training
./convert_to_gguf.sh \
  --model-dir output/clean-copilot-qwen3b \
  --output-name clean-copilot-3b-q4km.gguf \
  --clean-f16

# Step 4: Run CAS Benchmark Calibration
python3 proyecto/evaluation/eval_benchmark.py \
  --url "http://127.0.0.1:8085/v1/chat/completions" \
  --prompts proyecto/evaluation/legacy_benchmark_suite.jsonl \
  --output proyecto/evaluation/benchmark_report_qwen3b.json

# Step 5: Update Multi-Model Comparison Matrix
python3 proyecto/evaluation/compare_models.py \
  --candidate-report proyecto/evaluation/benchmark_report_qwen3b.json
```

---

## 4. Scalability Dimensions

| Dimension | Initial Baseline (v0.1) | Scaled Factory State (v1.0+) |
|---|---|---|
| **Base Model Scale** | Qwen 2.5 Coder 1.5B | 1B, 3B, 7B, MoE SLMs (e.g. Qwen, Llama, DeepSeek) |
| **Edge Footprint** | ~0.98 GB RAM / 58 t/s | Multi-tier: Ultra-Edge (0.5 GB) to Workstation (4 GB) |
| **Language Scope** | TypeScript / JavaScript | Polyglot (Go Clean Arch, Rust Hexagonal, Python DDD) |
| **Compute Targets** | Single NVIDIA DGX Spark (A100) | Distributed multi-GPU clusters, Apple Silicon MLX |
| **Inference Runtime** | llama.cpp (`llama-server`) | llama.cpp, vLLM, ONNX Runtime, WebGPU (in-browser) |

---

## 5. Architectural Invariance & Governance

To maintain platform consistency as new models are integrated:
1. **The Dataset is Truth:** New models must be fine-tuned against validated datasets (`validate_dataset.py`) to prevent domain drift.
2. **CAS is the Quality Gate:** No model variant is promoted to release without achieving `CAS >= 80.0` on the 30-case legacy benchmark suite.
3. **Decoupled Client:** The CLI client (`clean-copilot`) never contains model-specific parsing logic. It relies strictly on normalized ChatML standard completions via the `IInferenceEngine` interface.
