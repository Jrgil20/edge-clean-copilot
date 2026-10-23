# Registro de Recetas de Modelos

> **Especificación Autorizada:** Registro de Configuración de Modelos para Edge Clean Copilot

Este directorio contiene recetas declarativas de configuración (`.yaml` o `.json`) que definen la identidad del modelo fundacional, los módulos objetivo de LoRA, los delimitadores de respuesta para tokenización, la precisión numérica y los hiperparámetros de entrenamiento.

---

## 1. Estructura del Directorio

```
training/recipes/
├── schema.py                   # Dataclass ModelRecipe y cargador agnóstico
├── qwen2.5-coder-1.5b.yaml     # Modelo base 1.5B (Canónico)
├── llama-3.2-3b.yaml           # Modelo Llama 3.2 3B
├── gemma-2-2b.yaml             # Modelo Google Gemma 2 2B
└── README.md                   # Esta especificación
```

---

## 2. Campos del Esquema de Recetas

| Campo | Tipo | Descripción |
|---|---|---|
| `model_id` | `str` | Identificador del modelo en Hugging Face (e.g. `Qwen/Qwen2.5-Coder-1.5B-Instruct`). |
| `architecture_family` | `str` | Familia arquitectónica (`qwen2`, `llama3`, `gemma2`, `deepseek`). |
| `target_modules` | `list[str]` | Nombres exactos de las capas lineales donde aplicar adaptadores LoRA. |
| `response_template` | `str` | Delimitador que precede a la respuesta del asistente para enmascaramiento de pérdida. |
| `torch_dtype` | `str` | Tipo de dato del tensor (`bfloat16`, `float16`, `float32`). |
| `r` / `lora_alpha` | `int` | Rango LoRA y factor de escala alfa. |
| `recommended_quant` | `str` | Formato de cuantización GGUF recomendado (`Q4_K_M`, `Q8_0`). |

---

## 3. Cómo Registrar un Nuevo Modelo

1. Crear un archivo YAML en `training/recipes/<nombre-modelo>.yaml`.
2. Verificar los nombres de las proyecciones lineales del modelo (`q_proj`, `k_proj`, etc.).
3. Identificar el delimitador de cabecera del asistente para `response_template`.
4. Ejecutar la verificación con dry-run:
   ```bash
   python3 proyecto/training/train_lora.py --recipe proyecto/training/recipes/<nombre-modelo>.yaml --dry-run
   ```
