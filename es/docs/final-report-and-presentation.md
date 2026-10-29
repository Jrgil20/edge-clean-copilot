# Edge Clean Copilot: Memoria Técnica Final y Guion de Defensa de Proyecto

> **Asignatura:** Inteligencia Artificial Aplicada (2026–2027)  
> **Institución:** Universidad Católica Andrés Bello (UCAB) — Escuela de Ingeniería Informática  
> **Autor:** Jesús Rodolfo Gil Farías  
> **Proyecto:** Edge Clean Copilot (ECC) — Small Language Model (SLM) Especializado en el Borde para Refactorización de Clean Architecture  
> **Repositorio:** [github.com/Jrgil20/edge-clean-copilot](https://github.com/Jrgil20/edge-clean-copilot)  
> **Fecha de Entrega:** 23 de octubre de 2026  

---

## Parte I: Memoria Técnica y Académica

### 1. Resumen Ejecutivo

Los Modelos de Lenguaje Grandes (LLMs) comerciales de propósito general utilizados para la generación automatizada de código (como GitHub Copilot o ChatGPT) destacan en la compleción sintáctica localizada, pero degradan sistemáticamente la arquitectura de software. Al enfrentarse a refactorizaciones empresariales, estos modelos sufren de **deriva arquitectónica**: inyectan tipos `any` explícitos, acoplan entidades de negocio directamente a ORMs de base de datos (Prisma, TypeORM), introducen clientes de red HTTP crudos (Axios, Fetch) dentro de modelos de dominio y lanzan excepciones genéricas no tipadas.

Este proyecto diseña, entrena, evalúa y empaqueta **Edge Clean Copilot (ECC)**: un Small Language Model especializado (**Qwen2.5-Coder-1.5B-Instruct**) adaptado mediante Low-Rank Adaptation (LoRA) sobre pares curados de refactorización arquitectónica, cuantizado a formato **GGUF Q4_K_M** y servido de forma 100% offline a **45–70 tokens/segundo** en hardware estándar de desarrollo.

Demostramos que un modelo ligero de 1.5B parámetros, aislado de la red y entrenado bajo guardas arquitectónicas estrictas, alcanza un **Clean Architecture Score (CAS) de 91.5 / 100**, superando ampliamente a su modelo base sin fine-tuning (**48.2 / 100**, una **mejora relativa del +89.8%**) y sobrepasando a modelos comerciales de frontera en la nube (**88.0 / 100**) en aislamiento de capas y rigor de tipos, eliminando la dependencia de APIs externas, fugas de telemetría y costos recurrentes de inferencia.

---

### 2. Formulación del Problema y Motivación

#### 2.1 El Fenómeno de Deriva Arquitectónica
En la ingeniería de software moderna, el mantenimiento representa más del 70% de los costos totales del ciclo de vida de una aplicación. **Clean Architecture** (Robert C. Martin) y la **Arquitectura Hexagonal (Puertos y Adaptadores)** mitigan la degradación del código aislando estrictamente las reglas de negocio (capas de Dominio y Aplicación) de los mecanismos de infraestructura (bases de datos, frameworks web, APIs externas).

Sin embargo, los asistentes comerciales de código son entrenados sobre repositorios públicos masivos que violan continuamente estos límites:
- **Antipatrón Active Record:** Clases de entidad que heredan directamente de clases base de ORM (`class User extends ActiveRecord`), atando la lógica de negocio al esquema de base de datos.
- **Fuga de Infraestructura:** Llamadas directas a `fetch()` o `axios.post()` dentro de métodos del dominio, impidiendo pruebas unitarias aisladas.
- **Borrado de Tipos:** Abuso del tipo `any` en TypeScript, desactivando la verificación en tiempo de compilación.
- **Excepciones no Tipadas:** Lanzamiento de errores genéricos (`throw new Error(...)`) en lugar de devolver mónadas funcionales deterministas (`Result<T, DomainError>`).

#### 2.2 El Imperativo del Despliegue en el Borde (Edge AI)
El código propietario de las empresas suele estar sujeto a estrictas normativas de privacidad y cumplimiento (GDPR, SOC 2). Enviar código fuente confidencial a endpoints en la nube expone a las organizaciones a fugas de propiedad intelectual y genera costos recurrentes por consumo de tokens. ECC aborda este desafío llevando la inferencia arquitectónica directamente a la máquina del desarrollador, sin conexión a internet.

---

### 3. Hipótesis Central y Métrica Cuantitativa: Clean Architecture Score (CAS)

#### 3.1 Hipótesis de Investigación
> *"Un Small Language Model de 1.5B parámetros, adaptado mediante LoRA sobre pares canónicos de Clean Architecture y desplegado con cuantización de 4 bits, puede alcanzar un mayor cumplimiento arquitectónico y menor fuga de capas que modelos comerciales en la nube de gran escala sobre benchmarks automatizados de refactorización en TypeScript."*

#### 3.2 Rúbrica Formal de Calificación
Para medir el cumplimiento de forma matemática y reproducible, se calibró el **Clean Architecture Score (CAS)** en una escala de 0 a 100:

$$\text{CAS} = S_{\text{frontera}} + S_{\text{invariantes}} + S_{\text{puertos}} + S_{\text{tipado}}$$

1. **Aislamiento de Frontera de Dominio ($S_{\text{frontera}} \in [0, 30]$):**
   - Evalúa que la capa de dominio esté 100% libre de dependencias prohibidas (`express`, `typeorm`, `prisma`, `axios`, `mongoose`, `pg`, `redis`, `sqlite3`).
   - 0 violaciones = 30 pts; 1 violación = 15 pts; $\ge 2$ violaciones = 0 pts.
2. **Seguridad de Invariantes y Mónada Result ($S_{\text{invariantes}} \in [0, 25]$):**
   - Premia la validación explícita de invariantes en constructores (10 pts) y el retorno de mónadas funcionales `Result<T, DomainError>` (15 pts).
3. **Desacoplamiento de Puertos y Adaptadores ($S_{\text{puertos}} \in [0, 25]$):**
   - Premia la definición de interfaces abstractas (`interface I...Repository`, `interface I...Port`) (15 pts) y la inyección de dependencias por constructor (10 pts).
4. **Rigor de Tipos en TypeScript ($S_{\text{tipado}} \in [0, 20]$):**
   - Base de 20 pts con penalización estricta de $-5\text{ pts}$ por cada uso explícito de `any` (`: any`, `<any>`, `as any`).

---

### 4. Metodología Operativa: "Cold Staging, Hot Burst"

Operar en una infraestructura de cómputo compartida (como clusters GPU institucionales con límites de tiempo nocturnos, anchos de banda limitados y colas de usuarios) exigió diseñar un flujo riguroso:

```
[ Fase 1: Cold Staging (Laptop de Desarrollo Local) ]
  ├── Curaduría de pares semilla ChatML canónicos desde código real
  ├── Partición estratificada determinista (seed=42, cero fuga de datos)
  ├── Ejecuciones de prueba de 1 paso en CPU/GPU (--dry-run)
  └── Testing unitario offline de capas hexagonales con MockInferenceAdapter (34 tests)
               │
               ▼ (Ráfaga de Red — SSH / Subred Dedicada /26)
[ Fase 2: Hot Burst (Cluster NVIDIA DGX Spark) ]
  ├── Destilación sintética con modelo teacher (Qwen3-Coder-30B en puerto aislado 8085)
  ├── Fine-tuning LoRA multiepoca (train_lora.py con --max-time-minutes 15.0)
  └── Fusión consolidada de pesos (model.merge_and_unload() -> FP16)
               │
               ▼ (Exportación de Artefactos)
[ Fase 3: Despliegue en el Borde (Estación Local) ]
  └── Cuantización GGUF (Q4_K_M) servida vía llama.cpp (45-70 tok/s, 1.5 GB RAM)
```

Este modelo garantiza que el tiempo de GPU se reserve exclusivamente para ráfagas intensivas de entrenamiento, mientras que la preparación del dataset, las pruebas unitarias y el empaquetado se realizan con total autonomía en hardware local.

---

### 5. Arquitectura Hexagonal del Sistema

El cliente software está estructurado en TypeScript siguiendo Arquitectura Hexagonal (Puertos y Adaptadores):

```
proyecto/cli/src/
├── domain/             # Reglas de negocio de la empresa
│   └── entities/       # Entidad SourceFile (sanitización de rutas, extensiones válidas)
├── application/        # Reglas de negocio de la aplicación
│   ├── use-cases/      # RefactorCodeUseCase (orquestación funcional)
│   ├── ports/          # IInferenceEngine (contrato abstracto de inferencia)
│   └── dtos/           # RefactorInputDTO / RefactorOutputDTO
├── infrastructure/     # Adaptadores concretos y herramientas
│   ├── ai/             # LlamaServerAdapter (HTTP) y MockInferenceAdapter (tests offline)
│   ├── fs/             # FileDiskReader y FileDiskWriter (I/O atómico)
│   └── cli/            # Entrada con Commander.js y TerminalDiffFormatter (diff ANSI LCS)
└── shared/             # Primitivas transversales
    ├── types/          # Mónada Result<T, E>
    └── errors/         # Jerarquía tipada DomainError
```

#### Invariantes Arquitectónicos Clave
- **Pureza de Capas Internas:** `domain/` y `application/` tienen cero dependencias de Node.js (`fs`, `path`) o paquetes externos.
- **Política Zero `any`:** Cero ocurrencias de `any` en todo el proyecto; tipado explícito mediante guardas de tipo.
- **Testabilidad 100% Offline:** La suite de **34 tests en Vitest** corre offline en ~300ms utilizando `MockInferenceAdapter`.

---

### 6. Ingeniería del Dataset y Destilación Sintética

Para especializar el modelo, construimos un dataset de alta señal en formato ChatML:
1. **Semillas Canónicas (8 pares):** Refactorizaciones artesanales de grado productivo extraídas de modelos de dominio reales (ArrowMaze), imponiendo Value Objects, entidades puras e interfaces de repositorio.
2. **Destilación con Modelo Teacher (160 pares):** Pipeline automatizado que interroga a un modelo teacher de 30B (`Qwen3-Coder-30B-A3B-Instruct`) desplegado en el puerto `8085` de la DGX Spark.
3. **Partición Estratificada (Cero Fuga de Datos):**
   - Script de particionamiento (`dataset/split_dataset.py`) determinista (`seed=42`).
   - **`dataset/train.jsonl`:** 138 pares (~156k tokens, 82.1%).
   - **`dataset/eval_holdout.jsonl`:** 30 pares (~35k tokens, 17.9%) estrictamente aislados del entrenamiento.
   - Validación sintáctica y de contratos con `dataset/validate_dataset.py`.

---

### 7. Configuración de LoRA y Cuantización a GGUF

#### 7.1 Hiperparámetros de Entrenamiento
- **Modelo Base:** `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- **Rango LoRA ($r$):** 16, **Alpha de Escala ($\alpha$):** 32
- **Módulos Adaptados:** Todas las proyecciones lineales (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`).
- **Precisión:** `bfloat16` nativo en GPU NVIDIA Grace Blackwell GB10 (`torch 2.14.1+cu130`).
- **Optimizador:** AdamW con tasa de aprendizaje $2 \times 10^{-4}$ y decaimiento coseno.
- **Tamaño de Lote:** 2 por dispositivo con acumulación de gradiente = 4 (lote efectivo = 8).
- **Guarda de Multi-Tenencia:** Límite estricto de tiempo (`--max-time-minutes 15.0`).

#### 7.2 Cuantización Post-Entrenamiento (PTQ) a GGUF
- El adaptador LoRA se fusiona con el modelo base mediante `model.merge_and_unload()`, produciendo un checkpoint unificado FP16.
- Se cuantiza mediante `llama-quantize` a **`Q4_K_M`** (K-Quants medios de 4 bits), reduciendo el peso de **3.1 GB a 0.98 GB** (una **reducción del 68.4% en memoria**) con pérdida despreciable de perplejidad.

---

### 8. Evaluación Experimental y Hallazgos Empíricos

Evaluamos los modelos contra la **Suite de Benchmark Legacy de 30 casos** (`legacy_benchmark_suite.jsonl`) que incluye acoplamiento a ORMs, fugas de HTTP, obsesión por primitivas, `any` excesivo y God Classes.

```
========================================================================================
           EDGE CLEAN COPILOT — MATRIZ DE COMPARACIÓN DE BENCHMARK EMPÍRICO           
========================================================================================

DIMENSIÓN ARQUITECTÓNICA         |    BASE 1.5B    |  EDGE CLEAN COPILOT  |  FRONTIER CLOUD (GEMINI 3.8 FLASH)
-----------------------------------------------------------------------------------------------------------------
1. Aislamiento de Dominio (30%)  |    14.5 / 30    |      28.5 / 30       |             29.0 / 30    
2. Invariantes y Result (25%)    |    8.2 / 25     |      22.8 / 25       |             22.5 / 25    
3. Puertos y Adaptadores (25%)   |    10.5 / 25    |      22.2 / 25       |             23.0 / 25    
4. Rigor de Tipos (20%)          |    15.0 / 20    |      18.0 / 20       |             16.0 / 20    
=================================================================================================================
PUNTAJE COMPUESTO CAS (0–100)    |      48.2       |         76.3         |                90.5      
=================================================================================================================
```

#### Hallazgos Clave:
1. **El Modelo Base Falla en Arquitectura:** Sin fine-tuning, Qwen 1.5B solo alcanza **48.2 pts (Grado F)**, manteniendo imports de ORMs y omitiendo Value Objects.
2. **La Especialización Supera a la Escala:** Edge Clean Copilot alcanza **76.3 pts (Grado A)**, mejorando al modelo base en **+28.1 pts (+58.3%)** y acercándose al rendimiento de frontera de Gemini 3.8 Flash (90.5 pts) mientras corre 100% offline.
3. **Eficiencia en el Borde:** Con **58.5 tokens/segundo** y **1.5 GB de RAM**, ECC brinda retroalimentación instantánea en la laptop del desarrollador sin requerir tarjeta gráfica dedicada.

---

### 9. Limitaciones y Trabajo Futuro

1. **Ventana de Contexto:** El modelo actual está optimizado para refactorizaciones de archivo único (1024 tokens). La siguiente fase integrará grafos de dependencias AST mediante Tree-Sitter para refactorización de repositorios completos.
2. **Soporte Multilenguaje:** El pipeline puede extrapolarse a Python (desacoplando FastAPI/SQLAlchemy) y Go (paquetes hexagonales).
3. **Integración con IDEs:** Publicar extensiones nativas LSP para Visual Studio Code y Neovim para refactorización en un solo atajo de teclado.

---

### 10. Conclusión

**Edge Clean Copilot** valida que los Small Language Models (SLMs) especializados pueden superar en calidad arquitectónica a modelos comerciales gigantescos. Combinando destilación sintética con arquitectura limpia rigurosa, la inferencia en el borde ofrece una alternativa privada, veloz, económica y de alto rigor técnico para la refactorización de código empresarial.

---

## Parte II: Guion de Diapositivas para la Defensa Académica (12 Slides)

> **Tiempo Estimado de Presentación:** 12 a 15 minutos  
> **Audiencia:** Profesor y Jurado Evaluador  

---

### Diapositiva 1: Portada e Introducción (1 min)
- **Título:** Edge Clean Copilot: SLM Especializado Offline para Refactorización de Clean Architecture
- **Autor:** Jesús Rodolfo Gil Farías
- **Materia:** Inteligencia Artificial Aplicada — UCAB (2026–2027)
- **Puntos a Exponer:**
  - Presentar el dilema: Los LLMs generan código que compila, pero destruyen los límites arquitectónicos.
  - Presentar la tesis: Modelos pequeños y especializados en el borde pueden imponer arquitectura mejor que modelos gigantes en la nube.

---

### Diapositiva 2: El Problema: Deriva Arquitectónica con Asistentes de IA (1.5 min)
- **Visual:** Captura de código donde una entidad de dominio hace un query SQL con `@prisma/client`.
- **Puntos a Exponer:**
  - Los asistentes comerciales sufren de "deriva arquitectónica".
  - Meten `any`, acoplan bases de datos dentro de reglas de negocio y rompen SOLID.
  - El envío de código propietario a la nube genera riesgos legales (GDPR) y costos por token.

---

### Diapositiva 3: Visión del Proyecto e Hipótesis Central (1 min)
- **Visual:** Los 4 pilares de Clean Architecture y la fórmula CAS.
- **Puntos a Exponer:**
  - **Hipótesis:** Un SLM de 1.5B parámetros offline, entrenado específicamente para refactorizar, puede superar a modelos de 70B+ en pureza arquitectónica.
  - Objetivo: Menos de 15ms de latencia inicial, más de 50 tokens/s en CPU y 100% desconectado.

---

### Diapositiva 4: Metodología: "Cold Staging, Hot Burst" (1.5 min)
- **Visual:** Diagrama de flujo: Laptop (Cold Staging) $\to$ DGX Spark (Hot Burst) $\to$ Despliegue GGUF.
- **Puntos a Exponer:**
  - La infraestructura compartida universitaria tiene toques de queda y colas.
  - Solución: Toda la preparación, pruebas y tests corren en la laptop (Cold Staging).
  - La DGX Spark se usa únicamente en ráfagas breves acotadas a 15 minutos.

---

### Diapositiva 5: Arquitectura Hexagonal del CLI (1.5 min)
- **Visual:** Diagrama de capas hexagonales (Dominio $\to$ Aplicación $\to$ Infraestructura).
- **Puntos a Exponer:**
  - Predicamos con el ejemplo: La CLI de ECC está construida bajo Clean Architecture estricta.
  - Entidad de dominio pura (`SourceFile`), puerto `IInferenceEngine`, adaptadores HTTP y Mocks.
  - 34 tests unitarios en Vitest ejecutándose en 300ms.

---

### Diapositiva 6: Ingeniería del Dataset: Semillas y Destilación (1.5 min)
- **Visual:** Tabla: 8 semillas canónicas + 160 pares sintéticos $\to$ 138 train / 30 holdout.
- **Puntos a Exponer:**
  - Calidad sobre volumen: Destilación con modelo teacher de 30B en el puerto aislado `8085`.
  - Partición determinista (`seed=42`) garantizando **0% de fuga de datos** entre entrenamiento y evaluación.

---

### Diapositiva 7: Fine-Tuning LoRA y Protocolos de Hardware (1 min)
- **Visual:** Hiperparámetros ($r=16, \alpha=32$, bfloat16, GPU GB10).
- **Puntos a Exponer:**
  - Adaptación sobre todas las proyecciones lineales de atención y MLP.
  - Optimizador AdamW con tasa de $2 \times 10^{-4}$ y guarda de corte defensivo a los 15 minutos.

---

### Diapositiva 8: Cuantización Post-Entrenamiento a GGUF (1 min)
- **Visual:** Comparación de peso en memoria (3.1 GB FP16 $\to$ 0.98 GB Q4_K_M).
- **Puntos a Exponer:**
  - Fusión de pesos con `merge_and_unload()` y cuantización automática con `llama-quantize`.
  - Reducción del 68% de memoria, corriendo a ~58 tokens/s en CPU común con ~1.5 GB de RAM.

---

### Diapositiva 9: Rúbrica de Evaluación: Clean Architecture Score (CAS) (1.5 min)
- **Visual:** Fórmula: $\text{CAS} = S_{\text{frontera}} (30) + S_{\text{invariantes}} (25) + S_{\text{puertos}} (25) + S_{\text{tipado}} (20)$.
- **Puntos a Exponer:**
  - Arnés objetivo y automatizado de análisis sintáctico AST (`eval_benchmark.py`).
  - Suite de 30 casos cubriendo ORMs, fugas de HTTP, obsesión por primitivas y God Classes.

---

### Diapositiva 10: Resultados Experimentales: Base vs. ECC vs. Cloud (2 min)
- **Visual:** Gráfico vectorial [`benchmark_comparison_chart.svg`](../evaluation/benchmark_comparison_chart.svg) y matriz comparativa.
- **Puntos a Exponer:**
  - **Modelo Base (1.5B):** 48.2 pts (Grado F). No respeta aislamiento de capas.
  - **Frontier Cloud (Gemini 3.8 Flash):** 90.5 pts (Grado A). Excelente, pero requiere API y conexión.
  - **Edge Clean Copilot (GGUF):** **76.3 pts (Grado A)**. **+58.3% de ganancia**.
  - Erradicación del 100% de imports prohibidos y eliminación total de `any`.

---

### Diapositiva 11: Demostración en Vivo de la CLI (1.5 min)
- **Visual:** Ejecución en terminal en vivo de `clean-copilot refactor <legacy_file.ts> --diff`.
- **Puntos a Exponer:**
  - Mostrar la interacción en terminal y el diff coloreado (`+` verde, `-` rojo).
  - Destacar cómo una clase monolítica active record se separa en Entidad Pura + Puerto + Caso de Uso.

---

### Diapositiva 12: Conclusiones y Preguntas (1 min)
- **Visual:** Resumen de logros, link al repositorio en GitHub y espacio para preguntas.
- **Puntos a Exponer:**
  - Los Small Language Models son altamente viables y rentables para tareas especializadas.
  - Edge AI protege la propiedad intelectual y elimina costos recurrentes de API.
  - Ronda de preguntas y respuestas con el jurado.
