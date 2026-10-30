# Edge Clean Copilot (ECC)

> **Specialized, Edge-Native Small Language Model (SLM) & Hexagonal CLI for Strict Clean Architecture and Domain-Driven Design Refactoring.**

[![Phase Progress](https://img.shields.io/badge/Progress-70%25%20Verified-blue.svg)](docs/progress-and-milestones.md)
[![Architecture](https://img.shields.io/badge/Architecture-Hexagonal%20%2F%20Clean-emerald.svg)](propuesta.md)
[![Base Model](https://img.shields.io/badge/Base%20SLM-Qwen2.5--Coder--1.5B--Instruct-orange.svg)](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct)
[![Quantization](https://img.shields.io/badge/Edge%20Target-GGUF%20Q4__K__M%20(45--70%20tok%2Fs)-purple.svg)](training/convert_to_gguf.sh)
[![Tests](https://img.shields.io/badge/Vitest-41%2F41%20Passing-brightgreen.svg)](cli/tests/)
[![Web Portal](https://img.shields.io/badge/Docs-Interactive%20Portal-teal.svg)](docs/index.html)
[![License](https://img.shields.io/badge/License-Academic%20%2F%20MIT-lightgrey.svg)](README.md)

🌐 **[Versión en español disponible →](./es/README.md)**

---

## 1. Executive Summary

**Edge Clean Copilot (ECC)** is an offline, specialized AI coding assistant designed to enforce **Clean Architecture**, **Ports & Adapters (Hexagonal Architecture)**, and **Domain-Driven Design (DDD)** principles on edge developer workstations without requiring cloud API connections.

Mainstream commercial code LLMs frequently fail architectural boundaries: they inject `any` types, introduce circular layer dependencies, mix database SDKs directly into business entities, and hallucinate external framework couplings. ECC solves this by fine-tuning an agile Small Language Model (**Qwen2.5-Coder-1.5B-Instruct**) on high-signal architectural refactoring pairs, deploying it locally via **GGUF Q4_K_M** quantization served through `llama.cpp` at **~12 tokens/second** measured on a CPU-only laptop (Intel i5-10310U). It is slow on long inputs; review every output.

> **Key Architectural Value:** Beyond a single model checkpoint, ECC is designed as a reproducible **[Model Factory](docs/model-factory-architecture.md)**. The pipeline decoupled from specific model weights, allowing new open-weight SLMs (Llama-3.2, Gemma-2, DeepSeek) to be ingested, specialized, and edge-quantized through an automated, repeatable workflow.

---

## 2. Core Methodology: "Cold Staging, Hot Burst"

To reconcile shared multi-tenant AI infrastructure (such as university clusters) with independent local development, the project follows the **Cold Staging, Hot Burst** operational model:

```
[ Cold Staging (Local Developer Laptop) ]
  ├── Curation of canonical ChatML seed pairs
  ├── Deterministic stratified dataset partitioning (train/eval holdout)
  ├── 1-step offline dry runs (--dry-run)
  └── Offline unit testing of CLI layers via MockInferenceAdapter (28/28 green)
               │
               ▼ (Network Burst — SSH / Subnet /26)
[ Hot Burst (NVIDIA DGX Spark Cluster) ]
  ├── High-throughput Teacher distillation (Qwen3-Coder-30B on port 8085)
  ├── Multi-epoch LoRA fine-tuning (train_lora.py with --max-time-minutes 15.0)
  └── Consolidated weight merge (LoRA adapter + base model -> FP16)
               │
               ▼ (Artifact Consolidation)
[ Edge Deployment (100% Offline Local Machine) ]
  └── GGUF quantization (Q4_K_M) served via llama-server (zero cloud dependencies)
```

---

## 3. Subsystem Architecture

The repository is organized into five decoupled subsystems:

```
edge-clean-copilot/
├── cli/          # Hexagonal CLI client in TypeScript (Ports & Adapters, zero-any)
├── dataset/      # Canonical seeds, synthetic generator, and stratified partitions
├── training/     # PyTorch LoRA fine-tuning pipeline & GGUF export scripts
├── evaluation/   # Automated Clean Architecture Score (CAS 0-100) benchmark harness
├── docs/         # Technical specifications, telemetry logs, and execution roadmaps
├── es/           # Full documentation mirror in Spanish
└── status.py     # Zero-dependency instant diagnostic & session resume dashboard
```

### 3.1 Hexagonal CLI Subsystem (`cli/`)

The CLI client enforces strict Clean Architecture internally while refactoring user code externally:

```
cli/src/
├── domain/             # Enterprise business rules
│   └── entities/       # SourceFile entity (path validation, language invariants)
├── application/        # Application business rules
│   ├── use-cases/      # RefactorCodeUseCase (functional orchestration)
│   ├── ports/          # IInferenceEngine (abstract AI completion contract)
│   └── dtos/           # RefactorDTO (typed input/output structures)
├── infrastructure/     # External adapters & tools
│   ├── ai/             # LlamaServerAdapter (HTTP) & MockInferenceAdapter (offline unit testing)
│   ├── fs/             # FileDiskReader (deterministic file I/O)
│   └── cli/            # Commander.js entrypoint & terminal UI
└── shared/             # Cross-cutting primitives
    ├── types/          # Result<T, E> monad for deterministic error handling
    └── errors/         # DomainError typed hierarchy (zero untyped throws)
```

#### Non-Negotiable Architectural Guardrails
1. **The Dependency Rule:** Inner layers (`domain`, `application`) contain zero dependencies on outer layers (`infrastructure`, frameworks, file system, or network).
2. **Zero `any` Policy:** Explicit typing throughout; forbidden usage of `any`.
3. **Deterministic Error Monad:** Use cases return functional `Result<T, DomainError>` rather than throwing unhandled exceptions.
4. **100% Offline Testability:** The test suite runs completely offline via `MockInferenceAdapter` without requiring a live inference server.

### 3.2 Dataset Subsystem (`dataset/`)

- **Canonical Seed Examples (`dataset/seed_examples.jsonl`):** 8 hand-crafted, production-grade refactoring pairs extracted from real-world domain models (ArrowMaze).
- **Teacher Distillation Generator (`dataset/generate_with_teacher.py`):** Automated prompt pipeline interrogating a 30B teacher model (`Qwen3-Coder-30B-A3B-Instruct`) deployed on dedicated port `8085` of the NVIDIA DGX Spark cluster.
- **Stratified Partitioning (`dataset/split_dataset.py`):** Deterministic split (`seed=42`) creating:
  - `dataset/train.jsonl`: **138 pairs** (82.1%, ~156k tokens) for LoRA adaptation.
  - `dataset/eval_holdout.jsonl`: **30 pairs** (17.9%, ~35k tokens) strictly isolated for post-training validation (zero leakage).
- **Validation Engine (`dataset/validate_dataset.py`):** ChatML syntax and contract linter.

### 3.3 Training & Quantization Subsystem (`training/`)

- **Native PyTorch LoRA Pipeline (`training/train_lora.py`):**
  - **Base Foundation Model:** `Qwen/Qwen2.5-Coder-1.5B-Instruct`
  - **LoRA Configuration:** Rank $r=16$, $\alpha=32$, targeting all linear attention and MLP projections (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`).
  - **Hardware Acceleration:** Native `bfloat16` execution on Grace Blackwell GB10 GPU (`2.14.1+cu130`).
  - **Defensive Multi-Tenancy Guardrail:** Bounded execution cutoff (`--max-time-minutes 15.0`) preventing queue exhaustion.
  - **Weight Merge:** Automated `model.merge_and_unload()` export flag (`--merge`).
- **GGUF Export (`training/convert_to_gguf.sh`):** Automated pipeline converting merged FP16 PyTorch weights to GGUF `Q4_K_M` for local inference via `llama.cpp`.

### 3.4 Evaluation Subsystem (`evaluation/`)

The evaluation harness (`evaluation/eval_benchmark.py`) calculates the **Clean Architecture Score (CAS)** on a 0–100 scale:

| Component | Weight | Validation Rule |
| :--- | :--- | :--- |
| **Layer Isolation** | 25 pts | Domain entities have 0 imports from outer layers or external libraries. |
| **Inversion of Control** | 25 pts | Use cases interact with external adapters strictly through abstract interfaces (Ports). |
| **Zero `any` Compliance** | 25 pts | Generated TypeScript code contains 0 occurrences of explicit `any`. |
| **Typed Error Handling** | 25 pts | Functions return functional `Result<T, DomainError>` rather than untyped throws. |

---

## 4. Quickstart & Developer Workflow

### Prerequisites
- **Python:** 3.10+ (with PyTorch and Hugging Face tools if training)
- **Node.js & PNPM:** Node 20+, `pnpm` 10+ (mandatory package manager)

### 4.1 Instant Diagnostic Check
Inspect live project health, test suites, and partition counts at any time:
```bash
python3 status.py
```

### 4.2 Run CLI Unit Tests
The hexagonal TypeScript CLI includes 28 AAA unit tests:
```bash
cd cli
pnpm install
pnpm test
```

### 4.3 Validate Dataset Partitions
Ensure all ChatML pairs comply with schema standards:
```bash
python3 dataset/validate_dataset.py dataset/train.jsonl
python3 dataset/validate_dataset.py dataset/eval_holdout.jsonl
```

### 4.4 Run Clean Architecture Benchmark
Evaluate legacy code samples against the calibrated CAS rubric:
```bash
python3 evaluation/eval_benchmark.py \
  --cases evaluation/test_benchmark_cases.jsonl \
  --output evaluation/benchmark_report.json
```

---

## 5. Phase Completion & Verification Board

| Phase | Description | Scope | Status | Verified Metrics |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Infrastructure & Teacher Dataset | Weeks 1–3 | **100%** | Direct link `/26`, port 8085 isolated, 168 ChatML pairs partitioned (138 train / 30 holdout). |
| **Phase 2** | LoRA Adaptation & Specialization | Weeks 4–7 | **85%** | `train_lora.py` ready with time-bounding; virtualenv and 73% weights cached in DGX NVMe. |
| **Phase 3** | Weight Consolidation & GGUF Export | Weeks 8–11 | **50%** | Automated `convert_to_gguf.sh` pipeline verified and staged. |
| **Phase 4** | Hexagonal CLI & Offline Inference | Weeks 12–15 | **70%** | 28/28 Vitest unit tests green (~280ms); CAS benchmark harness calibrated. |
| **GLOBAL** | **Comprehensive Project Maturity** | **Overall** | **70%** | **Production-grade staging, ready for DGX Spark execution burst.** |

---

## 6. Technical Documentation Index

For deep-dive architecture specs, hardware runbooks, and telemetry:
- **[Detailed Execution Roadmap (Weeks 4–15)](docs/detailed-roadmap.md):** Tactical plan, milestones, and deliverables.
- **[Verified Progress Board](docs/progress-and-milestones.md):** Evidence-based milestone validation log.
- **[Session Report: 2026-10-22](docs/session-2026-10-22-burst-and-lessons.md):** Cluster telemetry, port isolation post-mortem, and dataset distillation metrics.
- **[Academic Technical Proposal](propuesta.md):** Theoretical foundation, research hypotheses, and academic articulation.
