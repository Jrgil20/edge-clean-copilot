# Edge Clean Copilot (ECC)

> **Small Language Model (SLM) especializado y nativo en el borde, con CLI Hexagonal para refactorización estricta de Clean Architecture y Domain-Driven Design.**

[![Progreso de Fase](https://img.shields.io/badge/Progreso-70%25%20Verificado-blue.svg)](docs/progress-and-milestones.md)
[![Arquitectura](https://img.shields.io/badge/Arquitectura-Hexagonal%20%2F%20Clean-emerald.svg)](propuesta.md)
[![Modelo Base](https://img.shields.io/badge/SLM%20Base-Qwen2.5--Coder--1.5B--Instruct-orange.svg)](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct)
[![Cuantización](https://img.shields.io/badge/Borde%20Offline-GGUF%20Q4__K__M%20(45--70%20tok%2Fs)-purple.svg)](training/convert_to_gguf.sh)
[![Tests](https://img.shields.io/badge/Vitest-28%2F28%20en%20Verde-brightgreen.svg)](cli/tests/)
[![Licencia](https://img.shields.io/badge/Licencia-Académica%20%2F%20MIT-lightgrey.svg)](README.md)

🌐 **[English version available →](../README.md)**

---

## 1. Resumen Ejecutivo

**Edge Clean Copilot (ECC)** es un asistente de código offline y especializado, diseñado para aplicar principios de **Clean Architecture**, **Puertos y Adaptadores (Arquitectura Hexagonal)** y **Domain-Driven Design (DDD)** directamente en la estación de trabajo del desarrollador, sin depender de conexiones a APIs en la nube.

Los modelos comerciales de código suelen fallar en los límites arquitectónicos: introducen tipos `any`, generan acoplamientos circulares entre capas, mezclan SDKs de bases de datos dentro de entidades de dominio y crean dependencias innecesarias de frameworks. ECC resuelve esto entrenando un Small Language Model ágil (**Qwen2.5-Coder-1.5B-Instruct**) con pares curados de refactorización arquitectónica de alta señal, desplegándolo localmente mediante cuantización **GGUF Q4_K_M** servido con `llama.cpp` a **45–70 tokens/segundo** en hardware estándar.

> **Valor Arquitectónico Clave:** Más allá de un checkpoint único, ECC está concebido como una **[Factoría de Modelos](docs/model-factory-architecture.md)** reproducible. El pipeline está desacoplado de pesos específicos, permitiendo incorporar, especializar y cuantizar nuevos SLMs de pesos abiertos (Llama-3.2, Gemma-2, DeepSeek) a través de un flujo automatizado y estandarizado.

---

## 2. Metodología Principal: "Cold Staging, Hot Burst"

Para compatibilizar la infraestructura de cómputo compartida (como clusters universitarios) con el desarrollo local continuo, el proyecto sigue el modelo operativo **Cold Staging, Hot Burst**:

```
[ Cold Staging (Laptop de Desarrollo Local) ]
  ├── Curaduría de pares semilla ChatML canónicos
  ├── Partición estratificada determinista del dataset (train/eval holdout)
  ├── Ejecuciones de prueba offline de 1 paso (--dry-run)
  └── Tests unitarios offline de capas CLI mediante MockInferenceAdapter (28/28 en verde)
               │
               ▼ (Ráfaga de Red — SSH / Subred /26)
[ Hot Burst (Cluster NVIDIA DGX Spark) ]
  ├── Destilación de alto rendimiento con Modelo Teacher (Qwen3-Coder-30B en puerto 8085)
  ├── Fine-tuning LoRA multiepoca (train_lora.py con --max-time-minutes 15.0)
  └── Fusión consolidada de pesos (adaptador LoRA + modelo base -> FP16)
               │
               ▼ (Consolidación de Artefactos)
[ Despliegue en el Borde (Máquina Local 100% Offline) ]
  └── Cuantización GGUF (Q4_K_M) servida vía llama-server (sub-15ms TTFT, cero nube)
```

---

## 3. Arquitectura de Subsistemas

El repositorio se divide en cinco subsistemas desacoplados:

```
edge-clean-copilot/
├── cli/          # Cliente CLI hexagonal en TypeScript (Puertos y Adaptadores, sin any)
├── dataset/      # Semillas canónicas, generador sintético y particiones estratificadas
├── training/     # Pipeline de fine-tuning LoRA en PyTorch y scripts de exportación GGUF
├── evaluation/   # Harness automatizado de benchmark Clean Architecture Score (CAS 0-100)
├── docs/         # Especificaciones técnicas, bitácoras de telemetría y roadmaps de ejecución
├── es/           # Espejo completo de documentación en español
└── status.py     # Diagnóstico instantáneo y tablero de reanudación sin dependencias
```

### 3.1 Subsistema CLI Hexagonal (`cli/`)

El cliente CLI respeta Clean Architecture internamente mientras refactoriza código de usuario externamente:

```
cli/src/
├── domain/             # Reglas de negocio de la empresa
│   └── entities/       # Entidad SourceFile (validación de rutas, invariantes de lenguaje)
├── application/        # Reglas de negocio de la aplicación
│   ├── use-cases/      # RefactorCodeUseCase (orquestación funcional)
│   ├── ports/          # IInferenceEngine (contrato abstracto de inferencia)
│   └── dtos/           # RefactorDTO (estructuras tipadas de entrada y salida)
├── infrastructure/     # Adaptadores y herramientas externas
│   ├── ai/             # LlamaServerAdapter (HTTP) y MockInferenceAdapter (testing unitario offline)
│   ├── fs/             # FileDiskReader (I/O determinista sobre disco)
│   └── cli/            # Punto de entrada con Commander.js e interfaz de terminal
└── shared/             # Primitivas transversales
    ├── types/          # Mónada Result<T, E> para manejo determinista de errores
    └── errors/         # Jerarquía tipada DomainError (sin throws descontrolados)
```

#### Guardas Arquitectónicas No Negociables
1. **Regla de Dependencia:** Las capas internas (`domain`, `application`) tienen cero dependencias de capas externas (`infrastructure`, frameworks, file system o red).
2. **Política Zero `any`:** Tipado estricto en todo el codebase; prohibido el uso de `any`.
3. **Mónada de Error Determinista:** Los casos de uso retornan `Result<T, DomainError>` en lugar de lanzar excepciones no tipadas.
4. **Testabilidad 100% Offline:** La suite de tests corre de forma totalmente aislada vía `MockInferenceAdapter` sin requerir un servidor de inferencia activo.

### 3.2 Subsistema de Dataset (`dataset/`)

- **Ejemplos Semilla Canónicos (`dataset/seed_examples.jsonl`):** 8 pares de refactorización de grado productivo extraídos de modelos reales de dominio (ArrowMaze).
- **Generador por Destilación del Teacher (`dataset/generate_with_teacher.py`):** Pipeline automatizado que interroga al modelo teacher de 30B (`Qwen3-Coder-30B-A3B-Instruct`) desplegado en el puerto aislado `8085` de la NVIDIA DGX Spark.
- **Partición Estratificada (`dataset/split_dataset.py`):** División determinista (`seed=42`) generando:
  - `dataset/train.jsonl`: **138 pares** (82.1%, ~156k tokens) para adaptación LoRA.
  - `dataset/eval_holdout.jsonl`: **30 pares** (17.9%, ~35k tokens) aislados estrictamente para evaluación post-entrenamiento (cero fuga de datos).
- **Motor de Validación (`dataset/validate_dataset.py`):** Linter de sintaxis ChatML y cumplimiento de contratos.

### 3.3 Subsistema de Entrenamiento y Cuantización (`training/`)

- **Pipeline Nativo LoRA en PyTorch (`training/train_lora.py`):**
  - **Modelo Base:** `Qwen/Qwen2.5-Coder-1.5B-Instruct`
  - **Configuración LoRA:** Rango $r=16$, $\alpha=32$, cubriendo todas las proyecciones lineales (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`).
  - **Aceleración de Hardware:** Ejecución nativa en `bfloat16` sobre GPU Grace Blackwell GB10 (`2.14.1+cu130`).
  - **Guarda Defensiva de Multi-Tenencia:** Límite estricto de tiempo (`--max-time-minutes 15.0`) para evitar agotar las colas de la máquina compartida.
  - **Fusión de Pesos:** Flag de exportación automática con `model.merge_and_unload()` (`--merge`).
- **Exportación GGUF (`training/convert_to_gguf.sh`):** Pipeline automatizado que convierte los pesos FP16 fusionados a GGUF `Q4_K_M` para inferencia local en `llama.cpp`.

### 3.4 Subsistema de Evaluación (`evaluation/`)

El arnés de evaluación (`evaluation/eval_benchmark.py`) calcula el **Clean Architecture Score (CAS)** en una escala de 0 a 100:

| Componente | Peso | Regla de Validación |
| :--- | :--- | :--- |
| **Aislamiento de Capas** | 25 pts | Entidades de dominio con 0 imports de capas externas o librerías de terceros. |
| **Inversión de Control** | 25 pts | Casos de uso interactúan con adaptadores externos exclusivamente mediante Interfaces (Puertos). |
| **Cumplimiento Zero `any`** | 25 pts | Código TypeScript generado contiene 0 ocurrencias de `any` explícito. |
| **Manejo de Errores Tipado** | 25 pts | Funciones retornan `Result<T, DomainError>` en lugar de throws no tipados. |

---

## 4. Guía Rápida y Flujo de Desarrollo

### Requisitos Previos
- **Python:** 3.10+ (con PyTorch y herramientas de Hugging Face para entrenamiento)
- **Node.js y PNPM:** Node 20+, `pnpm` 10+ (gestor de paquetes obligatorio)

### 4.1 Diagnóstico Instantáneo
Inspeccioná la salud del proyecto, suites de tests y particiones en cualquier momento:
```bash
python3 status.py
```

### 4.2 Ejecutar Tests Unitarios de la CLI
La CLI hexagonal en TypeScript incluye 28 tests unitarios AAA:
```bash
cd cli
pnpm install
pnpm test
```

### 4.3 Validar Particiones del Dataset
Verificá que los pares ChatML cumplan con el esquema formal:
```bash
python3 dataset/validate_dataset.py dataset/train.jsonl
python3 dataset/validate_dataset.py dataset/eval_holdout.jsonl
```

### 4.4 Ejecutar Benchmark de Clean Architecture
Evaluá casos legacy contra la rúbrica calibrada de CAS:
```bash
python3 evaluation/eval_benchmark.py \
  --cases evaluation/test_benchmark_cases.jsonl \
  --output evaluation/benchmark_report.json
```

---

## 5. Tablero de Avance e Hitos Verificados

| Fase | Descripción | Alcance | Estado | Métricas Verificadas |
| :--- | :--- | :--- | :--- | :--- |
| **Fase 1** | Infraestructura y Dataset del Teacher | Semanas 1–3 | **100%** | Enlace directo `/26`, puerto 8085 aislado, 168 pares ChatML particionados (138 train / 30 holdout). |
| **Fase 2** | Adaptación LoRA y Especialización | Semanas 4–7 | **85%** | `train_lora.py` listo con corte temporal; virtualenv y 73% de pesos en NVMe de DGX Spark. |
| **Fase 3** | Consolidación de Pesos y Exportación GGUF | Semanas 8–11 | **50%** | Pipeline automatizado `convert_to_gguf.sh` verificado y listo para ejecutar. |
| **Fase 4** | CLI Hexagonal e Inferencia Offline | Semanas 12–15 | **70%** | 28/28 tests en Vitest en verde (~280ms); arnés de benchmark CAS calibrado. |
| **GLOBAL** | **Madurez Integral del Proyecto** | **General** | **70%** | **Staging de grado productivo, listo para la ráfaga de ejecución en DGX Spark.** |

---

## 6. Índice de Documentación Técnica

Para especificaciones arquitectónicas profundas, runbooks y telemetría:
- **[Roadmap Detallado de Ejecución (Semanas 4–15)](docs/detailed-roadmap.md):** Plan táctico, hitos y entregables.
- **[Tablero de Progreso e Hitos](docs/progress-and-milestones.md):** Registro de validación de hitos basado en evidencia.
- **[Reporte de Sesión: 2026-10-22](docs/session-2026-10-22-burst-and-lessons.md):** Telemetría del cluster, post-mortem de puertos y destilación sintética.
- **[Propuesta Técnica Académica](propuesta.md):** Fundamento teórico, hipótesis de investigación y articulación académica.
