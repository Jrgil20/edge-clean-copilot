# Spark Day Plan — connect and run

> **Goal:** on the day of the Spark session, the only manual actions are: connect, sync, run one command, copy results back.
> **Background:** [evaluation-audit-2026-11-05.md](./evaluation-audit-2026-11-05.md). Manual fallback: [spark-eval-runbook.md](./spark-eval-runbook.md).
> **Assumptions (from repo docs, unverified on the Spark):** host user `ucab-spark1`, project at `/home/ucab-spark1/proyecto`, `llama.cpp` at `~/llama.cpp`, base model `Qwen/Qwen2.5-Coder-1.5B-Instruct` cached in `~/.cache/huggingface/hub`.

## 1. Night before (laptop)

| # | Action | Done when |
| :-- | :-- | :-- |
| 1 | Push `proyecto/` and the parent repo so the Spark can pull the new scripts. | `git status -sb` shows no `ahead`. |
| 2 | Confirm the base model is still cached on the Spark NVMe (first thing next morning if you cannot check tonight). | Preflight reports `base HF snapshot cached`. |

## 2. Morning (on the Spark)

| # | Command | Expected |
| :-- | :-- | :-- |
| 1 | Connect to the Spark (your usual SSH alias). | Shell on the Spark. |
| 2 | `cd ~/proyecto && git pull --ff-only` | Fast-forward. If `~/proyecto` is not a git checkout, copy `evaluation/`, `dataset/audit_dataset.py` and `docs/` from the laptop with `scp -r`. |
| 3 | `cd evaluation && ./spark_day.sh --preflight-only` | `Preflight OK.` Nothing is started or modified. |
| 4 | `./spark_day.sh` | Builds the base GGUF if missing, serves both models, runs the benchmark, prints `RESULT.md`. |
| 5 | From the laptop: run the `scp -r ...` line printed at the end of step 4. | Folder under `evaluation/reports/spark-<UTC>/`. |

## 3. If preflight fails

The script lists every failure at once and changes nothing.

| Message | Fix |
| :-- | :-- |
| `llama-server not found` | `export LLAMA_SERVER=/path/to/llama-server` |
| `llama.cpp directory not found` | `export LLAMA_CPP_DIR=/path/to/llama.cpp` |
| `base model not cached` | Pre-cache `Qwen/Qwen2.5-Coder-1.5B-Instruct`, or `export BASE_SNAPSHOT=<snapshot dir>`. |
| `AST engine unavailable` | `cd ~/proyecto/cli && pnpm install --frozen-lockfile`. Do not use the regex fallback; it is not comparable with the earlier 76.3. |
| `port 8085/8086 is busy serving ...` | The script will not touch it. Free the port yourself or set `PORT_FT` / `PORT_BASE`. |
| `less than 8 GB free` | Free disk space; conversion creates a ~3 GB intermediate F16 file. |

## 4. After the run

| # | Action | Done when |
| :-- | :-- | :-- |
| 1 | Open `RESULT.md`: all checks ticked? Verdict line read? | Verdict recorded. |
| 2 | Read 5 completions per model in `cas/completions_*.jsonl`. | Outputs are refactored code, not echoed input. |
| 3 | Update claims per [spark-eval-runbook.md §6](./spark-eval-runbook.md). | Docs match the report. |
| 4 | Commit in `proyecto/`, then update the pointer in the parent repo. | Both pushed. |

## 5. What the run produces

| File (under `evaluation/reports/spark-<UTC>/`) | Purpose |
| :-- | :-- |
| `RESULT.md` | Table, automatic checks, verdict. |
| `environment.txt` | Host, GPU, `llama-server` version, git commit, context, ports. |
| `dataset_audit.txt` | Leakage audit (expected `LEAKAGE` until the split is rebuilt). |
| `cas/report_*.json`, `cas/completions_*.jsonl` | Attributed scores and raw outputs. |
| `server_<port>.log` | Server logs for debugging. |

## 6. Guarantees of `spark_day.sh`

- Never opens SSH connections and never touches ports 8080 or 8084.
- Stops only the servers it started; reuses a server on 8085/8086 only if it reports the expected model file.
- Marks the run `INVALID` when any prompt failed, engines differ, models are identical, or the sample count is not 30.
- Tested locally against a fake `llama-server`; it has **not** run on the real Spark.
