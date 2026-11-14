# Reportes del benchmark

Corridas del benchmark que están en el repositorio. En la documentación, citar solo cifras de corridas atribuidas (reportes con bloque `meta`).

| Carpeta | Fecha | Estado | Contenido |
|---------|-------|--------|-----------|
| [`spark-20261105T143540Z/`](../../../evaluation/reports/spark-20261105T143540Z/RESULT.md) | 2026-11-05 | **Canónica** | Fine-tune frente a base en el DGX Spark, misma suite, Q4_K_M, motor AST: CAS 74.83 frente a 58.0 (n=30 cada uno, 0 fallos) |
| [`laptop-ft-20261105T051232Z/`](../../../evaluation/reports/laptop-ft-20261105T051232Z/) | 2026-11-05 | De apoyo | Repetición del fine-tune en la CPU del portátil |
| [`legacy-2026-10-29/`](../../../evaluation/reports/legacy-2026-10-29/README.md) | 2026-10-29 | Superada | Reportes sin atribución anteriores a la auditoría (sin bloque `meta`); se conservan solo como evidencia y no deben citarse |
| `local/` | — | Ignorada por git | Salida por defecto de `eval_benchmark.py` para corridas puntuales |
