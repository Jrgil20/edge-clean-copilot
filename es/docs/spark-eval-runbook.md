# Runbook de Evaluación en Spark

> **Objetivo:** reemplazar los números de benchmark escritos a mano y sin atribución por reportes reproducibles con modelo identificado.
> **Camino rápido:** [spark-day-plan.md](./spark-day-plan.md) (`evaluation/spark_day.sh` automatiza las secciones 1–4; este archivo es la alternativa manual).
> **Lectura previa:** [evaluation-audit-2026-11-05.md](./evaluation-audit-2026-11-05.md).
> **Restricciones:** los puertos `8080` y `8084` pertenecen a otros servicios del laboratorio; usar `8085` (ECC) y `8086` (base). No detener procesos que no iniciaste.

## 1. Preflight

```bash
# En la Spark: confirmar que los puertos están libres o ya son nuestros
ss -ltnp | grep -E ':(8080|8084|8085|8086)\b'

# En la laptop: chequeos previos al burst
python3 proyecto/status.py
python3 proyecto/dataset/audit_dataset.py   # esperado hoy: LEAKAGE (conocido, F1/F2)
```

## 2. Servir ambos modelos con la misma cuantización

La comparación solo es justa si base y fine-tune comparten cuantización (Q4_K_M) y flags del servidor.

```bash
# Fine-tune (ya está en el repo)
llama-server -m proyecto/training/output/gguf/clean-copilot-1.5b-q4_k_m.gguf \
  --port 8085 -c 4096

# Base: Qwen2.5-Coder-1.5B-Instruct en Q4_K_M.
# Opción A: descargar un GGUF ya hecho (verificar antes que el repo exista).
# Opción B: convertir con el script del proyecto, mismo pipeline que el fine-tune:
#   training/convert_to_gguf.sh --input-dir <snapshot HF> --output-dir training/output/gguf-base \
#     --model-name qwen2.5-coder-1.5b-base --clean-f16
llama-server -m /ruta/a/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf \
  --port 8086 -c 4096
```

Anotar: build/commit de `llama-server`, tamaño de contexto, GPU o CPU, cuantización.

## 3. Ejecutar la comparación

```bash
cd proyecto/evaluation
./run_comparison.sh \
  --model "ecc-ft=http://127.0.0.1:8085/v1/chat/completions=../training/output/gguf/clean-copilot-1.5b-q4_k_m.gguf" \
  --model "qwen-base=http://127.0.0.1:8086/v1/chat/completions=/ruta/a/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
```

La salida queda en `evaluation/reports/<timestamp UTC>/`:

| Archivo | Contenido |
| :--- | :--- |
| `report_<nombre>.json` | Puntajes más `meta` (modelo, SHA-256, endpoint, suite, prompts fallidos). |
| `completions_<nombre>.jsonl` | Salidas crudas del modelo para inspección manual. |
| `suite.jsonl`, `suite.sha256` | Suite exacta utilizada. |

## 4. Chequeos de aceptación

| Chequeo | Condición de aprobado |
| :--- | :--- |
| Sin prompts descartados | `meta.prompts_failed` es `[]` en todos los modelos. |
| Misma suite | Ambos reportes muestran el mismo `cases_file`; `suite.sha256` guardado. |
| Atribución | `meta.model_sha256` presente y distinto entre base y fine-tune. |
| Salidas reales | Leer al menos 5 completions por modelo; confirmar que son código refactorizado y no la entrada repetida. |
| Sensatez del puntaje | Si base y fine-tune difieren en menos de ~5 puntos, no afirmar mejora. |

## 5. Seguimientos opcionales (si hay tiempo)

1. Correr la suite dos veces por modelo para ver la varianza (temperatura 0.1, no 0).
2. Verificar tipos de las completions con `tsc --noEmit` para complementar el CAS por patrones.
3. Correr el baseline frontier con el mismo script si hay endpoint; si no, eliminar su fila.

## 6. Después de la corrida: actualizar afirmaciones

| Acción | Archivo |
| :--- | :--- |
| Reemplazar los valores base/ecc/cloud de `DEMO_DATA` por números derivados de los reportes, o marcarlos "no medido". | `evaluation/compare_models.py` |
| Actualizar puntajes en la model card, badges del README y el informe final. | `MODEL_CARD.md`, `README.md`, `docs/final-report-and-presentation.md` |
| Corregir la redacción "estrictamente aislado" del split holdout. | `docs/final-report-and-presentation.md`, `docs/progress-and-milestones.md` |
| Reflejar todo lo anterior en español. | `es/` |
| Commit dentro de `proyecto/` y luego actualizar el puntero en el repo padre. | git |

## 7. Diferido (requiere reentrenar, no para la primera sesión en la Spark)

- Reconstruir el split para que el código del holdout nunca aparezca en entrenamiento (F1) y aumentar la diversidad de prompts más allá de 18 tareas (F2). Repetir `dataset/audit_dataset.py --strict` hasta que pase; luego reentrenar y reevaluar.
