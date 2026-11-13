# Próximos pasos

ECC es una prueba de concepto. El modelo publicado (`clean-copilot-1.5b-q4_k_m.gguf`, SHA-256 `d2deae6542d1…`) ya está entrenado y puede que no se vuelva a entrenar. Los puntos están ordenados por importancia; **el dataset va primero** porque limita todo lo demás, incluido cualquier reentrenamiento futuro.

Cifras medidas el 2026-11-13 salvo que se indique otra cosa. Auditoría relacionada: [docs/evaluation-audit-2026-11-05.md](./evaluation-audit-2026-11-05.md).

🌐 **[English version →](../../docs/next-steps.md)**

---

## 1. Dataset (prioridad)

### 1.1 Muy pocas tareas distintas

| Partición | Filas | Prompts distintos |
| :--- | ---: | ---: |
| Usada para entrenar el modelo publicado (commit `64f3c6c`) | 138 train / 30 holdout | **18** en train |
| Partición actual (`split_dataset.py`, aún sin entrenar) | 91 train / 34 holdout | 36 en total, 28 en train |

Las 160 filas generadas por el maestro salen de un conjunto pequeño de plantillas de prompt muestreadas varias veces. Los prompts más repetidos de entrenamiento aparecen 13–14 veces cada uno (`python3 dataset/audit_dataset.py`). Con un loss final de entrenamiento de 0.031, lo más probable es que el modelo haya aprendido esas plantillas y no una habilidad general de refactorización.

**Siguiente:**
- Aumentar el número de tareas *distintas*, no de filas. Objetivo: al menos 150–200 prompts distintos antes de cualquier reentrenamiento. Una respuesta por prompt es mejor que muchas respuestas muestreadas al mismo prompt.
- Variar el código de entrada: distintos dominios (facturación, inventario, autenticación, agenda), tamaños, estilos de código, y JavaScript además de TypeScript.
- Añadir a `audit_dataset.py` una detección de duplicados y casi-duplicados que compare el código dentro de los prompts, no solo el texto del prompt.
- Hacer de `audit_dataset.py --strict` una comprobación obligatoria antes de cualquier entrenamiento.

### 1.2 Desbalance de categorías

Distribución actual en train + holdout (`classify_sample` en `split_dataset.py`):

| Categoría | Filas | Objetivo en `dataset/README.md` |
| :--- | ---: | ---: |
| Entidad / value object | 43 | — |
| Puerto / adaptador | 34 | — |
| Test AAA | 28 | 20% |
| `ARCH_REFACTOR` | 10 | **40%** |
| `SOLID_CRITIQUE` | 10 | 10% |

`ARCH_REFACTOR` (código desordenado → código por capas) es la tarea que realmente hace el CLI, y es la categoría más escasa. Sus 10 ejemplos están escritos a mano y se añadieron después de entrenar el modelo.

**Siguiente:** escribir o generar más pares `ARCH_REFACTOR` primero, partiendo de código acoplado realista (handlers de Express con SQL, componentes React que llaman APIs, servicios que importan ORMs).

### 1.3 Las respuestas no se verifican

Las respuestas del maestro solo se comprueban por estructura ChatML y por bloques de código bien cerrados. Nada comprueba que la respuesta compile ni que conserve el comportamiento de la entrada.

**Siguiente:**
- Ejecutar `tsc --noEmit` sobre cada bloque de código de cada respuesta del asistente, y descartar o corregir las que fallen.
- Para `ARCH_REFACTOR`, guardar un test ejecutable pequeño con el código original y comprobar que la versión refactorizada lo pasa.
- Puntuar cada respuesta de entrenamiento con CAS y descartar las de puntuación baja, para no entrenar el modelo con ejemplos que el propio benchmark penalizaría.

### 1.4 Los datos de entrenamiento publicados no están en el árbol de trabajo

Los `train.jsonl` / `eval_holdout.jsonl` del repo son la partición nueva. Los datos con los que se entrenó el modelo publicado solo existen en el historial de git (`git show 64f3c6c:dataset/train.jsonl`).

**Siguiente:** guardarlos como `dataset/published_model_train.jsonl` (o registrar el commit en `MODEL_CARD.md`) para que los datos de entrenamiento del modelo sean fáciles de encontrar.

### 1.5 El holdout estaba contaminado

El holdout usado con el modelo publicado compartía 28 de 30 prompts con el entrenamiento. No sirve como evidencia sobre ese modelo. La partición actual lo corrige (0/34 de solapamiento), pero todavía no se ha usado.

---

## 2. Evaluación

### 2.1 CAS mide forma, no corrección

CAS busca patrones (`interface I…Repository`, `Result.ok`, ausencia de `any` y de imports de frameworks). Un modelo puede cumplirlos sin producir un refactor correcto, y las respuestas de entrenamiento contienen esos mismos patrones.

**Siguiente:**
- Añadir a `eval_benchmark.py` una comprobación de compilación: envolver cada salida y ejecutar `tsc --noEmit`, y reportar la tasa de compilación junto al CAS.
- Añadir comprobaciones de comportamiento en un subconjunto de casos (código de entrada + tests que deben seguir pasando tras el refactor).
- Leer y calificar a mano una muestra de respuestas. `RESULT.md` ya pide 5 por modelo, y esto no se ha registrado.

### 2.2 Una salida vacía saca 50

Una respuesta vacía o un rechazo gana 50/100 (30 de frontera + 20 de tipado). Los reportes lo marcan, pero la escala sigue siendo engañosa.

**Siguiente:** dar cero a las salidas sin código, o reportar siempre el CAS junto con el piso de 50 puntos.

### 2.3 Faltan líneas base

La mejora de +16.8 es frente al modelo base con el mismo system prompt. No se sabe cuánto de esa mejora se lograría solo con un mejor prompt.

**Siguiente:** ejecutar la misma suite contra:
1. El modelo base con un prompt few-shot (2–3 ejemplos del dataset).
2. El maestro de 30B (Qwen3-Coder-30B), que muestra el techo del que aprende el modelo pequeño.
3. Opcionalmente, un modelo frontera.

### 2.4 Una sola suite, pequeña y escrita por el autor

Los 30 casos los escribió el mismo autor, en el mismo estilo que los datos de entrenamiento.

**Siguiente:** añadir casos de fuera del proyecto (código open source con problemas de acoplamiento reales) y reportar resultados por categoría.

### 2.5 Ruido

Dos ejecuciones del mismo GGUF dieron 72.5 y 76.3, con una diferencia media por caso de 17.8 puntos.

**Siguiente:** ejecutar cada modelo 3–5 veces (o con temperatura 0) y reportar la media y la dispersión.

---

## 3. Entrenamiento (solo si se reentrena)

- Añadir loss de validación usando el holdout actual, disjunto por prompt, y parar antes cuando deje de mejorar.
- Con 18 prompts distintos, 3 épocas llegaron a un loss de 0.031. Con un dataset más grande, empezar con 1–2 épocas y comparar checkpoints en el benchmark.
- Reentrenar solo después de completar §1.1–§1.3; reentrenar con los datos actuales mayormente volvería a aprender las mismas plantillas.

---

## 4. Coherencia de la documentación

- `MODEL_CARD.md` cita una puntuación frontera de **90.5**. La auditoría (F3, F8) no encontró ninguna ejecución registrada que la respalde. Quitar la cifra o marcarla como no medida.
- `MODEL_CARD.md` dice que el modelo "erradica el 100%" de los imports prohibidos. Eso solo se cumple en la suite de 30 casos; decirlo explícitamente.
- `docs/progress-and-milestones.md` y `docs/final-report-and-presentation.md` todavía hablan de "100% completado". Alinearlos con el enfoque de prueba de concepto del README.
- `status.py` imprime estados fijos en el código (por ejemplo "DGX Spark Status: Offline (Curfew)"). Calcularlos o eliminarlos.
- Mantener el espejo `es/` sincronizado con cada cambio anterior.
