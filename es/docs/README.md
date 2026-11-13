# Edge Clean Copilot: Documentación

🌐 **[English version →](../../docs/README.md)**

La documentación está agrupada por propósito. Si vas a citar este proyecto como antecedente (trabajo previo), empieza por el análisis.

## Orden de lectura para citar el proyecto como antecedente

1. [project/project-analysis.md](./project/project-analysis.md): objetivos frente a resultados, ideas, qué está bien y qué está mal, afirmaciones que se pueden citar con seguridad.
2. [project/retrospective.md](./project/retrospective.md): observaciones y lecciones: dónde está el valor y de dónde vienen los límites.
3. [project/propuesta.md](./project/propuesta.md): la propuesta original y su hipótesis.
4. [usage/use-cases.md](./usage/use-cases.md): dónde es válido usar el modelo y dónde no.
5. [next-steps.md](./next-steps.md): problemas conocidos y trabajo planeado (primero el dataset).

---

## `project/`: propuesta, ideas y evaluación

| Documento | Contenido |
| :-- | :-- |
| [project-analysis.md](./project/project-analysis.md) | Análisis completo (2026-11-13): objetivos planificados frente a logrados, el proceso etapa por etapa, fortalezas, hallazgos, fe de erratas, afirmaciones seguras. **Referencia vigente.** |
| [retrospective.md](./project/retrospective.md) | Observaciones y lecciones extraídas del análisis: el proceso por encima del artefacto, los datos como restricción decisiva, puntos ciegos de la métrica, preguntas abiertas. |
| [propuesta.md](./project/propuesta.md) | Propuesta original: visión, hipótesis, fases, replicabilidad. |
| [ideas.md](./project/ideas.md) | Banco de ideas: idea elegida y alternativas consideradas (RAG, linters). |
| [final-report-and-presentation.md](./project/final-report-and-presentation.md) | Informe final del curso y guion de defensa de 12 diapositivas (2026-10-23). Algunas afirmaciones quedaron superadas; ver la fe de erratas del análisis (§5.5). |

## `usage/`: uso del modelo

| Documento | Contenido |
| :-- | :-- |
| [use-cases.md](./usage/use-cases.md) | Casos de uso válidos, entornos ideales, para qué no usarlo, consejos prácticos. |
| [model-usage-and-sharing-guide.md](./usage/model-usage-and-sharing-guide.md) | Encender y apagar el servidor, CLI, enrutamiento en VS Code, compartir vía Ollama, LM Studio y Hugging Face. |

## `evaluation/`: benchmark, auditoría y ejecuciones en el Spark

| Documento | Contenido |
| :-- | :-- |
| [evaluation-audit-2026-11-05.md](./evaluation/evaluation-audit-2026-11-05.md) | Auditoría de tests, benchmark y dataset; hallazgos F1–F10; resultado de la comparación directa. |
| [spark-day-plan.md](./evaluation/spark-day-plan.md) | Plan de un comando para una sesión en el Spark. |
| [spark-eval-runbook.md](./evaluation/spark-eval-runbook.md) | Runbook manual paso a paso para la comparación base frente a fine-tune. |

## `architecture/`: diseño

| Documento | Contenido |
| :-- | :-- |
| [model-factory-architecture.md](./architecture/model-factory-architecture.md) | Diseño basado en recetas para especializar otros modelos base. Solo se ha entrenado la receta de Qwen 1.5B. |

## `history/`: bitácoras y planes tal como se escribieron

Estos documentos registran lo que se planeaba o se creía en su fecha. Sus cifras pueden estar superadas; la referencia vigente es el análisis.

| Documento | Contenido |
| :-- | :-- |
| [progress-and-milestones.md](./history/progress-and-milestones.md) | Bitácora de progreso por fases. |
| [detailed-roadmap.md](./history/detailed-roadmap.md) | Plan de ejecución de las semanas 4–15. |
| [session-2026-10-22-burst-and-lessons.md](./history/session-2026-10-22-burst-and-lessons.md) | Bitácora de sesión en el Spark: aislamiento de puertos, ráfaga de datos con el maestro, lecciones aprendidas. |

## Otros

- [next-steps.md](./next-steps.md): problemas conocidos y trabajo planeado.
- [index.html](./index.html): portal web interactivo (escrito antes de la auditoría; sus cifras no son la referencia).
- READMEs de los subsistemas: [dataset](../dataset/README.md), [entrenamiento](../training/README.md), [evaluación](../evaluation/README.md), [CLI](../../cli/README.md).
