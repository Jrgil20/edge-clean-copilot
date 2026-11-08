# Plan del Día de la Spark — conectar y ejecutar

> **Objetivo:** el día de la sesión en la Spark, las únicas acciones manuales son: conectar, sincronizar, correr un comando y copiar los resultados.
> **Contexto:** [evaluation-audit-2026-11-05.md](./evaluation-audit-2026-11-05.md). Alternativa manual: [spark-eval-runbook.md](./spark-eval-runbook.md).
> **Supuestos (tomados de los docs del repo, sin verificar en la Spark):** usuario `ucab-spark1`, proyecto en `/home/ucab-spark1/proyecto`, `llama.cpp` en `~/llama.cpp`, modelo base `Qwen/Qwen2.5-Coder-1.5B-Instruct` en el cache `~/.cache/huggingface/hub`.

## 1. La noche anterior (laptop)

| # | Acción | Listo cuando |
| :-- | :-- | :-- |
| 1 | Pushear `proyecto/` y el repo padre para que la Spark pueda traer los scripts nuevos. | `git status -sb` no muestra `ahead`. |
| 2 | Confirmar que el modelo base sigue en el cache NVMe de la Spark (si no puedes esta noche, es lo primero de la mañana). | El preflight muestra `base HF snapshot cached`. |

## 2. Mañana (en la Spark)

| # | Comando | Esperado |
| :-- | :-- | :-- |
| 1 | Conectar a la Spark (tu alias SSH habitual). | Shell en la Spark. |
| 2 | `cd ~/proyecto && git pull --ff-only` | Fast-forward. Si `~/proyecto` no es un checkout git, copiar `evaluation/`, `dataset/audit_dataset.py` y `docs/` desde la laptop con `scp -r`. |
| 3 | `cd evaluation && ./spark_day.sh --preflight-only` | `Preflight OK.` No se inicia ni modifica nada. |
| 4 | `./spark_day.sh` | Construye el GGUF base si falta, levanta ambos modelos, corre el benchmark e imprime `RESULT.md`. |
| 5 | Desde la laptop: ejecutar la línea `scp -r ...` que imprime el paso 4 al final. | Carpeta en `evaluation/reports/spark-<UTC>/`. |

## 3. Si el preflight falla

El script lista todos los fallos juntos y no cambia nada.

| Mensaje | Solución |
| :-- | :-- |
| `llama-server not found` | `export LLAMA_SERVER=/ruta/a/llama-server` |
| `llama.cpp directory not found` | `export LLAMA_CPP_DIR=/ruta/a/llama.cpp` |
| `base model not cached` | Pre-cachear `Qwen/Qwen2.5-Coder-1.5B-Instruct`, o `export BASE_SNAPSHOT=<dir del snapshot>`. |
| `AST engine unavailable` | `cd ~/proyecto/cli && pnpm install --frozen-lockfile`. No usar el fallback regex: no es comparable con el 76.3 anterior. |
| `port 8085/8086 is busy serving ...` | El script no lo toca. Libera el puerto tú o define `PORT_FT` / `PORT_BASE`. |
| `less than 8 GB free` | Liberar disco; la conversión crea un F16 intermedio de ~3 GB. |

## 4. Después de la corrida

| # | Acción | Listo cuando |
| :-- | :-- | :-- |
| 1 | Abrir `RESULT.md`: ¿todos los chequeos marcados? ¿leíste el veredicto? | Veredicto registrado. |
| 2 | Leer 5 completions por modelo en `cas/completions_*.jsonl`. | Son código refactorizado, no la entrada repetida. |
| 3 | Actualizar afirmaciones según [spark-eval-runbook.md §6](./spark-eval-runbook.md). | Los docs coinciden con el reporte. |
| 4 | Commit en `proyecto/` y luego actualizar el puntero en el repo padre. | Ambos pusheados. |

## 5. Qué produce la corrida

| Archivo (en `evaluation/reports/spark-<UTC>/`) | Propósito |
| :-- | :-- |
| `RESULT.md` | Tabla, chequeos automáticos, veredicto. |
| `environment.txt` | Host, GPU, versión de `llama-server`, commit git, contexto, puertos. |
| `dataset_audit.txt` | Auditoría de fuga (se espera `LEAKAGE` hasta reconstruir el split). |
| `cas/report_*.json`, `cas/completions_*.jsonl` | Puntajes atribuidos y salidas crudas. |
| `server_<puerto>.log` | Logs del servidor para depurar. |

## 6. Garantías de `spark_day.sh`

- Nunca abre conexiones SSH ni toca los puertos 8080 u 8084.
- Detiene solo los servidores que él inició; reutiliza uno en 8085/8086 únicamente si reporta el archivo de modelo esperado.
- Marca la corrida como `INVALID` si falló algún prompt, los motores difieren, los modelos son idénticos o la cantidad de muestras no es 30.
- Probado localmente contra un `llama-server` falso; **no** se ha ejecutado en la Spark real.
