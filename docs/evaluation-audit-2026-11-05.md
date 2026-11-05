# Evaluation Audit — 2026-11-05

> **Status:** findings from a read-only audit; remediation is scheduled in [spark-eval-runbook.md](./spark-eval-runbook.md).
> **Scope:** CLI tests, benchmark reports, dataset split, comparison tooling.
> **Method:** commands run locally against the repository; the DGX Spark was offline, so no model was queried.

## 1. Verified

| Claim | Evidence |
| :--- | :--- |
| 41 CLI tests pass | `cd cli && pnpm test` → 8 files, 41 passed. |
| ECC score 76.3 has a raw report | `evaluation/benchmark_report_edge_copilot.json`: `total_samples=30`, `average_score=76.33`. |
| Legacy suite is disjoint from training data | 0/30 suite prompts and 0/30 suite code blocks appear in `dataset/train.jsonl`. |
| Category sub-scores sum to the composite | e.g. ECC 30.0 + 11.7 + 16.0 + 18.7 = 76.4 (rounding). |
| `DEMO_DATA["ecc"]` sub-scores match the raw report | Recomputed from `benchmark_report_edge_copilot.json`: 30.0 / 11.67 / 16.0 / 18.67. |
| Training uses completion-only loss masking | `training/train_lora.py` collator masks everything before the assistant response. |

## 1b. Re-measurement on the laptop (first attributed run)

| Item | Value |
| :--- | :--- |
| Model | `clean-copilot-1.5b-q4_k_m.gguf`, SHA-256 `d2deae65...` (CPU, `llama-server -ngl 0 -c 4096`) |
| Suite / engine | `legacy_benchmark_suite.jsonl`, AST engine, temperature 0.1 |
| Result | **CAS 72.5** (n=30, 0 failed prompts, 0 empty outputs); grades A:3, B:23, C:4 |
| Earlier unattributed run | 76.33 (a 73.8 reproduction is cited in the final report) |
| Per-case agreement with the 76.33 run | 4/30 identical, mean absolute difference 17.8 points |
| Evidence | `evaluation/reports/laptop-ft-20261105T051232Z/` |

Reading: the fine-tune produces real code and scores around 72-76, but run-to-run variation per case is large, so differences under ~5 points are noise. The base-model comparison still requires the Spark run.

## 2. Findings

| ID | Severity | Finding | Reproduce |
| :--- | :--- | :--- | :--- |
| F1 | High | `eval_holdout.jsonl` is **not isolated** from training: 28/30 prompts and 28/30 code blocks also appear in `train.jsonl` (with different answers). Docs claim "strictly isolated". | `python3 dataset/audit_dataset.py` |
| F2 | High | Training data has only **18 unique prompts** across 138 rows (120 duplicates); the "160-pair pool" is 18 tasks with sampled variations. Overfitting to templates is likely. | `python3 dataset/audit_dataset.py` |
| F3 | High | Base (48.2) and frontier (90.5) scores have **no raw report**; they are hard-coded in `DEMO_DATA` of `evaluation/compare_models.py`, and `--demo` defaults to `True`. | `grep -n composite_cas evaluation/compare_models.py` |
| F4 | Medium | `benchmark_report_final.json` (avg 50.0) is the only base-like report and does not match 48.2. All 30 samples score exactly 50 with identical metrics, i.e. outputs with no code (see F9). It is not the unrefactored input: input code scores 41.3 (AST) / 42.3 (regex). | Inspect `results[*].metrics`. |
| F5 | High | No report recorded which model produced it, so 76.33 cannot be attributed to the GGUF. | Reports had no `meta` block before this change. |
| F6 | Medium | In live mode a failed prompt was dropped silently and the average was computed over successful prompts only. | Fixed: `meta.prompts_failed` now recorded. |
| F7 | Medium | CAS is regex/AST pattern matching (e.g. presence of `interface I...Repository`, `Result.ok`). It does not check compilation or behavior preservation, and training templates contain those patterns. | `evaluation/README.md` §1. |
| F9 | High | **Empty or refusal output scores 50/100** (30 pts for no forbidden imports + 20 pts for no `any`). The reported base (48.2) is below do-nothing, and ECC 76.3 is only +26 over it. | `python3 -m unittest discover -s evaluation/tests -v` (`test_empty_output_scores_fifty_floor`). |
| F10 | Medium | Training has no validation loop and no eval loss; 138 rows x 3 epochs at effective batch 8 is about 52 optimizer steps over 18 unique prompts. `train_lora.py:344` ignores an explicit `--lora-dropout 0.0` (`args.x or recipe.x`). | Read `training/train_lora.py`, `recipes/qwen2.5-coder-1.5b.yaml`. |
| F8 | Low | Frontier baseline is labeled "Gemini 3.8 Flash"; no run against the suite is recorded. | n/a |

## 3. Not verified

- The training code was read, not run; hyperparameters come from the recipe file.
- Whether the served endpoint at the time of the 76.33 run was the shipped GGUF.

## 4. Changes made alongside this audit

| File | Change |
| :--- | :--- |
| `evaluation/eval_benchmark.py` | Adds `meta` block (model name, file SHA-256, endpoint, suite, failed prompts), `--model-name`, `--model-file`, `--save-completions`. Existing report keys unchanged. |
| `evaluation/run_comparison.sh` | Runs the same suite against several endpoints with a health preflight. |
| `dataset/audit_dataset.py` | Repeatable duplicate and leakage audit (`--strict` exits 1 on overlap). |
| `evaluation/eval_benchmark.py` | `meta.degenerate_samples` lists empty/refusal outputs; `spark_day.sh` fails the run if any exist. |
| `evaluation/tests/` | Zero-dependency unit tests (`python3 -m unittest discover -s evaluation/tests`). |
| `evaluation/compare_models.py` | Base and frontier rows relabeled "unmeasured"; "Gemini 3.8 Flash" name removed. |
| README / dataset / report docs | "Strictly isolated" / "zero leakage" wording corrected (en/es). |

## 5. Claim hygiene until Spark results exist

- Present 76.3 as "self-run heuristic score on a 30-case suite, model attribution unrecorded".
- Do not cite 48.2 or 90.5 as measurements.
- Do not describe `eval_holdout.jsonl` as isolated.
- Report CAS together with the do-nothing floor of 50 (F9); a score near 50 means no usable code.
