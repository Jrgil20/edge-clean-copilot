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

## 2. Findings

| ID | Severity | Finding | Reproduce |
| :--- | :--- | :--- | :--- |
| F1 | High | `eval_holdout.jsonl` is **not isolated** from training: 28/30 prompts and 28/30 code blocks also appear in `train.jsonl` (with different answers). Docs claim "strictly isolated". | `python3 dataset/audit_dataset.py` |
| F2 | High | Training data has only **18 unique prompts** across 138 rows (120 duplicates); the "160-pair pool" is 18 tasks with sampled variations. Overfitting to templates is likely. | `python3 dataset/audit_dataset.py` |
| F3 | High | Base (48.2) and frontier (90.5) scores have **no raw report**; they are hard-coded in `DEMO_DATA` of `evaluation/compare_models.py`, and `--demo` defaults to `True`. | `grep -n composite_cas evaluation/compare_models.py` |
| F4 | Medium | `benchmark_report_final.json` (avg 50.0) is the only base-like report and does not match 48.2. Its first samples all score 50, which suggests unrefactored input may have been scored (unconfirmed). | Inspect `results[*].total_score`. |
| F5 | High | No report recorded which model produced it, so 76.33 cannot be attributed to the GGUF. | Reports had no `meta` block before this change. |
| F6 | Medium | In live mode a failed prompt was dropped silently and the average was computed over successful prompts only. | Fixed: `meta.prompts_failed` now recorded. |
| F7 | Medium | CAS is regex/AST pattern matching (e.g. presence of `interface I...Repository`, `Result.ok`). It does not check compilation or behavior preservation, and training templates contain those patterns. | `evaluation/README.md` §1. |
| F8 | Low | Frontier baseline is labeled "Gemini 3.8 Flash"; no run against the suite is recorded. | n/a |

## 3. Not verified

- That the sub-scores in `DEMO_DATA["ecc"]` match the per-category values inside the raw 76.33 report.
- The training code path (`training/train_lora.py`) and hyperparameters.
- Whether the served endpoint at the time of the 76.33 run was the shipped GGUF.

## 4. Changes made alongside this audit

| File | Change |
| :--- | :--- |
| `evaluation/eval_benchmark.py` | Adds `meta` block (model name, file SHA-256, endpoint, suite, failed prompts), `--model-name`, `--model-file`, `--save-completions`. Existing report keys unchanged. |
| `evaluation/run_comparison.sh` | Runs the same suite against several endpoints with a health preflight. |
| `dataset/audit_dataset.py` | Repeatable duplicate and leakage audit (`--strict` exits 1 on overlap). |

## 5. Claim hygiene until Spark results exist

- Present 76.3 as "self-run heuristic score on a 30-case suite, model attribution unrecorded".
- Do not cite 48.2 or 90.5 as measurements.
- Do not describe `eval_holdout.jsonl` as isolated.
