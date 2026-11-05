# Spark run result

| Model | Avg CAS | n | failed | sha256 |
| :-- | --: | --: | --: | :-- |
| ecc-ft | 74.83 | 30 | 0 | d2deae6542d1 |
| qwen-base | 58.0 | 30 | 0 | 27ca8fbeb81c |

## Checks

- [x] No dropped prompts
- [x] Same suite
- [x] AST engine for both
- [x] Models differ (SHA-256)
- [x] No empty/refusal outputs (each scores 50 for free)
- [x] Full sample count

**Verdict:** Fine-tune is +16.83 CAS points over base on this heuristic suite (30 cases, self-run).

Manual step still required: read 5 completions per model in `cas/completions_*.jsonl`.
