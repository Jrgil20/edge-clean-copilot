# Benchmark reports

Committed benchmark runs. Quote numbers in docs only from attributed runs (reports with a `meta` block).

| Folder | Date | Status | Content |
|--------|------|--------|---------|
| [`spark-20261105T143540Z/`](spark-20261105T143540Z/RESULT.md) | 2026-11-05 | **Canonical** | Fine-tune vs base on the DGX Spark, same suite, Q4_K_M, AST engine: CAS 74.83 vs 58.0 (n=30 each, 0 failed) |
| [`laptop-ft-20261105T051232Z/`](laptop-ft-20261105T051232Z/) | 2026-11-05 | Supporting | Same fine-tune GGUF (SHA-256 `d2deae6542d1`…) on the laptop CPU: CAS 72.5 (n=30, 0 failed); shows run-to-run noise vs 74.83 |
| [`legacy-2026-10-29/`](legacy-2026-10-29/README.md) | 2026-10-29 | Superseded | Unattributed reports from before the audit; kept as evidence only |
| `local/` | — | Gitignored | Default output of `eval_benchmark.py` for ad-hoc runs |
