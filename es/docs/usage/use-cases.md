# Casos de Uso Válidos: Dónde Usar el Modelo y Dónde No

> **Modelo:** `clean-copilot-1.5b-q4_k_m.gguf` (Qwen2.5-Coder-1.5B-Instruct + LoRA, 941 MB).
> **Base:** con qué se entrenó el modelo, qué midió el benchmark y a qué velocidad corre. La evidencia está en [project-analysis.md](../project/project-analysis.md).
> **Cómo ejecutarlo:** [model-usage-and-sharing-guide.md](./model-usage-and-sharing-guide.md).

---

## 1. El alcance en una tabla

| Dimensión | Dentro del alcance | Fuera del alcance |
| :-- | :-- | :-- |
| Tamaño de la entrada | Una clase o función de TypeScript, **hasta unas 20 líneas** (el benchmark usó 3–18 líneas) | Archivos completos, varios archivos, módulos |
| Lenguaje | TypeScript | Python, Go, Java, … (solo 13 filas de entrenamiento en Python) |
| Tarea | Quitar el acoplamiento a frameworks, declarar puertos, generar esqueletos de entidades, value objects y tests AAA | Refactorizaciones de código en producción que deban conservar el comportamiento, corrección de bugs, completado en línea |
| Uso de la salida | Un **borrador** que una persona lee, compila y edita | Código aplicado automáticamente |
| Entorno | Máquinas offline o aisladas de la red; un portátil con CPU y unos 2 GB de RAM libres | Edición interactiva donde importa la latencia (unos 47 s por respuesta en CPU) |
| Público | Docencia, demostraciones, investigación sobre modelos pequeños | Equipos que esperan calidad de modelo frontera |

---

## 2. Casos de uso válidos

Cada caso indica qué respalda la evidencia. "Medido" significa que lo cubrió el benchmark de 30 casos. "Entrenado" significa que estaba en los datos de entrenamiento, pero ningún benchmark lo midió.

### CU1: Extraer un puerto de una clase acoplada a un ORM o cliente HTTP (medido)

- **Entrada:** una clase pequeña que importa `axios`, `@prisma/client`, `mongoose`, etc. y los llama directamente.
- **Salida esperada:** una interfaz `I…Repository` o `I…Gateway`, una clase de dominio sin el import e inyección por constructor.
- **Evidencia:** las categorías con mejor puntuación, fine-tune frente a base: fuga HTTP 80.7 frente a 62.9; clase dios 80.0 frente a 38.3; acoplamiento a ORM 71.4 frente a 49.3. El fine-tune no dejó ningún import prohibido en 30/30 casos.
- **Revisar:** la lógica original puede desaparecer en vez de moverse. Compárala con la entrada.

### CU2: Quitar `any` y ajustar tipos en un fragmento pequeño (medido)

- **Evidencia:** componente de tipado 19.7/20 frente a 17.8/20 del base.
- **Revisar:** el `any` puede reemplazarse por una interfaz inventada. Confirma que los tipos nuevos coinciden con los datos reales.

### CU3: Generar el esqueleto de un value object o una entidad a partir de una descripción (entrenado)

- **Ejemplo:** "Implementa un Value Object puro `Money` con monto positivo y moneda ISO".
- **Evidencia:** fue la categoría de entrenamiento más grande. No estaba en el benchmark.
- **Revisar:** las guardas de invariantes son débiles en las salidas del benchmark (2.7/25). Si el modelo las omite, añade tú la validación y el manejo con `Result`.

### CU4: Generar el esqueleto de un test unitario AAA con un doble en memoria (entrenado)

- **Evidencia:** unas 25 filas de entrenamiento; no se evaluó en el benchmark.
- **Revisar:** algunas respuestas de entrenamiento usaban `as any` sobre el mock, así que el modelo puede repetirlo. Ejecuta el test.

### CU5: Docencia y demostración (respaldado)

- Mostrar la Regla de Dependencia, Puertos y Adaptadores y la diferencia entre una versión acoplada y una desacoplada con ejemplos pequeños, totalmente offline, en un aula o un laboratorio sin internet.
- Es el uso para el que el proyecto está mejor preparado.

### CU6: Línea base de investigación para modelos pequeños especializados (respaldado)

- Usar el GGUF, la suite y los reportes atribuidos como punto de partida reproducible para comparar estrategias de datos, métricas u otros modelos base.

---

## 3. Dónde es ideal usarlo

1. **Máquinas aisladas de la red o con restricciones de privacidad**, donde el código no puede salir del equipo y no se permite ningún asistente en la nube.
2. **Laboratorios y aulas** sin internet fiable, en portátiles comunes (no hace falta GPU).
3. **Ejecuciones por lotes, no interactivas**, por ejemplo generar durante la noche versiones desacopladas de una lista de clases pequeñas y revisarlas después.
4. **Un servidor local en una máquina con GPU** (por ejemplo el Spark en el puerto 8085). Ahí es mucho más rápido y puede atender a varios usuarios de un curso.

---

## 4. Dónde no usarlo

| No usar para | Por qué |
| :-- | :-- |
| Aplicar refactorizaciones a código en producción sin revisión | Solo 12/30 respuestas del benchmark pasaron el chequeo de tipos, y eso aisladas; el comportamiento nunca se verifica. |
| Archivos grandes o cambios en varios archivos | Se entrenó con secuencias de 2,048 tokens; se evaluó con entradas de 18 líneas o menos. |
| Invariantes, validación y manejo de errores con `Result` | Es el componente más débil (2.7/25); casi nunca los produce. |
| Completado en línea en tiempo real (enrutando Copilot en VS Code) | No se entrenó para fill-in-the-middle; unos 12 tok/s en CPU; nunca se evaluó. |
| Reemplazar un asistente frontera o comercial | Nunca se comparó con uno. |
| Lenguajes distintos de TypeScript | Casi no hay datos de entrenamiento. |

---

## 5. Consejos prácticos

- **Mantén las entradas cortas.** Una clase a la vez, de menos de unas 20 líneas. Divide antes el código más grande.
- **Usa el prompt de sistema con el que se entrenó el modelo.** El CLI ya lo envía. Si llamas directamente a la API HTTP, usa el de `cli/src/application/use-cases/RefactorCodeUseCase.ts`.
- **Mantén la temperatura baja** (0.1, el valor por defecto).
- **En CPU, pasa `--max-tokens 600` o menos al CLI.** El adaptador corta a los 60 s, y a unos 12 tok/s las respuestas más largas fallan.
- **No confíes en `-o` para archivos de código.** Escribe la respuesta completa (Markdown y prosa). Mejor usa `--diff` o copia el bloque de código a mano.
- **Compila siempre el resultado** (`tsc --noEmit`) y ejecuta tus tests antes de quedarte con él.
