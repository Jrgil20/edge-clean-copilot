# Spark Evaluation Runbook

> **Goal:** replace hard-coded and unattributed benchmark numbers with reproducible, model-attributed reports.
> **Prerequisite reading:** [evaluation-audit-2026-11-05.md](./evaluation-audit-2026-11-05.md).
> **Constraints:** ports `8080` and `8084` belong to other lab services; use `8085` (ECC) and `8086` (base). Do not stop processes you did not start.

## 1. Preflight

```bash
# On the Spark: confirm the ports are free or already ours
ss -ltnp | grep -E ':(8080|8084|8085|8086)\b'

# Locally (laptop): sanity checks before the burst
python3 proyecto/status.py
python3 proyecto/dataset/audit_dataset.py   # expected today: LEAKAGE (known, F1/F2)
```

## 2. Serve both models with the same quantization

The comparison is only fair if base and fine-tune share the same quant (Q4_K_M) and the same server flags.

```bash
# Fine-tune (already in the repo)
llama-server -m proyecto/training/output/gguf/clean-copilot-1.5b-q4_k_m.gguf \
  --port 8085 -c 4096

# Base: Qwen2.5-Coder-1.5B-Instruct at Q4_K_M.
# Option A: download a ready GGUF (verify the repo exists first).
# Option B: convert with the project script (check ./convert_to_gguf.sh --help for flags).
llama-server -m /path/to/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf \
  --port 8086 -c 4096
```

Record in the notes: `llama-server` build/commit, context size, GPU or CPU, quantization.

## 3. Run the comparison

```bash
cd proyecto/evaluation
./run_comparison.sh \
  --model "ecc-ft=http://127.0.0.1:8085/v1/chat/completions=../training/output/gguf/clean-copilot-1.5b-q4_k_m.gguf" \
  --model "qwen-base=http://127.0.0.1:8086/v1/chat/completions=/path/to/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
```

Output goes to `evaluation/reports/<UTC timestamp>/`:

| File | Content |
| :--- | :--- |
| `report_<name>.json` | Scores plus `meta` (model, SHA-256, endpoint, suite, failed prompts). |
| `completions_<name>.jsonl` | Raw model outputs for manual inspection. |
| `suite.jsonl`, `suite.sha256` | Exact suite used. |

## 4. Acceptance checks

| Check | Pass condition |
| :--- | :--- |
| No dropped prompts | `meta.prompts_failed` is `[]` for every model. |
| Same suite | Both reports show the same `cases_file`; `suite.sha256` stored. |
| Attribution | `meta.model_sha256` present and different between base and fine-tune. |
| Real outputs | Read at least 5 completions per model; confirm they are refactored code, not echoed input. |
| Sanity of score | If base and fine-tune differ by under ~5 points, do not claim improvement. |

## 5. Optional follow-ups (if time allows)

1. Run the suite twice per model to see run-to-run variance (temperature is 0.1, not 0).
2. Type-check completions with `tsc --noEmit` to complement the pattern-based CAS.
3. Run the frontier baseline through the same script if an endpoint is available; otherwise drop its row.

## 6. After the run: update claims

| Action | File |
| :--- | :--- |
| Replace `DEMO_DATA` base/ecc/cloud values with report-derived numbers, or label them "unmeasured". | `evaluation/compare_models.py` |
| Update scores in the model card, README badges, and final report. | `MODEL_CARD.md`, `README.md`, `docs/final-report-and-presentation.md` |
| Correct "strictly isolated" wording for the holdout split. | `docs/final-report-and-presentation.md`, `docs/progress-and-milestones.md` |
| Mirror all of the above in Spanish. | `es/` |
| Commit inside `proyecto/`, then update the pointer in the parent repo. | git |

## 7. Deferred (needs retraining, not for the first Spark session)

- Rebuild the split so holdout code never appears in training (F1) and increase prompt diversity beyond 18 tasks (F2). Re-run `dataset/audit_dataset.py --strict` until it passes, then retrain and re-evaluate.
