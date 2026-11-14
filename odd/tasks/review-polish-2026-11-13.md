# Review polish 2026-11-13

Objective: fix the defects found in the full project review (CLI unusable against the real CPU model) and bring docs in line with measured numbers.
Branch: `feat/review-polish-2026-11-13` (in `proyecto/`). Delivery: ask-on-risk, work-unit commits, push left to the user. Runners: `cd cli && pnpm test`; Python `python3 -m unittest`.

## Specs

User request (verbatim, L1): "primero quiero una revision completa aca tienes acceso hasta al modelo local que hicimos asi uqe termian de afinar y documentar". The specs below are derived from review findings (assumption: "afinar" = polish, not retraining).

- S1 — CLI inference timeout is configurable (`--timeout <ms>`, env `CLEAN_COPILOT_TIMEOUT_MS`) with a default that fits measured CPU speed. Evidence: a real run timed out at the fixed 60000 ms; the direct call took 86.4 s for 1091 tokens (12.6 tok/s, i5-10310U), so default `--max-tokens 2048` needs ~165 s.
- S2 — The refactored code returned by the use case is the code of the fenced blocks of the model reply, joined by a blank line, as the evaluator's `extractCodeBlock` does (fallback: trimmed reply when no fence). `-o` and `--diff` use the extracted code. Evidence: the model reply starts with "Here's the refactored code following Clean Architecture principles:" and ends with a prose summary.
- S3 — stdout carries only the result (code or diff); banner and status lines go to stderr, so `clean-copilot refactor f.ts > out.ts` yields code. Action errors exit non-zero (`parseAsync`).
- S4 — CLI docs (`cli/README.md`, `README.md` CLI section) list every implemented flag and env var.
- S5 — Current docs carry no unmeasured metrics: frontier 90.5, unmeasured tok/s, TTFT, "Eradicates 100%" without scope. History docs get the existing "Superseded figures" banner instead of rewrites.
- S6 — `dataset/README.md` English text matches the Spanish one about the current prompt-disjoint split and states that `eval_holdout.jsonl` overlaps `published_model_train.jsonl` (11/30), so it cannot evaluate the published model.
- S7 — `es/` mirrors the English changes of this feature.
- S8 (item 5) — The three unattributed 2026-10-29 reports (`evaluation/benchmark_report.json`, `_final`, `_edge_copilot`) move to `evaluation/reports/legacy-2026-10-29/` with a README saying they are superseded; `eval_benchmark.py` no longer defaults `--output` to a tracked file (default goes to a gitignored `evaluation/reports/local/`).
- S9 (item 6) — The Hugging Face card matches `MODEL_CARD.md`. Evidence: live card = previous MODEL_CARD (frontier 90.5, "Eradicates 100%"). No HF token on this laptop, so the upload is prepared and the final command handed to the user.
- S10 (item 7) — `status.py` prints only what it checks: no hardcoded Spark state, GGUF path checked on disk, CAS read from the Spark report JSON, both dataset splits listed with which one the published model was trained on.
- S11 (item 8) — Spanish mirrors exist for `cli/README.md` and `MODEL_CARD.md`.
- S12 (item 9) — Both findings verified: the Gemma-2 chat template raises "System role not supported" (fetched from the public `unsloth/gemma-2-2b-it` tokenizer_config), and `collate_fn` keeps the whole sequence as labels when the response template is not found. Fix: recipe flag to fold the system prompt into the first user turn (on for Gemma-2); rows without an assistant span after truncation are dropped with a warning instead of training on the prompt.

## Tasks

| ID | Specs | Route | Status | Commit |
|----|-------|-------|--------|--------|
| T1 | S1 | inline | done (RED→GREEN) | f692230 |
| T2 | S2 | inline | done (RED→GREEN) | f692230 |
| T3 | S3 | inline | done (RED→GREEN, e2e on mock) | f692230 |
| T4 | S4, S7 | inline | done | 5db9ee3 |
| T5 | S5, S6, S7 | inline | done | 70c2f2c |
| T6 | S8 | inline | done (RED→GREEN) | 1c4d3d7 |
| T7 | S9 | inline (upload by user) | prepared; upload pending user auth | c0608ad, ef4a9b5 |
| T8 | S10 | inline | done (RED→GREEN) | 0474733 |
| T9 | S11 | inline | done | bc0b61c |
| T10 | S12 | inline | done (RED→GREEN) | 2586aa1, 522a9e2 |

Route evidence: no Writer trigger (units are small and sequential); review mapping was delegated to 3 read-only explorers.

## Log

- L1 (2026-11-13) user: "primero quiero una revision completa aca tienes acceso hasta al modelo local que hicimos asi uqe termian de afinar y documentar"
- L2 baseline: 44/44 vitest, tsc build OK, Python unittest 9+12+4+1(skipped) OK. Real model smoke test: CLI failed with `llama-server ... did not respond within 60000ms`.
- L3 out of scope pending user decision: `bin/copilot-local` qwen target on Spark port 8080, hardcoded `192.168.6.35` default, moving stale `evaluation/benchmark_report*.json`, `train_lora.py` masking/Gemma-2 system role, renaming `-n`, file renames, HF card (`training/output/gguf/README.md` is untracked).
- L4 tests: 60/60 vitest (16 new incl. 8 e2e on the mock engine), tsc build OK. Real model after the fix: request ran 208 s with no timeout (S1 proven), then failed with `finish_reason=length` at 2048 tokens (the earlier direct call stopped at 1091). Second CLI run at the default temperature 0.1 also hit `finish_reason=length` (224 s). The CLI request body was captured with a local spy server and is byte-identical (model, temperature 0.1, max_tokens 2048, system and user messages) to the direct-API probe, whose 0.1 runs stopped at 1091 and 1287 tokens and whose temperature-0 run stopped at 1192. So at 0.1 the stop is sampling luck: CLI 0/2, API 2/2 (n too small to rate). CLI at `-t 0`: exit 0 in 120 s, `out.ts` 192 lines, no prose or fences, identical to stdout (first verified real end-to-end run). Extraction on 3 API replies: 2 parse cleanly; 1 has model-written placeholders (`= /* implementation */;`).
- L5 found during T5: `docs/index.html` (en/es) chart/table/slides used demo data (76.3/48.2/90.5); regenerated from the Spark report and checked with a headless-Chrome render. Holdout overlap verified with `audit_dataset.user_prompt`: 11/30 rows in published_model_train, 0 prompts shared with current train.
- L6 not done: es mirror for `cli/README.md` (no `es/cli/` exists), `MODEL_CARD.md`, matrix.
- L7 advisor follow-ups: `evaluation/benchmark_comparison_chart.svg` still drew the unmeasured "Gemini 3.8 Flash" series; replaced with the measured two-series chart (render identical to the validated index.html chart). `compare_models.py` still hardcodes three series and would redraw it on re-run (pending). `training/README.md` (en/es) unmeasured Q5/Q8/F16 speeds and quality-retention figures set to "not measured"; dataset README "183 samples" note marked superseded (en/es). CLI claims corrected to measured values (86–130 s typical, 208 s for a full 2048-token reply; "code only", not "a source file"). Added `--diff` e2e test: 61/61.

- L8 (2026-11-13) user: "puedes resolver de la 5 en adelante de hecho" (items 5–9 of the pending-decision list). Pushed earlier on request: branch + parent pointer c0c017f.
- L9 T6–T10: Gemma-2 finding verified from the template text (`raise_exception('System role not supported')`); rendering the downloaded template locally was blocked by the permission classifier, so the fold is proven with a stand-in tokenizer in `test_data_prep.py`. Loss-mask finding verified in code (`found_idx == -1` kept full labels). MODEL_CARD reading for the es mirror surfaced more unmeasured content (operational table 52/85 tok/s, "A100", "completely eliminates any", batch 2×4) — fixed in c0608ad from audit T1/T3 and the Spark report (28/30 outputs without an any penalty). HF upload needs the user's token (none on this laptop): `training/upload_to_hf.sh --card-only <repo>`. All suites: 61/61 vitest; Python evaluation, dataset, training (data_prep 12 OK, train_loop skipped without torch), test_status OK.
