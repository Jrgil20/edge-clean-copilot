# Especificación del Dataset — Edge Clean Copilot

## 1. Objetivo
Curar pares sintéticos canónicos de alta calidad en Clean Architecture y Spec-Driven Development para el fine-tuning de Small Language Models (SLMs: Qwen-2.5-Coder-1.5B/3B) mediante LoRA.

---

## 2. Formato Objetivo: OpenAI / ChatML
Para garantizar compatibilidad nativa con Hugging Face `trl` (`SFTTrainer`) y el template de chat de Qwen, todas las muestras siguen el estándar ChatML en formato JSONL:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are Edge Clean Copilot, an expert software architect specialized in Clean Architecture, Domain-Driven Design (DDD), and SOLID principles. You strictly enforce the Dependency Rule: domain and application layers must never depend on external libraries, frameworks, databases, or infrastructure."
    },
    {
      "role": "user",
      "content": "<Instrucción de la tarea + contexto o código acoplado>"
    },
    {
      "role": "assistant",
      "content": "<Solución canónica en Clean Architecture con clara separación de capas>"
    }
  ]
}
```

---

## 3. Taxonomía del Dataset (Distribución Objetivo)

| ID Categoría | Nombre de Categoría | Descripción | % Objetivo |
| :--- | :--- | :--- | :--- |
| `ARCH_REFACTOR` | Refactorización Acoplada a Limpia | Toma código mezclado (e.g. Express + SQL crudo) y lo descompone en Dominio, Aplicación, Puerto y Adaptador. | 40% |
| `USE_CASE_GEN` | Implementación de Casos de Uso y Dominio | Genera Entidades de Dominio, Value Objects y Casos de Uso con DTOs y `Result<T, E>`. | 30% |
| `AAA_TEST_GEN` | Pruebas Unitarias Aisladas | Genera tests Arrange-Act-Assert para Casos de Uso usando dobles de prueba puros en memoria (fakes/mocks). | 20% |
| `SOLID_CRITIQUE` | Lint y Crítica de Arquitectura | Analiza código, detecta violaciones de Clean Architecture (Inversión de Dependencias, fugas de capas) y propone fixes. | 10% |

---

## 4. Reglas de Calidad para Cada Muestra
1. **Cero Contaminación de Dominio:** Entidades y casos de uso no importan ORMs (Prisma, Mongoose, TypeORM), frameworks HTTP (Express, Nest, FastAPI) ni SDKs externos.
2. **Contratos Explícitos:** Toda dependencia de infraestructura se invierte mediante una interfaz (Puerto) definida en Aplicación o Dominio.
3. **Manejo de Errores Determinista:** Las capas internas retornan tipos funcionales `Result<T, E>` o errores de dominio tipados, evitando excepciones no controladas.

---

## 5. Partición Estratificada y Prevención de Data Leakage

Para garantizar rigor académico y metodológico, las 168 muestras unificadas (`seed_examples.jsonl` + `generated_examples.jsonl`) se dividen en dos conjuntos mutuamente excluyentes usando [`split_dataset.py`](../../dataset/split_dataset.py) con semilla determinista (`seed=42`):

> **Nota (2026-11-08):** las cifras siguientes describen el dataset con el que se entrenó el modelo publicado. `split_dataset.py` ahora divide por prompt normalizado y descarta respuestas con fences de código sin cerrar, y, desde el 2026-11-13, también descarta las respuestas con `any` explícito o que no pasan un chequeo de tipos aislado con `tsc`, por lo que al ejecutarlo resultan 82 muestras (67 train / 15 holdout, 32 prompts distintos). El holdout toma primero los grupos de prompts más pequeños y tiene un tope de 15 filas, para no vaciar ninguna categoría. `ARCH_REFACTOR` y `SOLID_CRITIQUE` se reconstruyeron con 19 ejemplos escritos a mano (10 por categoría tras el split) en `authored_examples.jsonl`; siguen siendo pocos, así que generá más con `generate_with_teacher.py` antes de reentrenar.
>
> **Actualización (2026-11-13):** `claude_authored_examples.jsonl` añade un piloto de 20 ejemplos `ARCH_REFACTOR` escritos por Claude (Opus 5.5) en una sesión de Claude Code, cada uno una tarea distinta (código de Express, NestJS, Fastify, Next.js, Hono, React, Angular, Redux, Kafka, SQS, BullMQ, cron, Socket.IO, GraphQL y CLI; dos entradas son JavaScript plano). Usan el system prompt del CLI y `Result<T, E>` con errores tipados, y todos pasan la auditoría. Se guardan en su propio archivo para conservar la procedencia y están pendientes de revisión manual. Un segundo lote de 20 añade más variedad: 10 filas usan el prompt de refactorización exacto del CLI con archivos completos como entrada, algunas entradas son pequeñas y reciben respuestas cortas, una modela los errores como subclases de `DomainError`, y una entrada ya está bien separada en capas y solo necesita un arreglo mínimo. `classify_sample` ahora ignora los bloques de código y la frase "Ports & Adapters", para que estas filas cuenten como `ARCH_REFACTOR`. Con las 40 filas, el split da 123 muestras (108 train / 15 holdout, 73 prompts distintos, 49 `ARCH_REFACTOR`).


```text
======================================================================
168 Muestras Canónicas Unificadas (~191.364 Tokens Totales)
  ├── train.jsonl         : 138 muestras (82.1%) — ~156.395 tokens
  └── eval_holdout.jsonl  :  30 muestras (17.9%) —  ~34.969 tokens
======================================================================
```

| Categoría Arquitectónica | Muestras Totales | Conjunto de Entrenamiento (`train.jsonl`) | Conjunto de Evaluación Ciega (`eval_holdout.jsonl`) |
| :--- | :--- | :--- | :--- |
| **Puertos y Adaptadores** | 68 | 56 | 12 |
| **Entidades y Value Objects** | 46 | 38 | 8 |
| **Pruebas Unitarias AAA** | 30 | 25 | 5 |
| **Crítica SOLID / Lint** | 13 | 11 | 2 |
| **Refactorización de Arquitectura** | 11 | 9 | 2 |
| **TOTAL** | **168** | **138** | **30** |

> [!IMPORTANT]
> El conjunto `eval_holdout.jsonl` generado por el `split_dataset.py` actual se divide por prompt: ningún prompt aparece a la vez en `train.jsonl` y en el holdout (verificable con `python3 audit_dataset.py`). El modelo publicado, en cambio, se entrenó con la división anterior, donde 28/30 prompts del holdout también estaban en `train.jsonl`; por eso la suite legacy disjunta de `evaluation/` es la evaluación real de ese modelo. Se reserva de forma exclusiva para el benchmark posterior al entrenamiento en [`evaluation/`](../../evaluation/).
