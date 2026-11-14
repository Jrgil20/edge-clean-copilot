# Auditoría de Evaluación — 2026-11-05

> **Estado:** hallazgos de una auditoría de solo lectura; la remediación está planificada en [spark-eval-runbook.md](./spark-eval-runbook.md).
> **Alcance:** tests del CLI, reportes de benchmark, split del dataset, herramientas de comparación.
> **Método:** comandos ejecutados localmente; la DGX Spark estaba apagada, no se consultó ningún modelo.

## 1. Verificado

| Afirmación | Evidencia |
| :--- | :--- |
| Pasan los 41 tests del CLI | `cd cli && pnpm test` → 8 archivos, 41 aprobados. |
| El puntaje 76.3 de ECC tiene reporte crudo | `evaluation/reports/legacy-2026-10-29/benchmark_report_edge_copilot.json`: `total_samples=30`, `average_score=76.33`. |
| La suite legacy no se solapa con el entrenamiento | 0/30 prompts y 0/30 bloques de código de la suite aparecen en `dataset/train.jsonl`. |
| Los subpuntajes suman el compuesto | p. ej. ECC 30.0 + 11.7 + 16.0 + 18.7 = 76.4 (redondeo). |
| Los subpuntajes de `DEMO_DATA["ecc"]` coinciden con el reporte crudo | Recalculados desde `benchmark_report_edge_copilot.json`: 30.0 / 11.67 / 16.0 / 18.67. |
| El entrenamiento usa enmascarado de loss solo en la respuesta | El collator de `training/train_lora.py` enmascara todo lo anterior a la respuesta del asistente. |

## 1b. Re-medición en la laptop (primera corrida atribuida)

| Elemento | Valor |
| :--- | :--- |
| Modelo | `clean-copilot-1.5b-q4_k_m.gguf`, SHA-256 `d2deae65...` (CPU, `llama-server -ngl 0 -c 4096`) |
| Suite / motor | `legacy_benchmark_suite.jsonl`, motor AST, temperatura 0.1 |
| Resultado | **CAS 72.5** (n=30, 0 prompts fallidos, 0 salidas vacías); notas A:3, B:23, C:4 |
| Corrida anterior sin atribución | 76.33 (el informe final cita una reproducción de 73.8) |
| Coincidencia caso a caso con la corrida de 76.33 | 4/30 idénticos, diferencia absoluta media 17.8 puntos |
| Evidencia | `evaluation/reports/laptop-ft-20261105T051232Z/` |

Lectura: el fine-tune produce código real y puntúa entre 72 y 76, pero la variación por caso entre corridas es grande, así que diferencias menores a ~5 puntos son ruido. La comparación contra el modelo base sigue requiriendo la corrida en la Spark.

## 1c. Comparación medida en DGX Spark (corrida head-to-head reproducible)

| Elemento | Fine-tune (`ecc-ft`) | Base (`qwen-base`) | Delta |
| :--- | :--- | :--- | :--- |
| Modelo | `clean-copilot-1.5b-q4_k_m.gguf` (`d2deae6542d1...`) | `qwen2.5-coder-1.5b-base-q4_k_m.gguf` (`27ca8fbeb81c...`) | - |
| Hardware / Runtime | NVIDIA GB10 Grace Blackwell, `llama-server` (ctx 4096, ngl 99) | NVIDIA GB10 Grace Blackwell, `llama-server` (ctx 4096, ngl 99) | Mismo |
| Suite / Motor | `legacy_benchmark_suite.jsonl`, motor AST (`ts.createSourceFile`) | `legacy_benchmark_suite.jsonl`, motor AST (`ts.createSourceFile`) | Mismo |
| Prompts evaluados | 30/30 (0 fallidos, 0 degenerados) | 30/30 (0 fallidos, 0 degenerados) | - |
| Aislamiento de Dominio | 30.0 / 30.0 (100.0%) | 24.0 / 30.0 (80.0%) | +6.0 |
| Seguridad e Invariantes | 2.7 / 25.0 (10.7%) | 0.3 / 25.0 (1.3%) | +2.4 |
| Puertos y Adaptadores | 22.5 / 25.0 (90.0%) | 15.8 / 25.0 (63.3%) | +6.7 |
| Tipado TypeScript | 19.7 / 20.0 (98.3%) | 17.8 / 20.0 (89.2%) | +1.9 |
| **CAS Compuesto** | **74.83 / 100.0** | **58.00 / 100.0** | **+16.83** |
| Evidencia | `evaluation/reports/spark-20261105T143540Z/` | `evaluation/reports/spark-20261105T143540Z/` | `RESULT.md` |

Lectura: con cuantización idéntica (Q4_K_M) y misma configuración de servidor en la DGX Spark, el fine-tune especializado logra una mejora de +16.83 puntos CAS sobre el modelo base sin prompts caídos ni salidas degeneradas.

## 2. Hallazgos

| ID | Severidad | Hallazgo | Reproducir |
| :--- | :--- | :--- | :--- |
| F1 | Alta | `eval_holdout.jsonl` **no está aislado**: 28/30 prompts y 28/30 bloques de código también están en `train.jsonl` (con respuestas distintas). Los docs dicen "estrictamente aislado". | `python3 dataset/audit_dataset.py` |
| F2 | Alta | El entrenamiento tiene solo **18 prompts únicos** en 138 filas (120 duplicadas); el "pool de 160 pares" son 18 tareas con variaciones. Es probable el sobreajuste a plantillas. | `python3 dataset/audit_dataset.py` |
| F3 | Alta | Los puntajes de base (48.2) y frontier (90.5) **no tienen reporte crudo**: están escritos a mano en `DEMO_DATA` de `evaluation/compare_models.py`, y `--demo` es `True` por defecto. | `grep -n composite_cas evaluation/compare_models.py` |
| F4 | Media | `benchmark_report_final.json` (prom. 50.0) es el único reporte tipo base y no coincide con 48.2. Sus 30 muestras puntúan exactamente 50 con métricas idénticas, lo que son salidas sin código (ver F9). No es la entrada sin refactorizar: el código de entrada puntúa 41.3 (AST) / 42.3 (regex). | Inspeccionar `results[*].metrics`. |
| F5 | Alta | Ningún reporte registraba qué modelo lo generó, así que 76.33 no se puede atribuir al GGUF. | Los reportes no tenían bloque `meta` antes de este cambio. |
| F6 | Media | En modo live un prompt fallido se descartaba en silencio y el promedio se calculaba solo sobre los exitosos. | Corregido: ahora se registra `meta.prompts_failed`. |
| F7 | Media | CAS es coincidencia de patrones regex/AST (p. ej. presencia de `interface I...Repository`, `Result.ok`). No verifica compilación ni preservación de comportamiento, y las plantillas de entrenamiento contienen esos patrones. | `evaluation/README.md` §1. |
| F9 | Alta | **Una salida vacía o una negativa puntúa 50/100** (30 pts por no tener imports prohibidos + 20 pts por no usar `any`). El base reportado (48.2) está por debajo de no hacer nada, y ECC 76.3 supera ese piso solo por +26. | `python3 -m unittest discover -s evaluation/tests -v` (`test_empty_output_scores_fifty_floor`). |
| F10 | Media | El entrenamiento no tiene bucle de validación ni loss de eval; 138 filas x 3 épocas con batch efectivo 8 son unos 52 pasos de optimizador sobre 18 prompts únicos. `train_lora.py:344` ignora un `--lora-dropout 0.0` explícito (`args.x or recipe.x`). | Leer `training/train_lora.py`, `recipes/qwen2.5-coder-1.5b.yaml`. |
| F8 | Baja | El baseline frontier figura como "Gemini 3.8 Flash"; no hay ejecución registrada contra la suite. | n/a |

## 3. No verificado

- El código de entrenamiento se leyó, no se ejecutó; los hiperparámetros salen del archivo de receta.
- Si el endpoint servido durante la corrida de 76.33 era el GGUF publicado.

## 4. Cambios realizados junto con esta auditoría

| Archivo | Cambio |
| :--- | :--- |
| `evaluation/eval_benchmark.py` | Agrega bloque `meta` (modelo, SHA-256 del archivo, endpoint, suite, prompts fallidos), `--model-name`, `--model-file`, `--save-completions`. Las claves existentes del reporte no cambian. |
| `evaluation/run_comparison.sh` | Ejecuta la misma suite contra varios endpoints con chequeo de salud previo. |
| `dataset/audit_dataset.py` | Auditoría repetible de duplicados y fuga (`--strict` sale con código 1 si hay solape). |
| `evaluation/eval_benchmark.py` | `meta.degenerate_samples` lista salidas vacías/negativas; `spark_day.sh` invalida la corrida si existen. |
| `evaluation/tests/` | Tests unitarios sin dependencias (`python3 -m unittest discover -s evaluation/tests`). |
| `evaluation/compare_models.py` | Filas base y frontier renombradas "no medido"; se eliminó el nombre "Gemini 3.8 Flash". |
| README / dataset / docs del informe | Corregida la redacción "estrictamente aislado" / "cero fuga" (en/es). |

## 5. Higiene de afirmaciones hasta tener resultados de la Spark

- Presentar 76.3 como "puntaje heurístico propio sobre una suite de 30 casos, modelo sin atribución registrada".
- No citar 48.2 ni 90.5 como mediciones.
- No describir `eval_holdout.jsonl` como aislado.
- Reportar CAS junto con el piso de 50 de "no hacer nada" (F9); un puntaje cercano a 50 significa que no hay código utilizable.
