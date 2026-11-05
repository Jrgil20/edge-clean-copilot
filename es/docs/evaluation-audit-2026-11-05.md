# Auditoría de Evaluación — 2026-11-05

> **Estado:** hallazgos de una auditoría de solo lectura; la remediación está planificada en [spark-eval-runbook.md](./spark-eval-runbook.md).
> **Alcance:** tests del CLI, reportes de benchmark, split del dataset, herramientas de comparación.
> **Método:** comandos ejecutados localmente; la DGX Spark estaba apagada, no se consultó ningún modelo.

## 1. Verificado

| Afirmación | Evidencia |
| :--- | :--- |
| Pasan los 41 tests del CLI | `cd cli && pnpm test` → 8 archivos, 41 aprobados. |
| El puntaje 76.3 de ECC tiene reporte crudo | `evaluation/benchmark_report_edge_copilot.json`: `total_samples=30`, `average_score=76.33`. |
| La suite legacy no se solapa con el entrenamiento | 0/30 prompts y 0/30 bloques de código de la suite aparecen en `dataset/train.jsonl`. |
| Los subpuntajes suman el compuesto | p. ej. ECC 30.0 + 11.7 + 16.0 + 18.7 = 76.4 (redondeo). |

## 2. Hallazgos

| ID | Severidad | Hallazgo | Reproducir |
| :--- | :--- | :--- | :--- |
| F1 | Alta | `eval_holdout.jsonl` **no está aislado**: 28/30 prompts y 28/30 bloques de código también están en `train.jsonl` (con respuestas distintas). Los docs dicen "estrictamente aislado". | `python3 dataset/audit_dataset.py` |
| F2 | Alta | El entrenamiento tiene solo **18 prompts únicos** en 138 filas (120 duplicadas); el "pool de 160 pares" son 18 tareas con variaciones. Es probable el sobreajuste a plantillas. | `python3 dataset/audit_dataset.py` |
| F3 | Alta | Los puntajes de base (48.2) y frontier (90.5) **no tienen reporte crudo**: están escritos a mano en `DEMO_DATA` de `evaluation/compare_models.py`, y `--demo` es `True` por defecto. | `grep -n composite_cas evaluation/compare_models.py` |
| F4 | Media | `benchmark_report_final.json` (prom. 50.0) es el único reporte tipo base y no coincide con 48.2. Sus primeras muestras puntúan todas 50, lo que sugiere que se pudo puntuar la entrada sin refactorizar (sin confirmar). | Inspeccionar `results[*].total_score`. |
| F5 | Alta | Ningún reporte registraba qué modelo lo generó, así que 76.33 no se puede atribuir al GGUF. | Los reportes no tenían bloque `meta` antes de este cambio. |
| F6 | Media | En modo live un prompt fallido se descartaba en silencio y el promedio se calculaba solo sobre los exitosos. | Corregido: ahora se registra `meta.prompts_failed`. |
| F7 | Media | CAS es coincidencia de patrones regex/AST (p. ej. presencia de `interface I...Repository`, `Result.ok`). No verifica compilación ni preservación de comportamiento, y las plantillas de entrenamiento contienen esos patrones. | `evaluation/README.md` §1. |
| F8 | Baja | El baseline frontier figura como "Gemini 3.8 Flash"; no hay ejecución registrada contra la suite. | n/a |

## 3. No verificado

- Que los subpuntajes de `DEMO_DATA["ecc"]` coincidan con los valores por categoría del reporte crudo de 76.33.
- El código de entrenamiento (`training/train_lora.py`) y sus hiperparámetros.
- Si el endpoint servido durante la corrida de 76.33 era el GGUF publicado.

## 4. Cambios realizados junto con esta auditoría

| Archivo | Cambio |
| :--- | :--- |
| `evaluation/eval_benchmark.py` | Agrega bloque `meta` (modelo, SHA-256 del archivo, endpoint, suite, prompts fallidos), `--model-name`, `--model-file`, `--save-completions`. Las claves existentes del reporte no cambian. |
| `evaluation/run_comparison.sh` | Ejecuta la misma suite contra varios endpoints con chequeo de salud previo. |
| `dataset/audit_dataset.py` | Auditoría repetible de duplicados y fuga (`--strict` sale con código 1 si hay solape). |

## 5. Higiene de afirmaciones hasta tener resultados de la Spark

- Presentar 76.3 como "puntaje heurístico propio sobre una suite de 30 casos, modelo sin atribución registrada".
- No citar 48.2 ni 90.5 como mediciones.
- No describir `eval_holdout.jsonl` como aislado.
