# Arquitectura de Factoría de Modelos y Especialización Escalable de SLMs

> **Especificación Técnica Autorizada**  
> **Repositorio:** `edge-clean-copilot`  
> **Concepto Central:** Desacoplamiento de la evolución de modelos fundacionales respecto a la especialización de dominio mediante una factoría reproducible y consciente del hardware para Modelos de Lenguaje Pequeños (SLMs).

---

## 1. Visión Arquitectónica: De Checkpoints Aislados a una Factoría de Modelos

Un error común en la ingeniería de IA aplicada es tratar el ajuste fino (fine-tuning) como un script desechable de una sola ejecución que produce un artefacto estático. En el panorama rápidamente cambiante de los SLMs de pesos abiertos (como Qwen, Llama, Gemma, DeepSeek o SmolLM), cualquier checkpoint específico queda obsoleto con rapidez.

**Edge Clean Copilot no está diseñado como un modelo aislado, sino como una Factoría de Modelos industrializada.**

La factoría provee una canalización (pipeline) automatizada y de extremo a extremo que ingiere nuevos SLMs base del estado del arte, aplica adaptación específica de dominio (invariantes de Clean Architecture y Diseño Guiado por el Dominio), cuantiza los pesos para inferencia en el borde (edge) y evalúa el modelo resultante bajo métricas estrictas de determinismo y calidad de ingeniería de software.

```
                  ┌────────────────────────────────────────────────────────┐
                  │             POOL DE SLMs BASE DE PESOS ABIERTOS        │
                  │ (Qwen2.5-Coder, Llama-3.2, Gemma-2, SmolLM2, DeepSeek) │
                  └───────────────────────────┬────────────────────────────┘
                                              │ Ingesta de Pesos Base
                                              ▼
┌─────────────────────────┐       ┌───────────────────────────────┐
│ FACTORÍA DE DATOS SINT. │       │  HARNESS DE ESPECIALIZACIÓN   │
│ • Taxonomía antipatrones│──────▶│  • Targets parametrizados     │
│ • Semillas canónicas    │ Pares │  • Límite temporal (DGX Spark)│
│ • Validador invariantes │       │  • Fusión atómica de pesos    │
└─────────────────────────┘       └───────────────┬───────────────┘
                                                  │ Pesos Fusionados FP16
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │   MOTOR DE CUANTIZACIÓN EDGE  │
                                  │   • Conversión llama.cpp      │
                                  │   • Formatos GGUF: Q4_K_M, Q8 │
                                  └───────────────┬───────────────┘
                                                  │ Artefacto Edge GGUF
                                                  ▼
┌─────────────────────────┐       ┌───────────────────────────────┐
│ ADAPTADOR CLI HEXAGONAL │◀──────│  CLEAN ARCH SCORE (CAS)       │
│ • Runtime desconectado  │ Server│  • Aislamiento dominio (30%)  │
│ • Pure TS / Cero any    │       │  • Seguridad Result (25%)     │
│ • Diffs ANSI en terminal│       │  • Puertos y Adaptadores (25%)│
└─────────────────────────┘       │  • Penalización por any (20%) │
                                  └───────────────────────────────┘
```

---

## 2. Los Cinco Subsistemas Desacoplados de la Factoría

La factoría se descompone en cinco capas autónomas siguiendo los principios de Clean Architecture y Separación de Responsabilidades:

### 2.1 Subsistema A: Motor de Docente y Datasets Sintéticos
- **Responsabilidad:** Generar, curar y validar pares de instrucción-refactorización que ilustran violaciones de Clean Architecture y sus resoluciones canónicas.
- **Invarianza:** Independiente del modelo de entrenamiento final. El dataset encapsula conocimiento puro de ingeniería de software (aislamiento de dominio, Value Objects, puertos/adaptadores, manejo funcional de errores).
- **Activos Principales:**
  - `dataset/seed_examples.jsonl`: Pares canónicos de referencia.
  - `dataset/validate_dataset.py`: Validador sintáctico y estructural en múltiples etapas.
  - `dataset/train.jsonl` y `dataset/eval_holdout.jsonl`: Particiones deterministas (seed=42).

### 2.2 Subsistema B: Harness de Entrenamiento LoRA Parametrizado
- **Responsabilidad:** Especializar modelos base de pesos abiertos utilizando Adaptación de Bajo Rango (LoRA) bajo presupuestos de cómputo controlados.
- **Características Clave:**
  - **Agnóstico al Modelo:** Los módulos objetivo, dimensiones ocultas y cabezas de atención se configuran dinámicamente mediante flags CLI (`--base-model`, `--r`, `--alpha`, `--target-modules`).
  - **Seguro frente a Interrupciones:** Límites nativos de tiempo de ejecución (`--max-time-minutes`) que previenen preemption o throttling térmico en hardware compartido (e.g., DGX Spark).
  - **Fusión Atómica:** Integra automáticamente los deltas LoRA en los pesos base al finalizar (`--merge`).

### 2.3 Subsistema C: Motor de Compresión y Cuantización
- **Responsabilidad:** Transformar pesos densos FP16 en binarios GGUF optimizados y alineados para ejecución en el borde.
- **Matriz de Cuantización:**
  - `Q4_K_M`: Predeterminado óptimo para borde (~0.94 GB, cabe en 1.5 GB de RAM, ~12 t/s medidos en CPU).
  - `Q8_0`: Referencia de alta fidelidad para servidores o estaciones de trabajo de desarrollo.
- **Canalización:** Automatizada a través de `training/convert_to_gguf.sh`.

### 2.4 Subsistema D: Evaluación y Calibración Arquitectónica (CAS)
- **Responsabilidad:** Cuantificar la adherencia del modelo a los patrones de arquitectura limpia mediante el **Clean Architecture Score (CAS, 0–100 puntos)**.
- **Independencia Evaluativa:** CAS evalúa tanto respuestas sintéticas fuera de línea como endpoints de inferencia HTTP en vivo (`llama-server`) sin sesgo hacia la arquitectura interna del modelo.
- **Desglose de Métricas:**
  1. *Aislamiento de Límites de Dominio (30%):* Ausencia total de frameworks/ORM/HTTP en la lógica de dominio.
  2. *Seguridad de Invariantes y Patrón Result (25%):* Integridad en Value Objects, validación defensiva en constructores y tipo funcional `Result<T, E>`.
  3. *Desacoplamiento de Puertos y Adaptadores (25%):* Interfaces abstractas e inyección de dependencias.
  4. *Rigor de Tipado (20%):* Eliminación estricta de `any` (-5 pts por violación) y tipado estricto en TypeScript.

### 2.5 Subsistema E: Cliente Hexagonal para el Borde (CLI)
- **Responsabilidad:** Proveer a los desarrolladores un asistente de refactorización local, con latencia mínima y capacidad de operar 100% desconectado en sus estaciones de trabajo.
- **Diseño:** Implementado en TypeScript estricto (cero `any`), desacoplando el protocolo de inferencia (`IInferenceEngine`) del sistema de archivos y de la interfaz de consola.

---

## 3. Receta: Incorporación de un Nuevo SLM Base

Cuando se publica un nuevo modelo fundacional (por ejemplo, `Qwen/Qwen2.5-Coder-3B-Instruct`, `meta-llama/Llama-3.2-3B-Instruct` o `google/gemma-2-2b-it`), se debe ejecutar la siguiente secuencia estandarizada para producir una variante especializada de Edge Clean Copilot:

```bash
# Paso 1: Verificación previa en DGX Spark (valida descarga de HF y tokenización)
python3 proyecto/training/train_lora.py \
  --base-model "Qwen/Qwen2.5-Coder-3B-Instruct" \
  --dry-run

# Paso 2: Ráfaga de entrenamiento LoRA con fusión automática de pesos
python3 proyecto/training/train_lora.py \
  --base-model "Qwen/Qwen2.5-Coder-3B-Instruct" \
  --output-dir "output/clean-copilot-qwen3b" \
  --max-time-minutes 30.0 \
  --r 16 \
  --lora-alpha 32 \
  --merge

# Paso 3: Cuantización a binario GGUF para el borde (Q4_K_M)
cd proyecto/training
./convert_to_gguf.sh \
  --model-dir output/clean-copilot-qwen3b \
  --output-name clean-copilot-3b-q4km.gguf \
  --clean-f16

# Paso 4: Calibración y evaluación en el benchmark CAS
python3 proyecto/evaluation/eval_benchmark.py \
  --url "http://127.0.0.1:8085/v1/chat/completions" \
  --prompts proyecto/evaluation/legacy_benchmark_suite.jsonl \
  --output proyecto/evaluation/benchmark_report_qwen3b.json

# Paso 5: Actualización de la matriz comparativa multimodelos
python3 proyecto/evaluation/compare_models.py \
  --candidate-report proyecto/evaluation/benchmark_report_qwen3b.json
```

---

## 4. Dimensiones de Escalabilidad

| Dimensión | Estado Inicial (v0.1) | Estado de la Factoría Escalada (v1.0+) |
|---|---|---|
| **Escala del Modelo Base** | Qwen 2.5 Coder 1.5B | SLMs de 1B, 3B, 7B y arquitecturas MoE (Qwen, Llama, DeepSeek) |
| **Consumo en el Borde** | ~0.94 GB disco / ~1.5 GB RAM / ~12 t/s (CPU) | Múltiples niveles: Ultra-Edge (0.5 GB) hasta Workstations (4 GB) |
| **Alcance de Lenguajes** | TypeScript / JavaScript | Políglota (Go Clean Arch, Rust Hexagonal, Python DDD) |
| **Entornos de Cómputo** | NVIDIA DGX Spark individual (A100) | Clústeres distribuidos multi-GPU, Apple Silicon MLX |
| **Runtime de Inferencia** | llama.cpp (`llama-server`) | llama.cpp, vLLM, ONNX Runtime, WebGPU en navegador |

---

## 5. Invarianza Arquitectónica y Gobernanza

Para preservar la consistencia de la plataforma a medida que se integran nuevos modelos:
1. **El Dataset es la Fuente de Verdad:** Todo nuevo modelo debe ajustarse sobre datasets validados (`validate_dataset.py`) para evitar la degradación de dominio.
2. **CAS es la Puerta de Calidad:** Ninguna variante se promueve a versión final sin alcanzar `CAS >= 80.0` en la suite de 30 casos de prueba.
3. **Cliente Desacoplado:** El cliente CLI (`clean-copilot`) nunca contiene lógica de análisis dependiente de un modelo particular. Se comunica exclusivamente mediante el formato estándar ChatML a través de la interfaz `IInferenceEngine`.
