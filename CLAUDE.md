# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Edge Clean Copilot (ECC): a LoRA fine-tune of `Qwen2.5-Coder-1.5B-Instruct` that refactors TypeScript toward Clean Architecture / DDD, quantized to GGUF and served offline via `llama.cpp`. It is a pipeline of four loosely coupled subsystems that communicate through files, not imports:

```
dataset/ (ChatML JSONL)  →  training/ (LoRA → merged FP16 → GGUF)  →  llama-server  →  cli/ and evaluation/
```

`docs/` is grouped into `project/` (proposal, ideas, `project-analysis.md`: the current assessment and errata), `usage/`, `evaluation/`, `architecture/` and `history/` (dated logs, figures may be superseded), with `next-steps.md` and the index `README.md` at the top; `es/` is a full Spanish mirror of the READMEs and `docs/`. When you change an English doc, update its `es/` counterpart too. `status.py` prints a zero-dependency project health dashboard.

## Commands

### CLI (TypeScript, `cli/`) — pnpm only
```bash
cd cli && pnpm install
pnpm test                                    # vitest run (tests/**/*.test.ts)
pnpm exec vitest run tests/domain/entities/SourceFile.test.ts   # single file
pnpm exec vitest run -t "extracts code blocks"                  # single test by name
pnpm run build                               # tsc → dist/
pnpm run dev refactor <file> --mock          # run without a model server
pnpm run dev refactor <file> --url http://127.0.0.1:8080 --diff
```
`bin/clean-copilot` runs `cli/dist` if built, otherwise falls back to `tsx` on the source. Server URL/model also come from `CLEAN_COPILOT_URL` / `LLAMA_SERVER_URL` / `CLEAN_COPILOT_MODEL`.

### Python tests — stdlib `unittest` (pytest is not installed)
```bash
python3 -m unittest discover -s evaluation/tests -v
python3 -m unittest dataset/test_split_dataset.py -v
python3 -m unittest dataset/test_audit_dataset.py -v   # typecheck tests skip without cli/node_modules
python3 -m unittest training/test_train_loop.py -v      # skipped if torch is missing
python3 -m unittest training/test_data_prep.py -v       # system-prompt folding + completion labels (no torch)
python3 -m unittest test_status.py -v                   # status.py reports only what it checks
```

### Dataset
```bash
python3 dataset/validate_dataset.py dataset/train.jsonl
python3 dataset/split_dataset.py        # deterministic (seed=42) train/holdout split
python3 dataset/audit_dataset.py        # prompt-overlap audit + truncated answers / explicit any
python3 dataset/audit_dataset.py --typecheck --list-failures   # also tsc-check answers (needs pnpm install in cli/)
```

### Training (GPU / DGX Spark; `--dry-run` works on CPU)
```bash
cd training && pip install -r requirements.txt
python3 train_lora.py --recipe recipes/qwen2.5-coder-1.5b.yaml --dry-run
python3 train_lora.py --recipe recipes/qwen2.5-coder-1.5b.yaml --max-time-minutes 15.0 --merge
./convert_to_gguf.sh [--all --clean-f16]
```

### Evaluation (CAS benchmark)
```bash
cd evaluation
python3 eval_benchmark.py --cases legacy_benchmark_suite.jsonl          # offline, AST engine
python3 eval_benchmark.py --cases legacy_benchmark_suite.jsonl --no-ast # regex fallback
python3 eval_benchmark.py --url http://HOST:8085/v1/chat/completions --prompts legacy_benchmark_suite.jsonl --output live_report.json
./run_comparison.sh --model "name=URL[=MODEL_FILE]" ...                  # multi-model, attributed reports
```

## Architecture notes that span files

- **CLI is itself hexagonal** and must stay that way: `domain/` and `application/` never import from `infrastructure/` or third-party packages. All I/O goes through ports (`application/ports/IInferenceEngine.ts`); adapters live in `infrastructure/` (`LlamaServerAdapter` over HTTP, `MockInferenceAdapter` for offline tests, `fs/` readers/writers). `infrastructure/cli/index.ts` is the composition root (excluded from coverage).
- **Errors are values**: functions return `Result<T, E>` from `shared/types/Result.ts` (`Result.ok` / `Result.fail`, check `.success`) with typed errors from `shared/errors/DomainError.ts`; don't throw across layers. `tsconfig` is fully strict with `noUnusedLocals/Parameters`; no `any`. ESM with `NodeNext`, so relative imports need the `.js` suffix.
- **Evaluation spans Python and TypeScript**: `eval_benchmark.py` shells out to `pnpm exec tsx evaluation/ast_analyzer.ts` with `cwd=cli/` and `NODE_PATH=cli/node_modules`, so the AST engine needs `pnpm install` in `cli/` first; otherwise it falls back to regex scoring. `ast_analyzer.ts` is unit-tested from `cli/tests/evaluation/`. Scoring rules (CAS 0–100: boundary 30, invariants 25, ports 25, typing 20) are documented in `evaluation/README.md` — keep the Python fallback and the AST analyzer in agreement when changing them.
- **Training is recipe-driven**: `training/recipes/*.yaml` (schema in `recipes/schema.py`) declare model ID, LoRA targets, dtype, response template and hyperparameters; CLI flags on `train_lora.py` override them.
- **Dataset format** is ChatML JSONL (`{"messages":[system,user,assistant]}`). `split_dataset.py` merges seed + generated + authored examples, splits by normalized user prompt (no prompt may appear in both partitions) and drops answers with unbalanced code fences, explicit `any` or a failing isolated `tsc` type-check (via `audit_dataset.typecheck` → `typecheck_answers.mjs`, which needs `pnpm install` in `cli/`; `--no-verify` skips the last two). The committed `train.jsonl`/`eval_holdout.jsonl` are this newer prompt-disjoint split and have **not** been trained on; the published model was trained on the older split at commit `64f3c6c` (138 rows, 18 distinct prompts, holdout overlapping train), kept as `dataset/published_model_{train,holdout}.jsonl`. `evaluation/legacy_benchmark_suite.jsonl` is the disjoint eval set. Known problems and priorities (dataset first) are in `docs/next-steps.md`; the README frames the project as a proof of concept, so keep claims in line with measured reports.
- **Reports are attributed**: benchmark reports carry a `meta` block (model name, GGUF SHA-256, endpoint, suite hash). Committed runs live in `evaluation/reports/<run>/`. When quoting benchmark numbers in docs, use measured report values (README states 74.8 fine-tune vs 58.0 base on Spark).

## Constraints

- Shared Spark cluster: `spark_day.sh` / `run_comparison.sh` never open SSH and never touch ports 8080/8084 (other tenants). Fine-tune serves on 8085, base on 8086. Preserve these guarantees when editing those scripts.
- Model weights (`*.gguf`, `*.safetensors`, `output/`) are gitignored. Don't commit them.
- Commit messages use Conventional Commits with scopes matching subsystems, e.g. `fix(dataset): …`, `test(training): …`, `docs(evaluation): …`.
