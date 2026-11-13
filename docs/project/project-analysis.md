# Project Analysis: Edge Clean Copilot

> **Date:** 2026-11-13
> **Purpose:** a complete and verifiable account of the project to cite as background (prior work) for a later thesis. This project is not the thesis itself. The document covers its objectives, its ideas, what worked, what did not, and which claims the evidence supports.
> **Method:** every figure below was re-measured from the repository on this date: test suites run, dataset files counted, the published training split and training code recovered from git history, and the committed benchmark completions re-analysed (paired statistics, standalone type-checking). Scripts were run locally. No model was queried.
> **Related:** [evaluation audit (2026-11-05)](../evaluation/evaluation-audit-2026-11-05.md), [next steps](../next-steps.md), [valid use cases](../usage/use-cases.md).

---

## 1. Summary

Edge Clean Copilot (ECC) is a LoRA fine-tune of `Qwen2.5-Coder-1.5B-Instruct`. It is merged, quantized to GGUF Q4_K_M (941 MB) and served offline with `llama.cpp`. A hexagonal TypeScript CLI drives it.

**Supported by the evidence:**

- The full pipeline works end to end: teacher-generated data, LoRA training on a shared GPU, merge, GGUF export, local serving, a CLI and an attributed benchmark.
- On the project's own 30-case suite, the fine-tune beats its base model by **+16.8 CAS points** (74.8 vs 58.0). The 95% bootstrap confidence interval is [10.0, 25.2]. The fine-tune wins 24 cases, ties 6 and loses none.

**Not supported by the evidence:**

- The proposal's hypothesis that the model can outperform commercial or frontier models. No such model was ever run on the suite.
- That the output is correct code. The metric checks patterns, not compilation or behavior.
- That it is fast on a laptop. Measured speed is about 12 tok/s, roughly 47 s per answer.
- That the result generalizes beyond short, synthetic snippets. Suite inputs are 3–18 lines long.

**Where the main weakness is:** the training data. The published model learned from **18 distinct prompts** (138 rows). 35% of the training answers are truncated and 15% contain explicit `any`. Only 4 distinct prompts ask the model to refactor given code, which is the task the benchmark measures.

**Overall:** the proposal is mainly about the **process**: how to specialise, package and evaluate a small model on limited, shared hardware. On that it holds up well: every stage exists, is scripted and was executed (§3.5). The model is one output of the process. It is a credible proof of concept, not evidence that a small model rivals large ones. Framed that way, the project is solid prior work to cite, and its limitations define concrete follow-up work.

---

## 2. Objectives: planned vs achieved

The planned objectives come from [propuesta.md](./propuesta.md) and the proposal's §4 schedule.

| # | Objective (as proposed) | Status | Evidence |
| :-- | :-- | :-- | :-- |
| O1 | Fine-tune an SLM (1.5B–3B) with LoRA on Clean Architecture pairs | **Done for 1.5B.** 3B not trained. | `training/train_lora.py`; final loss 0.031 (progress log). |
| O2 | Export GGUF Q4_K_M (and Q5_K_M, Q8_0) | **Done.** Q5/Q8 exported but never benchmarked. | 941 MB Q4_K_M, SHA-256 `d2deae65…` in the reports. |
| O3 | 35–70 tok/s on a commodity laptop | **Not met.** | About 12 tok/s on an i5-10310U. The laptop benchmark took 1,419 s for 30 answers (about 47 s each). |
| O4 | Hexagonal CLI (Ports & Adapters) with a mock engine | **Done.** | `cli/`, 44 Vitest tests passing. |
| O5 | Constrain output with deterministic grammars (GBNF / type schemas) | **Not done.** | No grammar is used anywhere in the pipeline. |
| O6 | Measure convergence, loss and catastrophic forgetting | **Partly done.** Training loss only. | No validation loss and no forgetting test. |
| O7 | Benchmark speed and memory on a laptop | **Partly done.** | Speed measured once; RAM (~1.5 GB) is quoted, not logged. |
| O8 | Show the SLM beats general commercial models at Clean Architecture adherence (hypothesis) | **Not tested.** | No frontier, teacher or few-shot baseline exists. The 90.5 "frontier" figure has no run behind it (audit F3/F8). |
| O9 | Publish weights on Hugging Face, with CI/CD and documentation | **Partly done.** | Upload script and model card exist; publication was not verified from the repo; there is no CI (no `.github/`). |
| O10 | Replicable on Colab T4 / 6 GB GPUs via QLoRA | **Not tested.** | No QLoRA path in `train_lora.py`. |
| O11 | "Model Factory" for other base models | **Designed, not run.** | Llama-3.2 and Gemma-2 recipes exist; neither was trained. |

---

## 3. The ideas

### 3.1 Core idea

**Put architectural conventions into the weights of a small model that runs offline,** instead of prompting a large cloud model. Two motivations are given:

- **Architectural drift:** general assistants couple domain code to frameworks.
- **Privacy and cost:** proprietary code should not leave the machine.

The idea is sound and current. Small, specialised, locally run models are an active line of work.

The weak link is the assumption that **a small dataset can teach architecture rather than surface form**. With 18 prompts, the model learned a template: an interface, a class with a private constructor and a static `create`, and no framework imports. It did not learn a transferable skill. The measured profile shows this (§5.3 E7).

### 3.2 "Cold Staging, Hot Burst"

All work that does not need a GPU was done on a laptop. The shared DGX Spark was used only in short, time-capped windows, with explicit care not to disturb other tenants (ports 8080/8084 untouched, a memory-fraction cap, `--max-time-minutes`).

This is one of the project's most transferable contributions. It is a documented operating method for constrained, shared academic hardware ([session log](../history/session-2026-10-22-burst-and-lessons.md)).

### 3.3 Alternatives considered

The alternatives are listed in [ideas.md](./ideas.md):

- **RAG over architecture literature:** rejected because the patterns are not internalised in the weights.
- **Model-assisted linters:** deferred.

In hindsight, a **linter or AST checker combined with a model** is the most natural extension. The project already has an AST analyzer, and the measured weaknesses (correctness, invariants) are exactly what a deterministic checker can verify.

### 3.4 Teacher distillation

`Qwen3-Coder-30B` generated training pairs from a small set of templates. This is standard practice. Here, however, the templates were few and the teacher's outputs were never verified, so the teacher's errors (truncation, `any`, non-compiling code) went straight into training (§5.1).

### 3.5 The process is the main contribution

The proposal is mostly about a **process**: how to specialise, package and evaluate a small model with limited, shared hardware. The model is one output of that process. Judged stage by stage:

| Stage | What exists | Repeatable from the repo? | Main gap |
| :-- | :-- | :-- | :-- |
| 1. Seed and teacher data | Seeds from a real project, a time-capped teacher generator and a format validator | Yes, given a teacher endpoint | No quality gate (compile, `any`, truncation) between teacher and training set (D3–D5) |
| 2. Split and audit | Deterministic prompt-disjoint split, leakage audit, unit tests | Yes, fully offline | Added after the published run; too few distinct prompts (D1, D9) |
| 3. Training burst | Recipe-driven LoRA, time cap, memory cap, completion-only loss, merge | Yes, with a GPU; `--dry-run` on CPU | No validation loss; run parameters were not recorded with the run (T1–T3) |
| 4. Export and serving | GGUF Q4/Q5/Q8 script, `llama-server` on isolated ports | Yes, given `llama.cpp` | Only Q4_K_M evaluated |
| 5. Evaluation | Attributed benchmark, AST scoring, one-command Spark run, checks for empty answers and failures | Yes | The metric checks patterns, not correctness; no baselines beyond the base model (E1–E9) |
| 6. Client | Hexagonal CLI, mock engine, 44 tests | Yes, fully offline | Timeout and output handling on CPU (C1, C2); no CI |
| 7. Operations on shared hardware | Port isolation, curfew-aware time caps, runbooks, session logs | Yes, documented | Depends on lab-specific paths and hosts |

**Reading:** every stage exists, is scripted and is documented. The weakest links are the two **quality gates**: data entering training (stage 1) and outputs leaving the model (stage 5). Both can be fixed without retraining the published model. That makes them a natural scope for follow-up work.

---

## 4. What is right

| Area | Strength | Evidence |
| :-- | :-- | :-- |
| Pipeline | Complete and reproducible in structure: data, training, merge, GGUF, serving, CLI and benchmark all exist and connect through files. | Repository layout; [README](../../README.md) §2. |
| Measured gain | The fine-tune beats the base on every CAS component. The paired difference is robust within this metric: mean +16.8, SD 21.5, t ≈ 4.3, bootstrap 95% CI [10.0, 25.2], 24 wins / 6 ties / 0 losses. | `evaluation/reports/spark-20261105T143540Z/` |
| Fair comparison | Same suite, same quantization, same server settings, same scoring engine; models identified by SHA-256; 0 failed or empty answers. | `RESULT.md`, report `meta` blocks. |
| CLI engineering | Hexagonal layering is respected: `domain/` and `application/` have no infrastructure imports. Errors are values (`Result<T, E>`), TypeScript is strict with no `any`, and 44 tests run offline against a mock engine. | `cli/`; `pnpm test`. |
| Attribution and audit trail | Reports record model name, file hash, endpoint, suite and failures. An audit script checks leakage. The project corrected its own earlier claims in commits. | `eval_benchmark.py` `meta`; `audit_dataset.py`; commits `13fab38`, `aab8d9b`. |
| Responsible use of shared hardware | Never touches other tenants' ports; caps memory and wall-clock time; no automated destructive operations. | `spark_day.sh`, `train_lora.py`, session log §5. |
| Data hygiene, current version | The current split is prompt-disjoint (0/34 holdout prompts in train) and drops truncated answers. The suite shares no prompts or code with training. | `python3 dataset/audit_dataset.py`. |
| Tests | 44 Vitest tests and the Python stdlib tests pass (the training-loop test skips without torch). | Run on 2026-11-13. |

---

## 5. What is wrong

Severity reflects impact on the claims that can be cited from this project.

### 5.1 Dataset (highest priority)

The published model was trained on `dataset/train.jsonl` at commit `64f3c6c`.

| ID | Severity | Finding | How to reproduce |
| :-- | :-- | :-- | :-- |
| D1 | High | **18 distinct prompts** behind 138 rows; the most repeated prompts appear 13 times. The model sees few tasks many times. | `git show 64f3c6c:dataset/train.jsonl`, count distinct user messages. |
| D2 | High | **Task mismatch.** Only 42 rows (4 distinct prompts) ask to refactor given code. The rest ask the model to write new entities, value objects, ports or tests from a description. Every benchmark case is a refactoring. | Classify user prompts by their opening verb. |
| D3 | High | **49/138 answers (35%) are truncated**: an odd number of code fences, ending mid-code. The model was trained to produce cut-off answers. (The current `split_dataset.py` drops these.) | Count answers with an odd number of fences. |
| D4 | Medium | **20/138 answers contain explicit `any`** (e.g. `(mockRepository as any)`, `private stripe: any`), although the project's rule is zero `any`. | `grep` for `: any`, `as any`, `<any>`. |
| D5 | Medium | **Answers are unverified.** Of the 107 answers with closed TypeScript blocks, 82 type-check in isolation (strict; imports and unresolved names ignored), so about 1 in 4 has real type errors. Nothing checks behavior. | `python3 dataset/audit_dataset.py --typecheck` (see §7). |
| D6 | Medium | **Off-target content**: 13 rows are Python (FastAPI/SQLAlchemy) in a TypeScript project. | Count fence languages. |
| D7 | Medium | **Learned patterns do not transfer.** 120/138 answers use `Result`, yet the fine-tune uses `Result` in 2/30 benchmark answers. The pattern was learned for "write a use case", not for "refactor this class". | Compare training answers with Spark completions. |
| D8 | Medium | **The old holdout was contaminated**: 28/30 holdout prompts also appear in train (audit F1). Evaluation therefore relies only on the 30-case suite. | `audit_dataset.py` on `64f3c6c`. |
| D9 | Low | **The current split is better but still small**: 91 train rows (28 distinct prompts) and 34 holdout rows (8 distinct prompts); one prompt is still repeated 14 times. It has not been trained on. | `python3 dataset/audit_dataset.py`. |

### 5.2 Training

| ID | Severity | Finding | Evidence |
| :-- | :-- | :-- | :-- |
| T1 | Medium | **The documented hyperparameters differ from the code that trained the model.** The published run used per-device batch **1** (hard-coded in the DataLoader), so the effective batch was **4**, not 8: about 105 optimizer steps. The learning rate was **constant**, with no warmup and no cosine decay. No seed was set. The docs (final report, roadmap, model card) state batch 2, effective 8 and a cosine schedule. | `git show fb3e812:training/train_lora.py` (DataLoader `batch_size=... else 1`; no scheduler). |
| T2 | Medium | **No validation loss and no early stopping.** A final training loss of 0.031 on 18 distinct prompts indicates memorization. | Training log in the progress doc. |
| T3 | Medium | **HEAD no longer reproduces the published model.** The training fixes of 2026-11-08 (seed, warmup, weight decay, batch wiring) and the new split mean a rerun from HEAD trains a different model. Exact reproduction needs data `64f3c6c` + code `fb3e812`. | `git log -- training/train_lora.py`. |
| T4 | Low | **Context length differs between docs and recipe.** The roadmap and final report say 1,024 tokens; the recipe says 2,048. Answers longer than the limit were silently truncated by the tokenizer. | `recipes/qwen2.5-coder-1.5b.yaml`. |

### 5.3 Evaluation and the CAS metric

| ID | Severity | Finding | Evidence |
| :-- | :-- | :-- | :-- |
| E1 | High | **An empty answer scores 50/100**: 30 points for no forbidden imports plus 20 for no `any`. Read 74.8 as roughly 25 points above doing nothing, and 58.0 as 8 above it. | `test_empty_output_scores_fifty_floor`. |
| E2 | High | **The "ports" component counts any `interface` or `type` alias**, including props and DTOs. It does not check naming (`I…Repository`) or constructor injection, although the docs say it does. Of the fine-tune's 91 detected "contracts", about 37 have port-like names. | `evaluation/ast_analyzer.ts`, ports block; report notes such as `Port: UserAccountProps`. |
| E3 | Medium | **The "invariants" component is shallow.** A guard is any `if` or `throw` directly in a constructor. "Result" is any type reference whose name contains `Result`. | `ast_analyzer.ts`. |
| E4 | Medium | **The boundary score rewards omission.** Only 4/30 fine-tune answers contain any import at all, versus 23/30 for the base. The full 30/30 boundary score partly comes from leaving imports out, and nothing checks that the original functionality is still there. | Spark completions. |
| E5 | High | **Compilation and behavior are not part of the score.** A standalone type-check (strict; imports and unresolved names ignored) passes **14/30 fine-tune** answers and **17/30 base** answers. Neither has syntax errors. The fine-tune is **not** better at producing type-correct code, and no behavior check exists. | §7. |
| E6 | Medium | **Suite validity.** The suite has 30 cases, all written by the author and all opening with the same instruction. Inputs are **3–18 lines (median 8.5)**. Results say nothing about real files. | `legacy_benchmark_suite.jsonl`. |
| E7 | Medium | **The fine-tune converges on one template.** 26/30 of its scores fall between 65 and 75. Invariant safety is 0 in 26/30 cases. Almost all of the gain comes from boundary (+6.0) and ports (+6.7); invariants add +2.4. | Report score distributions. |
| E8 | Medium | **The evaluation prompt differs from use and training.** The benchmark sends only a user message. Training and the CLI both use a system prompt. | `eval_benchmark.py` payload; `RefactorCodeUseCase.ts`. |
| E9 | High | **No baselines beyond the raw base model.** There is no few-shot-prompted base, no 30B teacher and no frontier model. Without them, the hypothesis (O8) cannot be evaluated. | Audit F3, F8. |
| E10 | Low | **Run-to-run noise.** The same GGUF scored 72.5 (laptop) and 74.8 (Spark): 17/30 cases identical, mean per-case difference 4.7. An unattributed earlier run (76.3) differs by 17.8 points per case. | Laptop and Spark reports. |

### 5.4 CLI and tooling

| ID | Severity | Finding | Evidence |
| :-- | :-- | :-- | :-- |
| C1 | Medium | **On CPU, the CLI will time out on longer answers.** The adapter's timeout is 60 s by default and has no CLI flag; `maxTokens` defaults to 2,048. At about 12 tok/s, any answer over about 700 tokens exceeds the timeout. | `LlamaServerAdapter.ts`; `infrastructure/cli/index.ts`. |
| C2 | Medium | **`-o` writes the raw model reply** (Markdown fences and prose) into the target `.ts` file. No code block is extracted. | `index.ts` writes `refactoredCode` as returned. |
| C3 | Low | **The default URL is `127.0.0.1:8080`.** That is fine on a laptop, but on the Spark it is another tenant's server. | `index.ts`. |
| C4 | Low | **No CI.** Tests exist but nothing runs them automatically. | No `.github/`. |
| C5 | Low | **The VS Code Copilot routing (`copilot-local`) is unevaluated.** Routing inline completions to a chat-tuned model that was never trained on fill-in-the-middle has not been measured. | `bin/copilot-local`. |

### 5.5 Documentation and claims (errata)

These statements are still in the repository and should **not** be cited as written:

| Where | Statement | Correction |
| :-- | :-- | :-- |
| [propuesta.md](./propuesta.md) | 35–70 tok/s on laptops; GBNF-constrained output | About 12 tok/s measured; no grammar was implemented. |
| [final-report-and-presentation.md](./final-report-and-presentation.md) | Hypothesis and conclusion claim superiority over frontier models | Not tested (E9). |
| Same | Cosine schedule; effective batch 8; 1,024 tokens; 34 tests; "zero data leakage" heading | Constant LR, effective batch 4 (T1); 2,048 tokens (T4); 44 tests now; old holdout leaked (D8). |
| [MODEL_CARD.md](../../MODEL_CARD.md) | Frontier 90.5; "eradicates 100%" of prohibited imports; hardware "GB10 / Ampere A100"; batch 2 × accum 4 | 90.5 unmeasured (F3); 30/30 on a 30-case suite, partly by omission (E4); GB10 only; effective batch 4. |
| [progress-and-milestones.md](../history/progress-and-milestones.md), `status.py` | "100% complete"; older test counts; stale Spark status | Proof of concept; see this document. |
| [detailed-roadmap.md](../history/detailed-roadmap.md) | Cosine schedule; 1,024 tokens; 3B burst | Not as executed. |

---

## 6. What can be cited safely

**Supported claims:**

1. A LoRA-tuned 1.5B model, quantized to 4 bits, runs fully offline on a CPU-only laptop at about 12 tok/s with about 1 GB on disk.
2. On a 30-case, self-authored TypeScript refactoring suite scored by an AST pattern metric, it scores 74.8 vs 58.0 for its base model under identical conditions (95% CI of the difference: [10.0, 25.2]). Most of the gain is in dropping framework imports and declaring interfaces.
3. The "Cold Staging, Hot Burst" method made it possible to train and evaluate on a shared GPU in short windows without disturbing other users.

**Claims to avoid:**

- That it outperforms, matches or approaches frontier or commercial models.
- That it produces correct or behavior-preserving refactorings, or more type-correct code than its base (14/30 vs 17/30 type-check).
- That it is fast.
- That the training data was large, diverse, verified or leakage-free (for the published model).

---

## 7. Reproducing the figures in this document

```bash
# Tests
cd cli && pnpm install && pnpm test                    # 44 passed
python3 -m unittest discover -s evaluation/tests -v
python3 -m unittest dataset/test_split_dataset.py -v

# Published training split vs current split
git show 64f3c6c:dataset/train.jsonl > /tmp/train_published.jsonl
python3 dataset/audit_dataset.py                       # current split: 0/34 overlap

# Training code that produced the published model
git show fb3e812:training/train_lora.py | grep -n "batch_size=2 if dry_run"

# Benchmark evidence
cat evaluation/reports/spark-20261105T143540Z/RESULT.md
```

The paired statistics (bootstrap with 10,000 resamples, seed 0) and the standalone type-check used the committed completions in `evaluation/reports/spark-20261105T143540Z/cas/`. The type-check used the TypeScript compiler from `cli/node_modules` with `strict: true`, targeting ES2022 + DOM. Because the snippets are fragments, `import` and `export … from` statements are blanked before checking (answers often hold several files in one block that import each other), and diagnostics for unresolved modules and names (TS2304, TS2307 and related) are ignored. The check is committed as `dataset/typecheck_answers.mjs` and runs on dataset answers with `python3 dataset/audit_dataset.py --typecheck`.

> **Correction (2026-11-13):** an earlier version of this document used a check that did not blank imports. Those imports collided with declarations in the same snippet, which understated pass rates: it reported 46/107 for the published training answers (now 82/107) and 12/30 vs 5/30 for the benchmark (now 14/30 vs 17/30). That earlier version wrongly listed type-correctness as a strength of the fine-tune.

---

## 8. Directions that follow from this analysis

In order of value for follow-up work:

1. **Data first.** Build 150–200 distinct refactoring tasks from real code. Verify each answer with `tsc --noEmit` and the AST analyzer, with no `any` and no truncation. Keep a prompt-disjoint holdout.
2. **Better metric.** Add compilation and behavior checks to CAS. Score ports by naming and injection. Subtract the empty-answer floor.
3. **Real baselines.** A few-shot-prompted base model, the 30B teacher and one frontier model, all on the same suite. This is the only way to test the original hypothesis.
4. **Hybrid system.** Model plus deterministic checker (or GBNF): the checker rejects or repairs outputs that do not compile. This revives the deferred linter idea.
5. **Retrain** only after 1–3, with validation loss, a fixed seed and the hyperparameters recorded with the run.
