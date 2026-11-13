# Edge Clean Copilot (ECC)

> **Prueba de concepto:** un modelo de lenguaje pequeño (Qwen2.5-Coder-1.5B-Instruct + LoRA) que corre offline como archivo GGUF y refactoriza fragmentos pequeños de TypeScript hacia Clean Architecture / DDD, más un CLI hexagonal para usarlo.

[![Estado](https://img.shields.io/badge/Estado-Prueba%20de%20Concepto-yellow.svg)](docs/next-steps.md)
[![Modelo Base](https://img.shields.io/badge/Base-Qwen2.5--Coder--1.5B--Instruct-orange.svg)](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct)
[![Cuantización](https://img.shields.io/badge/GGUF-Q4__K__M%20(~12%20tok%2Fs%20CPU)-purple.svg)](../training/convert_to_gguf.sh)
[![Tests](https://img.shields.io/badge/Vitest-44%20en%20verde-brightgreen.svg)](../cli/tests/)
[![Licencia](https://img.shields.io/badge/Licencia-Académica%20%2F%20MIT-lightgrey.svg)](README.md)

🌐 **[English version available →](../README.md)**

---

## 1. Qué es (y qué no es)

ECC pone a prueba una idea: **¿puede un modelo de 1.5B parámetros, ajustado con un conjunto pequeño de ejemplos de arquitectura, producir código que siga las convenciones de Clean Architecture con más frecuencia que su modelo base, corriendo offline en la CPU de un portátil?**

En el benchmark propio del proyecto la respuesta es un sí con matices (ver §3). El modelo se entrenó, se fusionó, se cuantizó a GGUF y se sirve con `llama.cpp`; el pipeline completo está en este repositorio.

**No** es una herramienta de producción:

- Los datos de entrenamiento son pocos y repetitivos (18 prompts distintos detrás de 138 filas de entrenamiento).
- El benchmark mide si la salida *parece* arquitectónicamente limpia (patrones como puertos, `Result`, ausencia de `any`), no si compila ni si conserva el comportamiento.
- Los resultados vienen de una sola suite de 30 casos escrita por el propio autor. Ningún modelo frontera se ha evaluado con ella.
- Es lento por diseño: unos 12 tokens/segundo en un portátil solo con CPU (Intel Core i5-10310U). Está pensado para fragmentos pequeños y acotados.

Los problemas conocidos y el trabajo para resolverlos están en **[docs/next-steps.md](docs/next-steps.md)**.

---

## 2. Cómo se construyó: "Cold Staging, Hot Burst"

El tiempo de GPU solo estaba disponible en ventanas cortas en un NVIDIA DGX Spark (GB10) compartido. Todo lo que no necesita GPU se preparó antes en un portátil:

```
[ Cold Staging: portátil ]
  ├── Ejemplos semilla escritos a mano (ChatML)
  ├── Partición determinista train/holdout (seed=42)
  ├── Ejecuciones de prueba de 1 paso (--dry-run)
  └── Tests unitarios del CLI contra un motor de inferencia mock
               │
               ▼
[ Hot Burst: DGX Spark ]
  ├── Generación de pares con un modelo maestro (Qwen3-Coder-30B)
  ├── Fine-tuning LoRA con límite de tiempo (--max-time-minutes 15)
  └── Fusión del adaptador con los pesos base (FP16)
               │
               ▼
[ Borde: portátil, offline ]
  └── GGUF Q4_K_M servido con llama-server
```

---

## 3. Resultados medidos

Comparación directa en el DGX Spark: misma suite, misma cuantización (Q4_K_M), misma configuración de `llama-server`, motor de puntuación AST. Evidencia: [`evaluation/reports/spark-20261105T143540Z/`](../evaluation/reports/spark-20261105T143540Z/RESULT.md).

| Componente CAS (máx.) | Fine-tune | Base | Delta |
| :--- | ---: | ---: | ---: |
| Frontera de dominio (30) | 30.0 | 24.0 | +6.0 |
| Seguridad de invariantes (25) | 2.7 | 0.3 | +2.4 |
| Desacople por puertos (25) | 22.5 | 15.8 | +6.7 |
| Tipado TypeScript (20) | 19.7 | 17.8 | +1.9 |
| **CAS compuesto (100)** | **74.8** | **58.0** | **+16.8** |

Cómo leer estas cifras:

- **Una respuesta vacía saca 50.** Gana 30 por no tener imports prohibidos y 20 por no tener `any`. El modelo base queda 8 puntos por encima de no hacer nada; el fine-tune, unos 25. Ninguna de las dos ejecuciones produjo salidas vacías ni rechazos.
- **La seguridad de invariantes es débil en ambos modelos** (2.7 / 25). El fine-tune rara vez produce constructores con validación o manejo con `Result`.
- **El ruido entre ejecuciones existe.** El mismo GGUF (mismo SHA-256) dio 72.5 en la CPU del portátil y 74.8 en la GPU del Spark, con 17/30 casos idénticos y una diferencia media por caso de 4.7 puntos. Una ejecución anterior sin modelo registrado dio 76.3 y difería de la del portátil en 17.8 puntos por caso. Diferencias menores a unos 5 puntos deben tratarse como ruido.
- **Aún sin medir:** si el código compila, si conserva el comportamiento, cuánto saca el modelo base con un prompt few-shot, y cuánto sacan el maestro de 30B o un modelo frontera.

Auditoría completa: [docs/evaluation/evaluation-audit-2026-11-05.md](docs/evaluation/evaluation-audit-2026-11-05.md).

---

## 4. Estructura del repositorio

```
edge-clean-copilot/
├── cli/          # CLI en TypeScript (hexagonal: domain / application / infrastructure)
├── dataset/      # Ejemplos ChatML, generador con maestro, scripts de partición y auditoría
├── training/     # Entrenamiento LoRA (basado en recetas) y exportación GGUF
├── evaluation/   # Harness del benchmark CAS, suites y reportes atribuidos
├── docs/         # Runbooks, auditoría, bitácoras de progreso
├── es/           # Espejo de la documentación en español
└── status.py     # Panel rápido de estado del proyecto
```

### 4.1 CLI (`cli/`)

Un CLI pequeño en TypeScript que lee un archivo, lo envía a un endpoint de `llama-server` (o a un motor mock) e imprime o escribe el resultado refactorizado. Sigue las mismas convenciones que el modelo aprende a producir:

- `domain/` y `application/` no importan de `infrastructure/` ni de paquetes de terceros.
- La inferencia pasa por un puerto (`IInferenceEngine`), con `LlamaServerAdapter` y `MockInferenceAdapter` como adaptadores.
- Las funciones devuelven `Result<T, E>` con errores tipados en vez de lanzar excepciones.
- TypeScript estricto, sin `any`. Todos los tests corren offline contra el motor mock.

### 4.2 Dataset (`dataset/`)

ChatML en JSONL (`system` / `user` / `assistant`).

| Fuente | Filas | Notas |
| :--- | ---: | :--- |
| `seed_examples.jsonl` | 8 | Escritos a mano, tomados de un proyecto real (ArrowMaze). |
| `generated_examples.jsonl` | 160 | Generados por el maestro de 30B a partir de un conjunto pequeño de plantillas de prompt. |
| `authored_examples.jsonl` | 19 | Ejemplos `ARCH_REFACTOR` y `SOLID_CRITIQUE` escritos a mano, añadidos después del entrenamiento. |

**El modelo publicado se entrenó con una partición anterior** (commit `64f3c6c`): 138 filas de entrenamiento construidas a partir de solo **18 prompts distintos**, con un holdout que compartía 28 de sus 30 prompts con el entrenamiento. Esa partición ya no está en el árbol de trabajo.

El `split_dataset.py` actual parte por prompt normalizado y descarta respuestas truncadas. Al ejecutarlo se obtienen 91 filas de entrenamiento / 34 de holdout a partir de 36 prompts distintos, sin solapamiento de prompts (`python3 dataset/audit_dataset.py`). **Esta partición no se ha usado para entrenar.**

La suite de evaluación (`evaluation/legacy_benchmark_suite.jsonl`, 30 casos) no comparte prompts ni código con los datos de entrenamiento.

### 4.3 Entrenamiento (`training/`)

- Base: `Qwen/Qwen2.5-Coder-1.5B-Instruct`. LoRA r=16, α=32 sobre todas las proyecciones de atención y MLP, bfloat16.
- Los hiperparámetros están en archivos de receta (`training/recipes/*.yaml`); los flags de CLI los sobrescriben.
- Ejecución publicada: 3 épocas, unos 5.5 minutos en el GB10; loss final de entrenamiento 0.031. No se registró loss de validación. Un loss tan bajo con 18 prompts distintos apunta a memorización.
- `--merge` fusiona el adaptador con los pesos base; `convert_to_gguf.sh` exporta Q4_K_M (941 MB), con Q5_K_M y Q8_0 opcionales.

### 4.4 Evaluación (`evaluation/`)

`eval_benchmark.py` calcula el **Clean Architecture Score (CAS, 0–100)** usando el AST del compilador de TypeScript (`ast_analyzer.ts`), con una alternativa por regex:

| Componente | Puntos | Regla |
| :--- | ---: | :--- |
| Frontera de dominio | 30 | Sin imports de frameworks/ORMs (`express`, `typeorm`, `prisma`, `axios`, …). |
| Seguridad de invariantes | 25 | Uso de `Result` y guardas de validación en constructores. |
| Desacople por puertos | 25 | `interface I…Repository/Port/Gateway` e inyección por constructor. |
| Tipado TypeScript | 20 | −5 por cada `any` explícito. |

Es coincidencia de patrones. No compila la salida ni verifica que el comportamiento se conserve. Los reportes registran el nombre del modelo, el SHA-256 del GGUF, el endpoint y la suite, para que cada puntuación se pueda atribuir a un modelo.

---

## 5. Inicio rápido

Requisitos: Python 3.10+, Node 20+, `pnpm` 10+. Para entrenar se necesita además PyTorch y los paquetes de `training/requirements.txt`.

```bash
python3 status.py                          # estado del proyecto

cd cli && pnpm install && pnpm test        # tests del CLI (offline)

python3 -m unittest discover -s evaluation/tests -v
python3 -m unittest dataset/test_split_dataset.py -v
python3 -m unittest dataset/test_audit_dataset.py -v

python3 dataset/validate_dataset.py dataset/train.jsonl
python3 dataset/audit_dataset.py --typecheck   # duplicados, fugas, truncamiento, any, tsc
```

### 5.1 Refactorizar un archivo

Requiere `llama-server` sirviendo el GGUF (por defecto `http://127.0.0.1:8080`), o `--mock` para probar sin modelo. `bin/` debe estar en tu `PATH`.

```bash
clean-copilot refactor ruta/a/Archivo.ts --diff
clean-copilot refactor ruta/a/Archivo.ts -o ruta/a/ArchivoRefactorizado.ts
clean-copilot refactor ruta/a/Archivo.ts --mock
```

### 5.2 Enrutar Copilot de VS Code a un modelo local

`bin/copilot-local` edita `debug.overrideProxyUrl` en `~/.config/Code/User/settings.json`. Recarga la ventana de VS Code después de cambiar.

```bash
copilot-local on        # ECC en el Spark (puerto 8085)
copilot-local on qwen   # Qwen3-Coder 30B en el Spark (puerto 8080)
copilot-local status
copilot-local off       # volver al servicio de GitHub
```

---

## 6. Más documentación

- [Análisis del proyecto](docs/project/project-analysis.md): objetivos frente a resultados, fortalezas, hallazgos y afirmaciones seguras (para citar el proyecto como antecedente).
- [Casos de uso válidos](docs/usage/use-cases.md): dónde usar el modelo y dónde no.
- [docs/next-steps.md](docs/next-steps.md): problemas conocidos y trabajo planeado.
- [Auditoría de evaluación](docs/evaluation/evaluation-audit-2026-11-05.md): hallazgos detrás de las advertencias anteriores.
- [Runbook de evaluación en Spark](docs/evaluation/spark-eval-runbook.md) y [plan del día en Spark](docs/evaluation/spark-day-plan.md): cómo se produjo la comparación directa.
- [Model card](../MODEL_CARD.md) y [guía de uso y distribución](docs/usage/model-usage-and-sharing-guide.md).
- [Arquitectura de la Factoría de Modelos](docs/architecture/model-factory-architecture.md): diseño basado en recetas para entrenar otros modelos base (existen recetas para Llama-3.2 y Gemma-2, pero no se han entrenado).
- [Bitácora de progreso](docs/history/progress-and-milestones.md) y [propuesta académica](docs/project/propuesta.md).
