# Análisis del Proyecto: Edge Clean Copilot

> **Fecha:** 2026-11-13
> **Propósito:** un relato completo y verificable del proyecto para citarlo como antecedente (trabajo previo) de una tesis posterior. Este proyecto no es la tesis en sí. El documento cubre sus objetivos, sus ideas, qué funcionó, qué no y qué afirmaciones sostiene la evidencia.
> **Método:** cada cifra de este documento se volvió a medir desde el repositorio en esta fecha: se ejecutaron las suites de tests, se contaron los archivos del dataset, se recuperaron del historial de git la partición y el código de entrenamiento del modelo publicado, y se reanalizaron las salidas del benchmark ya commiteadas (estadística pareada y chequeo de tipos aislado). Los scripts se ejecutaron en local. No se consultó ningún modelo.
> **Relacionado:** [auditoría de evaluación (2026-11-05)](../evaluation/evaluation-audit-2026-11-05.md), [próximos pasos](../next-steps.md), [casos de uso válidos](../usage/use-cases.md).

---

## 1. Resumen

Edge Clean Copilot (ECC) es un fine-tune LoRA de `Qwen2.5-Coder-1.5B-Instruct`. Se fusiona, se cuantiza a GGUF Q4_K_M (941 MB) y se sirve offline con `llama.cpp`. Lo maneja un CLI hexagonal en TypeScript.

La propuesta trata sobre todo de un **proceso**: cómo especializar, empaquetar y evaluar un modelo pequeño con hardware limitado y compartido. El modelo es un producto de ese proceso.

**Lo que la evidencia sostiene:**

- El pipeline completo funciona de punta a punta: datos generados por un modelo maestro, entrenamiento LoRA en una GPU compartida, fusión, exportación GGUF, servicio local, un CLI y un benchmark atribuido.
- En la suite propia de 30 casos, el fine-tune supera a su modelo base por **+16.8 puntos CAS** (74.8 frente a 58.0). El intervalo de confianza bootstrap al 95% es [10.0, 25.2]. El fine-tune gana 24 casos, empata 6 y no pierde ninguno.

**Lo que la evidencia no sostiene:**

- La hipótesis de la propuesta de que el modelo puede superar a modelos comerciales o frontera. Nunca se evaluó ninguno con la suite.
- Que la salida sea código correcto. La métrica revisa patrones, no compilación ni comportamiento.
- Que sea rápido en un portátil. Se midieron unos 12 tok/s, alrededor de 47 s por respuesta.
- Que el resultado se generalice más allá de fragmentos cortos y sintéticos. Las entradas de la suite tienen 3–18 líneas.

**Dónde está la debilidad principal:** en los datos de entrenamiento. El modelo publicado aprendió de **18 prompts distintos** (138 filas). El 35% de las respuestas de entrenamiento está truncado y el 15% contiene `any` explícito. Solo 4 prompts distintos piden refactorizar código dado, que es justo la tarea que mide el benchmark.

**Conclusión:** en lo que respecta al proceso, el proyecto se sostiene bien: cada etapa existe, está automatizada con scripts y se ejecutó (§3.5). Es una **prueba de concepto y un pipeline de ingeniería** creíbles, no evidencia de que un modelo pequeño rivalice con los grandes. Con ese enfoque es un antecedente sólido para citar, y sus limitaciones definen trabajo futuro concreto.

---

## 2. Objetivos: planificado frente a logrado

Los objetivos planificados vienen de [propuesta.md](./propuesta.md) y del cronograma de su §4.

| # | Objetivo (según la propuesta) | Estado | Evidencia |
| :-- | :-- | :-- | :-- |
| O1 | Ajustar un SLM (1.5B–3B) con LoRA sobre pares de Clean Architecture | **Hecho para 1.5B.** El 3B no se entrenó. | `training/train_lora.py`; loss final 0.031 (bitácora de progreso). |
| O2 | Exportar GGUF Q4_K_M (y Q5_K_M, Q8_0) | **Hecho.** Q5 y Q8 se exportaron pero nunca se evaluaron. | Q4_K_M de 941 MB, SHA-256 `d2deae65…` en los reportes. |
| O3 | 35–70 tok/s en un portátil común | **No se cumplió.** | Unos 12 tok/s en un i5-10310U. El benchmark en el portátil tardó 1,419 s para 30 respuestas (unos 47 s cada una). |
| O4 | CLI hexagonal (Puertos y Adaptadores) con motor mock | **Hecho.** | `cli/`, 44 tests de Vitest en verde. |
| O5 | Restringir la salida con gramáticas deterministas (GBNF / esquemas de tipos) | **No se hizo.** | Ninguna parte del pipeline usa gramáticas. |
| O6 | Medir convergencia, loss y olvido catastrófico | **Parcial.** Solo loss de entrenamiento. | Sin loss de validación ni prueba de olvido. |
| O7 | Medir velocidad y memoria en un portátil | **Parcial.** | Velocidad medida una vez; la RAM (~1.5 GB) se cita, no se registró. |
| O8 | Mostrar que el SLM supera a modelos comerciales generales en adherencia a Clean Architecture (hipótesis) | **No se probó.** | No existe línea base frontera, del maestro ni few-shot. La cifra "frontera" de 90.5 no tiene ejecución que la respalde (auditoría F3/F8). |
| O9 | Publicar los pesos en Hugging Face, con CI/CD y documentación | **Parcial.** | Existen el script de subida y la model card; la publicación no se pudo verificar desde el repo; no hay CI (no existe `.github/`). |
| O10 | Replicable en Colab T4 / GPUs de 6 GB con QLoRA | **No se probó.** | `train_lora.py` no tiene ruta QLoRA. |
| O11 | "Model Factory" para otros modelos base | **Diseñado, no ejecutado.** | Existen recetas para Llama-3.2 y Gemma-2; ninguna se entrenó. |

---

## 3. Las ideas

### 3.1 Idea central

**Llevar las convenciones de arquitectura a los pesos de un modelo pequeño que corre offline,** en lugar de dar instrucciones a un modelo grande en la nube. Se dan dos motivaciones:

- **Deriva arquitectónica:** los asistentes generales acoplan el código de dominio a los frameworks.
- **Privacidad y costo:** el código propietario no debería salir de la máquina.

La idea es sólida y actual. Los modelos pequeños, especializados y locales son una línea de trabajo activa.

El eslabón débil es suponer que **un dataset pequeño puede enseñar arquitectura y no solo forma superficial**. Con 18 prompts, el modelo aprendió una plantilla: una interfaz, una clase con constructor privado y un `create` estático, y ningún import de framework. No aprendió una habilidad transferible. El perfil medido lo muestra (§5.3 E7).

### 3.2 "Cold Staging, Hot Burst"

Todo el trabajo que no necesita GPU se hizo en un portátil. El DGX Spark compartido se usó solo en ventanas cortas y con límite de tiempo, cuidando explícitamente no molestar a otros usuarios (puertos 8080/8084 intactos, límite de fracción de memoria, `--max-time-minutes`).

Es una de las contribuciones más transferibles del proyecto: un método de operación documentado para hardware académico limitado y compartido ([bitácora de sesión](../history/session-2026-10-22-burst-and-lessons.md)).

### 3.3 Alternativas consideradas

Las alternativas están en [ideas.md](./ideas.md):

- **RAG sobre literatura de arquitectura:** descartada porque los patrones no quedan internalizados en los pesos.
- **Linters asistidos por modelo:** pospuesta.

Vista en retrospectiva, **la combinación de un linter o chequeador AST con un modelo** es la extensión más natural. El proyecto ya tiene un analizador AST, y las debilidades medidas (corrección, invariantes) son justo lo que un chequeador determinista puede verificar.

### 3.4 Destilación con un modelo maestro

`Qwen3-Coder-30B` generó pares de entrenamiento a partir de un conjunto pequeño de plantillas. Es una práctica estándar. Aquí, sin embargo, las plantillas eran pocas y las salidas del maestro nunca se verificaron, así que sus errores (truncamiento, `any`, código que no compila) pasaron directo al entrenamiento (§5.1).

### 3.5 El proceso es la contribución principal

La propuesta habla sobre todo de un **proceso**: cómo especializar, empaquetar y evaluar un modelo pequeño con hardware limitado y compartido. El modelo es un producto de ese proceso. Evaluado etapa por etapa:

| Etapa | Qué existe | ¿Repetible desde el repo? | Carencia principal |
| :-- | :-- | :-- | :-- |
| 1. Semillas y datos del maestro | Semillas de un proyecto real, generador con maestro limitado en tiempo, validador de formato | Sí, si hay un endpoint del maestro | No hay filtro de calidad (compilación, `any`, truncamiento) entre el maestro y el set de entrenamiento (D3–D5) |
| 2. Partición y auditoría | Partición determinista sin prompts compartidos, auditoría de fugas, tests unitarios | Sí, totalmente offline | Se añadió después de la ejecución publicada; pocos prompts distintos (D1, D9) |
| 3. Ráfaga de entrenamiento | LoRA basado en recetas, límite de tiempo y de memoria, loss solo sobre la respuesta, fusión | Sí, con GPU; `--dry-run` en CPU | Sin loss de validación; los parámetros no se guardaron junto con la ejecución (T1–T3) |
| 4. Exportación y servicio | Script GGUF Q4/Q5/Q8, `llama-server` en puertos aislados | Sí, con `llama.cpp` | Solo se evaluó Q4_K_M |
| 5. Evaluación | Benchmark atribuido, puntuación por AST, ejecución en el Spark con un comando, chequeos de respuestas vacías y fallos | Sí | La métrica revisa patrones, no corrección; sin más líneas base que el modelo base (E1–E9) |
| 6. Cliente | CLI hexagonal, motor mock, 44 tests | Sí, totalmente offline | Timeout y manejo de la salida en CPU (C1, C2); sin CI |
| 7. Operación en hardware compartido | Aislamiento de puertos, límites de tiempo según el horario del laboratorio, runbooks, bitácoras | Sí, documentado | Depende de rutas y hosts del laboratorio |

**Lectura:** cada etapa existe, tiene scripts y está documentada. Los eslabones más débiles son los dos **filtros de calidad**: los datos que entran al entrenamiento (etapa 1) y las salidas que entrega el modelo (etapa 5). Ambos se pueden arreglar sin reentrenar el modelo publicado, así que son un alcance natural para el trabajo futuro.

---

## 4. Qué está bien

| Área | Fortaleza | Evidencia |
| :-- | :-- | :-- |
| Pipeline | Completo y reproducible en su estructura: datos, entrenamiento, fusión, GGUF, servicio, CLI y benchmark existen y se conectan mediante archivos. | Estructura del repositorio; [README](../../README.md) §2. |
| Ganancia medida | El fine-tune supera al base en todos los componentes de CAS. La diferencia pareada es robusta dentro de esta métrica: media +16.8, DE 21.5, t ≈ 4.3, IC bootstrap al 95% [10.0, 25.2], 24 victorias / 6 empates / 0 derrotas. | `evaluation/reports/spark-20261105T143540Z/` |
| Comparación justa | Misma suite, misma cuantización, misma configuración del servidor, mismo motor de puntuación; modelos identificados por SHA-256; 0 respuestas fallidas o vacías. | `RESULT.md`, bloques `meta` de los reportes. |
| Ingeniería del CLI | Se respeta la separación hexagonal: `domain/` y `application/` no importan nada de infraestructura. Los errores son valores (`Result<T, E>`), TypeScript es estricto y sin `any`, y 44 tests corren offline contra un motor mock. | `cli/`; `pnpm test`. |
| Atribución y trazabilidad | Los reportes registran nombre del modelo, hash del archivo, endpoint, suite y fallos. Un script audita las fugas. El proyecto corrigió en commits sus propias afirmaciones anteriores. | `meta` de `eval_benchmark.py`; `audit_dataset.py`; commits `13fab38`, `aab8d9b`. |
| Uso responsable del hardware compartido | Nunca toca los puertos de otros usuarios; limita memoria y tiempo; ninguna operación destructiva automatizada. | `spark_day.sh`, `train_lora.py`, bitácora §5. |
| Higiene de datos, versión actual | La partición actual no comparte prompts (0/34 prompts del holdout en train) y descarta respuestas truncadas. La suite no comparte prompts ni código con el entrenamiento. | `python3 dataset/audit_dataset.py`. |
| Tests | 44 tests de Vitest y los tests de Python con stdlib pasan (el del loop de entrenamiento se omite sin torch). | Ejecutados el 2026-11-13. |

---

## 5. Qué está mal

La severidad refleja el impacto sobre las afirmaciones que se pueden citar de este proyecto.

### 5.1 Dataset (máxima prioridad)

El modelo publicado se entrenó con `dataset/train.jsonl` del commit `64f3c6c`.

| ID | Severidad | Hallazgo | Cómo reproducirlo |
| :-- | :-- | :-- | :-- |
| D1 | Alta | **18 prompts distintos** detrás de 138 filas; los prompts más repetidos aparecen 13 veces. El modelo ve pocas tareas muchas veces. | `git show 64f3c6c:dataset/train.jsonl` y contar los mensajes de usuario distintos. |
| D2 | Alta | **La tarea no coincide.** Solo 42 filas (4 prompts distintos) piden refactorizar código dado. El resto pide escribir entidades, value objects, puertos o tests nuevos a partir de una descripción. Todos los casos del benchmark son refactorizaciones. | Clasificar los prompts por el verbo inicial. |
| D3 | Alta | **49/138 respuestas (35%) están truncadas**: tienen un número impar de bloques de código y terminan a mitad de código. El modelo se entrenó para producir respuestas cortadas. (El `split_dataset.py` actual las descarta.) | Contar las respuestas con un número impar de bloques. |
| D4 | Media | **20/138 respuestas contienen `any` explícito** (p. ej. `(mockRepository as any)`, `private stripe: any`), aunque la regla del proyecto es cero `any`. | `grep` de `: any`, `as any`, `<any>`. |
| D5 | Media | **Las respuestas no están verificadas.** De las 107 respuestas con bloques TypeScript cerrados, 82 pasan el chequeo de tipos aislado (estricto; imports y nombres sin resolver ignorados), así que alrededor de 1 de cada 4 tiene errores de tipos reales. Nada verifica el comportamiento. | Script de chequeo de tipos de la §7. |
| D6 | Media | **Contenido fuera de objetivo**: 13 filas son Python (FastAPI/SQLAlchemy) en un proyecto de TypeScript. | Contar los lenguajes de los bloques. |
| D7 | Media | **Lo aprendido no se transfiere.** 120/138 respuestas usan `Result`, pero el fine-tune usa `Result` en 2/30 respuestas del benchmark. El patrón se aprendió para "escribe un caso de uso", no para "refactoriza esta clase". | Comparar las respuestas de entrenamiento con las salidas del Spark. |
| D8 | Media | **El holdout anterior estaba contaminado**: 28/30 prompts del holdout también estaban en train (auditoría F1). Por eso la evaluación depende solo de la suite de 30 casos. | `audit_dataset.py` sobre `64f3c6c`. |
| D9 | Baja | **La partición actual es mejor pero sigue siendo pequeña**: 91 filas de train (28 prompts distintos) y 34 de holdout (8 prompts distintos); un prompt aún se repite 14 veces. No se ha entrenado con ella. | `python3 dataset/audit_dataset.py`. |

### 5.2 Entrenamiento

| ID | Severidad | Hallazgo | Evidencia |
| :-- | :-- | :-- | :-- |
| T1 | Media | **Los hiperparámetros documentados difieren del código que entrenó el modelo.** La ejecución publicada usó lote por dispositivo **1** (fijo en el DataLoader), así que el lote efectivo fue **4**, no 8: unos 105 pasos de optimización. La tasa de aprendizaje fue **constante**, sin warmup ni decaimiento coseno. No se fijó semilla. La documentación (informe final, roadmap, model card) dice lote 2, efectivo 8 y schedule coseno. | `git show fb3e812:training/train_lora.py` (DataLoader `batch_size=... else 1`; sin scheduler). |
| T2 | Media | **Sin loss de validación ni early stopping.** Un loss final de entrenamiento de 0.031 con 18 prompts distintos indica memorización. | Log de entrenamiento en la bitácora de progreso. |
| T3 | Media | **HEAD ya no reproduce el modelo publicado.** Las correcciones de entrenamiento del 2026-11-08 (semilla, warmup, weight decay, conexión del tamaño de lote) y la nueva partición hacen que reentrenar desde HEAD produzca otro modelo. Para reproducirlo exactamente hacen falta los datos de `64f3c6c` y el código de `fb3e812`. | `git log -- training/train_lora.py`. |
| T4 | Baja | **La longitud de contexto difiere entre la documentación y la receta.** El roadmap y el informe final dicen 1,024 tokens; la receta dice 2,048. Las respuestas más largas que el límite se truncaron en silencio en el tokenizador. | `recipes/qwen2.5-coder-1.5b.yaml`. |

### 5.3 Evaluación y la métrica CAS

| ID | Severidad | Hallazgo | Evidencia |
| :-- | :-- | :-- | :-- |
| E1 | Alta | **Una respuesta vacía saca 50/100**: 30 puntos por no tener imports prohibidos y 20 por no tener `any`. Hay que leer 74.8 como unos 25 puntos por encima de no hacer nada, y 58.0 como 8 por encima. | `test_empty_output_scores_fifty_floor`. |
| E2 | Alta | **El componente "puertos" cuenta cualquier `interface` o alias `type`**, incluidos props y DTOs. No revisa el nombre (`I…Repository`) ni la inyección por constructor, aunque la documentación dice que sí. De los 91 "contratos" detectados en el fine-tune, unos 37 tienen nombre de puerto. | `evaluation/ast_analyzer.ts`, bloque de puertos; notas del reporte como `Port: UserAccountProps`. |
| E3 | Media | **El componente "invariantes" es superficial.** Una guarda es cualquier `if` o `throw` directo en un constructor. "Result" es cualquier referencia de tipo cuyo nombre contenga `Result`. | `ast_analyzer.ts`. |
| E4 | Media | **La puntuación de frontera premia la omisión.** Solo 4/30 respuestas del fine-tune contienen algún import, frente a 23/30 del base. El 30/30 de frontera viene en parte de no poner imports, y nada verifica que la funcionalidad original siga ahí. | Salidas del Spark. |
| E5 | Alta | **La compilación y el comportamiento no forman parte de la puntuación.** Un chequeo de tipos aislado (estricto; imports y nombres sin resolver ignorados) aprueba **14/30** respuestas del fine-tune y **17/30** del base. Ninguno tiene errores de sintaxis. El fine-tune **no** produce código con tipos correctos más a menudo que el base, y no existe chequeo de comportamiento. | §7. |
| E6 | Media | **Validez de la suite.** La suite tiene 30 casos, todos escritos por el autor y todos con la misma instrucción inicial. Las entradas tienen **3–18 líneas (mediana 8.5)**. Los resultados no dicen nada sobre archivos reales. | `legacy_benchmark_suite.jsonl`. |
| E7 | Media | **El fine-tune converge a una sola plantilla.** 26/30 de sus puntuaciones están entre 65 y 75. La seguridad de invariantes es 0 en 26/30 casos. Casi toda la ganancia viene de frontera (+6.0) y puertos (+6.7); invariantes suma +2.4. | Distribuciones de puntuación de los reportes. |
| E8 | Media | **El prompt de evaluación difiere del de uso y entrenamiento.** El benchmark envía solo un mensaje de usuario. El entrenamiento y el CLI usan un prompt de sistema. | Payload de `eval_benchmark.py`; `RefactorCodeUseCase.ts`. |
| E9 | Alta | **No hay líneas base más allá del modelo base sin ajustar.** No hay base con prompt few-shot, ni maestro de 30B, ni modelo frontera. Sin ellas no se puede evaluar la hipótesis (O8). | Auditoría F3, F8. |
| E10 | Baja | **Ruido entre ejecuciones.** El mismo GGUF dio 72.5 (portátil) y 74.8 (Spark): 17/30 casos idénticos, diferencia media por caso de 4.7. Una ejecución anterior sin atribución (76.3) difiere en 17.8 puntos por caso. | Reportes del portátil y del Spark. |

### 5.4 CLI y herramientas

| ID | Severidad | Hallazgo | Evidencia |
| :-- | :-- | :-- | :-- |
| C1 | Media | **En CPU, el CLI agota el tiempo con respuestas largas.** El timeout del adaptador es de 60 s por defecto y no tiene flag en el CLI; `maxTokens` vale 2,048 por defecto. A unos 12 tok/s, cualquier respuesta de más de unos 700 tokens supera el timeout. | `LlamaServerAdapter.ts`; `infrastructure/cli/index.ts`. |
| C2 | Media | **`-o` escribe la respuesta cruda del modelo** (bloques Markdown y prosa) en el archivo `.ts` de destino. No se extrae el bloque de código. | `index.ts` escribe `refactoredCode` tal cual llega. |
| C3 | Baja | **La URL por defecto es `127.0.0.1:8080`.** En un portátil no hay problema, pero en el Spark es el servidor de otro usuario. | `index.ts`. |
| C4 | Baja | **Sin CI.** Los tests existen pero nada los ejecuta automáticamente. | No existe `.github/`. |
| C5 | Baja | **El enrutamiento de Copilot en VS Code (`copilot-local`) no está evaluado.** No se ha medido qué pasa al enviar completado en línea a un modelo de chat que nunca se entrenó para fill-in-the-middle. | `bin/copilot-local`. |

### 5.5 Documentación y afirmaciones (fe de erratas)

Estas afirmaciones siguen en el repositorio y **no** deben citarse tal como están:

| Dónde | Afirmación | Corrección |
| :-- | :-- | :-- |
| [propuesta.md](./propuesta.md) | 35–70 tok/s en portátiles; salida restringida por GBNF | Unos 12 tok/s medidos; no se implementó ninguna gramática. |
| [final-report-and-presentation.md](./final-report-and-presentation.md) | La hipótesis y la conclusión afirman superioridad sobre modelos frontera | No se probó (E9). |
| Ídem | Schedule coseno; lote efectivo 8; 1,024 tokens; 34 tests; título "cero fuga de datos" | LR constante, lote efectivo 4 (T1); 2,048 tokens (T4); hoy hay 44 tests; el holdout anterior tenía fuga (D8). |
| [MODEL_CARD.md](../../../MODEL_CARD.md) | Frontera 90.5; "erradica el 100%" de los imports prohibidos; hardware "GB10 / Ampere A100"; lote 2 × acumulación 4 | 90.5 no medido (F3); 30/30 en una suite de 30 casos, en parte por omisión (E4); solo GB10; lote efectivo 4. |
| [progress-and-milestones.md](../history/progress-and-milestones.md), `status.py` | "100% completo"; conteos de tests antiguos; estado del Spark desactualizado | Prueba de concepto; ver este documento. |
| [detailed-roadmap.md](../history/detailed-roadmap.md) | Schedule coseno; 1,024 tokens; ráfaga de 3B | No es lo que se ejecutó. |

---

## 6. Qué se puede citar con seguridad

**Afirmaciones sostenidas:**

1. Un modelo de 1.5B ajustado con LoRA y cuantizado a 4 bits corre totalmente offline en un portátil solo con CPU a unos 12 tok/s y ocupa alrededor de 1 GB en disco.
2. En una suite propia de 30 casos de refactorización en TypeScript, puntuada con una métrica de patrones sobre el AST, obtiene 74.8 frente a 58.0 de su modelo base en condiciones idénticas (IC al 95% de la diferencia: [10.0, 25.2]). La mayor parte de la ganancia está en eliminar imports de frameworks y declarar interfaces.
3. El método "Cold Staging, Hot Burst" permitió entrenar y evaluar en una GPU compartida en ventanas cortas sin molestar a otros usuarios.

**Afirmaciones que hay que evitar:**

- Que supera, iguala o se acerca a modelos frontera o comerciales.
- Que produce refactorizaciones correctas o que conservan el comportamiento, o código con tipos más correctos que su base (14/30 frente a 17/30 pasan el chequeo de tipos).
- Que es rápido.
- Que los datos de entrenamiento eran grandes, diversos, verificados o libres de fugas (en el modelo publicado).

---

## 7. Cómo reproducir las cifras de este documento

```bash
# Tests
cd cli && pnpm install && pnpm test                    # 44 passed
python3 -m unittest discover -s evaluation/tests -v
python3 -m unittest dataset/test_split_dataset.py -v

# Partición publicada frente a la actual
git show 64f3c6c:dataset/train.jsonl > /tmp/train_published.jsonl
python3 dataset/audit_dataset.py                       # partición actual: 0/34 de solapamiento

# Código de entrenamiento que produjo el modelo publicado
git show fb3e812:training/train_lora.py | grep -n "batch_size=2 if dry_run"

# Evidencia del benchmark
cat evaluation/reports/spark-20261105T143540Z/RESULT.md
```

La estadística pareada (bootstrap con 10,000 remuestreos, semilla 0) y el chequeo de tipos aislado usaron las salidas commiteadas en `evaluation/reports/spark-20261105T143540Z/cas/`. El chequeo de tipos usó el compilador de TypeScript de `cli/node_modules` con `strict: true` y destino ES2022 + DOM. Como los fragmentos están incompletos, antes de chequear se borran las sentencias `import` y `export … from` (las respuestas suelen traer varios archivos en un mismo bloque que se importan entre sí), y se ignoran los diagnósticos de módulos y nombres sin resolver (TS2304, TS2307 y afines). El chequeo está en el repositorio como `dataset/typecheck_answers.mjs` y se ejecuta sobre las respuestas del dataset con `python3 dataset/audit_dataset.py --typecheck`.

> **Corrección (2026-11-13):** una versión anterior de este documento usaba un chequeo que no borraba los imports. Esos imports chocaban con declaraciones del mismo fragmento y subestimaban la tasa de aprobación: decía 46/107 para las respuestas de entrenamiento publicadas (ahora 82/107) y 12/30 frente a 5/30 en el benchmark (ahora 14/30 frente a 17/30). Esa versión presentaba por error la corrección de tipos como una fortaleza del fine-tune.

---

## 8. Líneas de trabajo que se desprenden de este análisis

En orden de valor para el trabajo futuro:

1. **Primero los datos.** Construir 150–200 tareas de refactorización distintas a partir de código real. Verificar cada respuesta con `tsc --noEmit` y el analizador AST, sin `any` y sin truncamiento. Mantener un holdout que no comparta prompts.
2. **Una métrica mejor.** Añadir a CAS chequeos de compilación y de comportamiento. Puntuar los puertos por nombre e inyección. Restar el piso de la respuesta vacía.
3. **Líneas base reales.** Un modelo base con prompt few-shot, el maestro de 30B y un modelo frontera, todos con la misma suite. Es la única manera de probar la hipótesis original.
4. **Sistema híbrido.** Modelo más un chequeador determinista (o GBNF): el chequeador rechaza o repara las salidas que no compilan. Esto retoma la idea pospuesta del linter.
5. **Reentrenar** solo después de los puntos 1–3, con loss de validación, semilla fija y los hiperparámetros guardados junto con la ejecución.
