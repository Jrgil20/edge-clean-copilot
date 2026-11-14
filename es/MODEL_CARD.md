# Edge Clean Copilot (1.5B Q4_K_M GGUF)

> Espejo en español de [`MODEL_CARD.md`](../MODEL_CARD.md). La versión en inglés es la que se publica en Hugging Face.

**Edge Clean Copilot** es un modelo de lenguaje pequeño (SLM) especializado y sin conexión a la red, diseñado para refactorizar código hacia Clean Architecture y arquitectura hexagonal directamente en el hardware del desarrollador (CPU/portátil), sin telemetría en la nube y sin costos recurrentes de API.

Se ajustó a partir de `Qwen/Qwen2.5-Coder-1.5B-Instruct` con fine-tuning eficiente en parámetros (LoRA) y se cuantizó a GGUF de 4 bits (`Q4_K_M`).

---

## Uso previsto y límites

- **Propósito:** un asistente de refactorización muy liviano y privado para artefactos TypeScript pequeños y acotados (entidades, servicios o clases individuales) que no deben salir de la máquina.
- **No está optimizado para velocidad:** ~12 tokens/s medidos en un portátil solo con CPU (Intel Core i5-10310U, 15 GB de RAM). Las entradas largas serán lentas.
- **No reemplaza a un modelo de frontera:** 74.8 / 100 en nuestro benchmark; no se midió ningún modelo de frontera en él. Revise cada salida antes de usarla.

---

## Características principales

- **100% sin conexión:** el código no sale de la máquina. Se ejecuta completamente en la RAM local (~1.5 GB).
- **Pureza del dominio:** en la suite legacy de 30 casos, todas las salidas obtuvieron el puntaje completo de 30/30 en aislamiento de la frontera de dominio: ningún import prohibido de frameworks o bases de datos (`express`, `mongoose`, `axios`, `typeorm`, `prisma`) en la capa de dominio. En parte se debe a omisión: solo 4 de 30 respuestas contienen algún import (auditoría E4 en `docs/project/project-analysis.md`).
- **Desacoplamiento con puertos y adaptadores:** genera interfaces abstractas (`IRepository`, `IPort`, `IGateway`) con inyección de dependencias por constructor.
- **Rigor de tipos en TypeScript:** evita el `any` explícito: 28 de 30 salidas del benchmark no tuvieron penalización por `any` (rigor de tipos 19.7 / 20).
- **Ganancia medida:** obtiene **74.8 / 100 en el Clean Architecture Score (CAS)**, grado B, en nuestro benchmark de 30 casos de refactorización legacy (+16.8 puntos sobre el modelo base, que obtiene 58.0).

---

## Resultados del benchmark (Clean Architecture Score — CAS 0–100)

Evaluado con la **suite legacy de 30 casos** (`legacy_benchmark_suite.jsonl`) mediante un analizador sintáctico AST automático:

| Dimensión arquitectónica | Máximo | Modelo base (Qwen 1.5B Q4_K_M) | **Edge Clean Copilot (Q4_K_M)** |
| :--- | :---: | :---: | :---: |
| **Aislamiento de la frontera de dominio** | 30 pts | 24.0 pts | **30.0 pts** |
| **Invariantes y patrón Result** | 25 pts | 0.3 pts | **2.7 pts** |
| **Desacoplamiento con puertos y adaptadores** | 25 pts | 15.8 pts | **22.5 pts** |
| **Rigor de tipos TypeScript (cero `any`)** | 20 pts | 17.8 pts | **19.7 pts** |
| **CAS COMPUESTO TOTAL** | **100 pts** | **58.0 pts** | **74.8 pts (grado B)** |

Medido en una corrida reproducible cara a cara en el NVIDIA DGX Spark, con la misma cuantización (Q4_K_M) y el analizador AST del compilador de TypeScript (ver el reporte `evaluation/reports/spark-20261105T143540Z`).

### Métricas operativas en el borde

| Métrica | **Edge Clean Copilot (Q4_K_M)** |
| :--- | :--- |
| **Velocidad de inferencia** | **~12 tok/s medidos** (solo CPU, Intel i5-10310U); una respuesta típica de refactorización (1100–1300 tokens) tarda entre 1.5 y 2 minutos |
| **Uso de RAM** | ~1.5 GB |
| **Tamaño en disco** | 941 MB (0.94 GB) |
| **Operación sin conexión** | 100% sin conexión |
| **Costo de API** | $0.00 |

El modelo base y las APIs en la nube no se midieron en este hardware.

---

## Inicio rápido y uso

### 1. Ejecutar con `llama.cpp` / `llama-server`

Descargue el archivo binario `clean-copilot-1.5b-q4_k_m.gguf`:

```bash
# Inicia un servidor de inferencia local compatible con OpenAI
llama-server \
  -m clean-copilot-1.5b-q4_k_m.gguf \
  --host 127.0.0.1 \
  --port 8085 \
  -c 2048
```

### 2. Ejecutar con Ollama

Cree un `Modelfile`:

```dockerfile
FROM ./clean-copilot-1.5b-q4_k_m.gguf

TEMPLATE """<|im_start|>system
{{ .System }}<|im_end|>
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""

PARAMETER temperature 0.1
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
```

Construya y ejecute:
```bash
ollama create clean-copilot -f Modelfile
ollama run clean-copilot
```

### 3. Ejecutar con Python (`llama-cpp-python`)

```python
from llama_cpp import Llama

llm = Llama(
    model_path="clean-copilot-1.5b-q4_k_m.gguf",
    n_ctx=2048,
    n_threads=6,
    verbose=False
)

system_prompt = (
    "You are an expert Clean Architecture assistant. Refactor legacy TypeScript/JavaScript "
    "code strictly adhering to Clean Architecture principles: isolate domain entities, "
    "define port interfaces, inject dependencies, and eliminate all `any` types."
)

user_code = """
import express from 'express';
import mongoose from 'mongoose';

export class UserService {
  async getUser(req: any) {
    return await mongoose.model('User').findById(req.params.id);
  }
}
"""

response = llm.create_chat_completion(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Refactor this code to Clean Architecture:\n\n{user_code}"}
    ],
    temperature=0.1,
    max_tokens=1024
)

print(response["choices"][0]["message"]["content"])
```

El modelo se entrenó con prompts en inglés; por eso el ejemplo los mantiene en inglés.

---

## Detalles del entrenamiento

- **Modelo base:** `Qwen/Qwen2.5-Coder-1.5B-Instruct`
- **Metodología:** LoRA (fine-tuning eficiente en parámetros) con PyTorch y `peft` de Hugging Face
- **Hardware:** NVIDIA DGX Spark (Grace Blackwell GB10)
- **Módulos objetivo:** `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
- **Hiperparámetros:**
  - Rango LoRA ($r$): 16
  - Alfa LoRA ($\alpha$): 32
  - Dropout: 0.05
  - Tasa de aprendizaje: 2e-4
  - Optimizador: AdamW (`bfloat16`), tasa de aprendizaje constante (sin warmup ni decaimiento), sin semilla fija
  - Épocas: 3 (batch por dispositivo 1, acumulación de gradiente 4, batch efectivo 4; unos 105 pasos de optimización)
  - Reproducirlo requiere los datos del commit `64f3c6c` y el código de entrenamiento del commit `fb3e812`; el `train_lora.py` actual entrena un modelo distinto (auditoría T1 y T3 en `docs/project/project-analysis.md`)
- **Dataset:** 138 pares de instrucciones ChatML curados que imponen fronteras de dominio estrictas, Value Objects con validación de invariantes, contratos de puertos y adaptadores, y manejo funcional de errores con `Result<T, E>`. Los archivos exactos de entrenamiento y holdout son `dataset/published_model_train.jsonl` y `dataset/published_model_holdout.jsonl` (del commit `64f3c6c`; 18 prompts de entrenamiento distintos, y 28 de los 30 prompts del holdout también aparecen en el entrenamiento; ver `docs/next-steps.md` 1.1 y 1.5).
- **Cuantización:** pesos consolidados de 16 bits exportados a GGUF con el cuantizador de `llama.cpp` (`Q4_K_M`, 4 bits de precisión media).

---

## Reglas arquitectónicas que impone

1. **Regla de la frontera de dominio:** las entidades y los value objects del núcleo nunca dependen de capas externas, frameworks ni ORMs de bases de datos.
2. **Tipado determinista:** prohibición estricta del `any` de TypeScript. Todos los contratos usan tipos acotados, interfaces explícitas o `unknown` con guardas de tipo.
3. **Puertos y adaptadores (hexagonal):** los casos de uso se comunican con el almacenamiento, las APIs y la mensajería únicamente mediante interfaces.
4. **Manejo funcional de errores:** se prefiere `Result<T, DomainError>` sobre las excepciones no controladas en tiempo de ejecución.

---

## Cita y repositorio

Repositorio del proyecto: [https://github.com/Jrgil20/edge-clean-copilot](https://github.com/Jrgil20/edge-clean-copilot)  
Proyecto semestral de Inteligencia Artificial Aplicada (UCAB).
