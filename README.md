# Edge Clean Copilot (ECC)

> **Proof of concept:** a small language model (Qwen2.5-Coder-1.5B-Instruct + LoRA) that runs offline as a GGUF file and refactors small TypeScript snippets toward Clean Architecture / DDD, plus a hexagonal CLI to drive it.

[![Status](https://img.shields.io/badge/Status-Proof%20of%20Concept-yellow.svg)](docs/next-steps.md)
[![Base Model](https://img.shields.io/badge/Base-Qwen2.5--Coder--1.5B--Instruct-orange.svg)](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct)
[![Quantization](https://img.shields.io/badge/GGUF-Q4__K__M%20(~12%20tok%2Fs%20CPU)-purple.svg)](training/convert_to_gguf.sh)
[![Tests](https://img.shields.io/badge/Vitest-44%20passing-brightgreen.svg)](cli/tests/)
[![License](https://img.shields.io/badge/License-Academic%20%2F%20MIT-lightgrey.svg)](README.md)

🌐 **[Versión en español disponible →](./es/README.md)**

---

## 1. What this is (and what it is not)

ECC tests one idea: **can a 1.5B-parameter model, fine-tuned on a small set of architecture examples, produce code that follows Clean Architecture conventions more often than its base model, while running offline on a laptop CPU?**

On the project's own benchmark the answer is a qualified yes (see §3). The model was trained, merged, quantized to GGUF and served with `llama.cpp`; the full pipeline is in this repository.

It is **not** a production tool:

- The training data is small and repetitive (18 distinct prompts behind 138 training rows).
- The benchmark measures whether output *looks* architecturally clean (patterns such as ports, `Result`, no `any`), not whether it compiles or preserves behavior.
- Results come from one self-authored 30-case suite. No frontier model has been run on it.
- It is slow by design: about 12 tokens/second on a CPU-only laptop (Intel Core i5-10310U). It is meant for small, bounded snippets.

Known problems and the work to address them are listed in **[docs/next-steps.md](docs/next-steps.md)**.

---

## 2. How it was built: "Cold Staging, Hot Burst"

GPU time was available only in short windows on a shared NVIDIA DGX Spark (GB10). Everything that does not need a GPU was prepared on a laptop first:

```
[ Cold Staging: laptop ]
  ├── Hand-written seed examples (ChatML)
  ├── Deterministic train/holdout split (seed=42)
  ├── 1-step training dry runs (--dry-run)
  └── CLI unit tests against a mock inference engine
               │
               ▼
[ Hot Burst: DGX Spark ]
  ├── Teacher generation of training pairs (Qwen3-Coder-30B)
  ├── LoRA fine-tuning, time-capped (--max-time-minutes 15)
  └── Merge adapter into base weights (FP16)
               │
               ▼
[ Edge: laptop, offline ]
  └── GGUF Q4_K_M served by llama-server
```

---

## 3. Measured results

Head-to-head run on the DGX Spark, same suite, same quantization (Q4_K_M), same `llama-server` settings, AST scoring engine. Evidence: [`evaluation/reports/spark-20261105T143540Z/`](evaluation/reports/spark-20261105T143540Z/RESULT.md).

| CAS component (max) | Fine-tune | Base | Delta |
| :--- | ---: | ---: | ---: |
| Domain boundary (30) | 30.0 | 24.0 | +6.0 |
| Invariant safety (25) | 2.7 | 0.3 | +2.4 |
| Ports decoupling (25) | 22.5 | 15.8 | +6.7 |
| TypeScript typing (20) | 19.7 | 17.8 | +1.9 |
| **Composite CAS (100)** | **74.8** | **58.0** | **+16.8** |

How to read these numbers:

- **An empty answer scores 50.** It earns 30 for having no forbidden imports and 20 for having no `any`. The base model is 8 points above doing nothing; the fine-tune is about 25 above it. Neither run produced empty or refusal outputs.
- **Invariant safety is weak in both models** (2.7 / 25). The fine-tune rarely produces validated constructors or `Result` handling.
- **Run-to-run noise is real.** The same GGUF (same SHA-256) scored 72.5 on the laptop CPU and 74.8 on the Spark GPU, with 17/30 cases identical and a mean per-case difference of 4.7 points. An earlier run without model attribution scored 76.3 and differed from the laptop run by 17.8 points per case. Differences under about 5 points should be treated as noise.
- **Not yet measured:** whether the code compiles, whether behavior is preserved, how a prompted (few-shot) base model scores, and how the 30B teacher or a frontier model scores.

Full audit: [docs/evaluation/evaluation-audit-2026-11-05.md](docs/evaluation/evaluation-audit-2026-11-05.md).

---

## 4. Repository layout

```
edge-clean-copilot/
├── cli/          # TypeScript CLI (hexagonal: domain / application / infrastructure)
├── dataset/      # ChatML examples, teacher generator, split and audit scripts
├── training/     # LoRA training (recipe-driven) and GGUF export
├── evaluation/   # CAS benchmark harness, suites and attributed reports
├── docs/         # Runbooks, audit, progress logs
├── es/           # Spanish mirror of the documentation
└── status.py     # Quick project status dashboard
```

### 4.1 CLI (`cli/`)

A small TypeScript CLI that reads a file, sends it to a `llama-server` endpoint (or a mock engine), and prints or writes the refactored result. It follows the conventions the model is trained to produce:

- `domain/` and `application/` do not import from `infrastructure/` or third-party packages.
- Inference goes through a port (`IInferenceEngine`), with `LlamaServerAdapter` and `MockInferenceAdapter` as adapters.
- Functions return `Result<T, E>` with typed errors instead of throwing.
- Strict TypeScript, no `any`. All tests run offline against the mock engine.

### 4.2 Dataset (`dataset/`)

ChatML JSONL (`system` / `user` / `assistant`).

| Source | Rows | Notes |
| :--- | ---: | :--- |
| `seed_examples.jsonl` | 8 | Hand-written, taken from a real project (ArrowMaze). |
| `generated_examples.jsonl` | 160 | Generated by the 30B teacher from a small set of prompt templates. |
| `authored_examples.jsonl` | 19 | Hand-written `ARCH_REFACTOR` and `SOLID_CRITIQUE` examples, added after training. |
| `claude_authored_examples.jsonl` | 20 | Pilot batch of `ARCH_REFACTOR` examples written by Claude (Opus 5.5) in a Claude Code session, one per distinct task, added after training. Pending manual review. |

**The published model was trained on an earlier split** (commit `64f3c6c`): 138 training rows built from only **18 distinct prompts**, with a holdout that shared 28 of its 30 prompts with training. That split is no longer in the working tree.

The current `split_dataset.py` splits by normalized prompt and drops answers that are truncated, contain explicit `any` or fail an isolated `tsc` type-check. Rerunning it gives 88 training / 15 holdout rows from 53 distinct prompts, with no prompt overlap (`python3 dataset/audit_dataset.py`). **This split has not been used for training.**

The evaluation suite (`evaluation/legacy_benchmark_suite.jsonl`, 30 cases) shares no prompts or code with the training data.

### 4.3 Training (`training/`)

- Base: `Qwen/Qwen2.5-Coder-1.5B-Instruct`. LoRA r=16, α=32 on all attention and MLP projections, bfloat16.
- Hyperparameters live in recipe files (`training/recipes/*.yaml`); CLI flags override them.
- Published run: 3 epochs, about 5.5 minutes on the GB10; final training loss 0.031. No validation loss was tracked. A loss that low on 18 distinct prompts points to memorization.
- `--merge` merges the adapter into the base weights; `convert_to_gguf.sh` exports Q4_K_M (941 MB), with optional Q5_K_M and Q8_0.

### 4.4 Evaluation (`evaluation/`)

`eval_benchmark.py` computes the **Clean Architecture Score (CAS, 0–100)** using the TypeScript compiler AST (`ast_analyzer.ts`), with a regex fallback:

| Component | Points | Rule |
| :--- | ---: | :--- |
| Domain boundary | 30 | No imports of frameworks/ORMs (`express`, `typeorm`, `prisma`, `axios`, …). |
| Invariant safety | 25 | `Result` usage and constructor validation guards. |
| Ports decoupling | 25 | `interface I…Repository/Port/Gateway` and constructor injection. |
| TypeScript typing | 20 | −5 per explicit `any`. |

This is pattern matching. It does not compile the output or check that behavior is preserved. Reports record the model name, GGUF SHA-256, endpoint and suite so each score can be traced to a model.

---

## 5. Quickstart

Requirements: Python 3.10+, Node 20+, `pnpm` 10+. Training additionally needs PyTorch and the packages in `training/requirements.txt`.

```bash
python3 status.py                          # project status

cd cli && pnpm install && pnpm test        # CLI tests (offline)

python3 -m unittest discover -s evaluation/tests -v
python3 -m unittest dataset/test_split_dataset.py -v
python3 -m unittest dataset/test_audit_dataset.py -v

python3 dataset/validate_dataset.py dataset/train.jsonl
python3 dataset/audit_dataset.py --typecheck   # duplicates, leakage, truncation, any, tsc
```

### 5.1 Refactor a file

Requires `llama-server` running the GGUF (default `http://127.0.0.1:8080`), or `--mock` to test without a model. `bin/` must be on your `PATH`.

```bash
clean-copilot refactor path/to/File.ts --diff
clean-copilot refactor path/to/File.ts -o path/to/RefactoredFile.ts
clean-copilot refactor path/to/File.ts --mock
```

### 5.2 Route VS Code Copilot to a local model

`bin/copilot-local` edits `debug.overrideProxyUrl` in `~/.config/Code/User/settings.json`. Reload the VS Code window after switching.

```bash
copilot-local on        # ECC on the Spark (port 8085)
copilot-local on qwen   # Qwen3-Coder 30B on the Spark (port 8080)
copilot-local status
copilot-local off       # back to GitHub's service
```

---

## 6. Further documentation

- [Project analysis](docs/project/project-analysis.md): objectives vs results, strengths, findings and safe claims (for citing the project as prior work).
- [Valid use cases](docs/usage/use-cases.md): where to use the model and where not.
- [docs/next-steps.md](docs/next-steps.md): known problems and planned work.
- [Evaluation audit](docs/evaluation/evaluation-audit-2026-11-05.md): findings behind the caveats above.
- [Spark evaluation runbook](docs/evaluation/spark-eval-runbook.md) and [Spark day plan](docs/evaluation/spark-day-plan.md): how the head-to-head run was produced.
- [Model card](MODEL_CARD.md) and [usage and sharing guide](docs/usage/model-usage-and-sharing-guide.md).
- [Model Factory architecture](docs/architecture/model-factory-architecture.md): recipe-driven design for training other base models (Llama-3.2, Gemma-2 recipes exist but have not been trained).
- [Progress log](docs/history/progress-and-milestones.md) and [academic proposal](docs/project/propuesta.md).
