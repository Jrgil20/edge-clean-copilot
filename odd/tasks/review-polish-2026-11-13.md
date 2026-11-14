# Review polish 2026-11-13

Objective: fix the defects found in the full project review (CLI unusable against the real CPU model) and bring docs in line with measured numbers.
Branch: `feat/review-polish-2026-11-13` (in `proyecto/`). Delivery: ask-on-risk, work-unit commits, push left to the user. Runners: `cd cli && pnpm test`; Python `python3 -m unittest`.

## Specs

User request (verbatim, L1): "primero quiero una revision completa aca tienes acceso hasta al modelo local que hicimos asi uqe termian de afinar y documentar". The specs below are derived from review findings (assumption: "afinar" = polish, not retraining).

- S1 — CLI inference timeout is configurable (`--timeout <ms>`, env `CLEAN_COPILOT_TIMEOUT_MS`) with a default that fits measured CPU speed. Evidence: a real run timed out at the fixed 60000 ms; the direct call took 86.4 s for 1091 tokens (12.6 tok/s, i5-10310U), so default `--max-tokens 2048` needs ~165 s.
- S2 — The refactored code returned by the use case is the first fenced code block of the model reply (fallback: full reply when no fence). `-o` and `--diff` use the extracted code. Evidence: the model reply starts with "Here's the refactored code following Clean Architecture principles:" and ends with a prose summary.
- S3 — stdout carries only the result (code or diff); banner and status lines go to stderr, so `clean-copilot refactor f.ts > out.ts` yields code. Action errors exit non-zero (`parseAsync`).
- S4 — CLI docs (`cli/README.md`, `README.md` CLI section) list every implemented flag and env var.
- S5 — Current docs carry no unmeasured metrics: frontier 90.5, unmeasured tok/s, TTFT, "Eradicates 100%" without scope. History docs get the existing "Superseded figures" banner instead of rewrites.
- S6 — `dataset/README.md` English text matches the Spanish one about the current prompt-disjoint split and states that `eval_holdout.jsonl` overlaps `published_model_train.jsonl` (11/30), so it cannot evaluate the published model.
- S7 — `es/` mirrors the English changes of this feature.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1 | inline | pending | |
| T2 | S2 | inline | pending | |
| T3 | S3 | inline | pending | |
| T4 | S4, S7 | inline | pending | |
| T5 | S5, S6, S7 | inline | pending | |

Route evidence: no Writer trigger (units are small and sequential); review mapping was delegated to 3 read-only explorers.

## Log

- L1 (2026-11-13) user: "primero quiero una revision completa aca tienes acceso hasta al modelo local que hicimos asi uqe termian de afinar y documentar"
- L2 baseline: 44/44 vitest, tsc build OK, Python unittest 9+12+4+1(skipped) OK. Real model smoke test: CLI failed with `llama-server ... did not respond within 60000ms`.
- L3 out of scope pending user decision: `bin/copilot-local` qwen target on Spark port 8080, hardcoded `192.168.6.35` default, moving stale `evaluation/benchmark_report*.json`, `train_lora.py` masking/Gemma-2 system role, renaming `-n`, file renames, HF card (`training/output/gguf/README.md` is untracked).
