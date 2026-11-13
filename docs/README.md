# Edge Clean Copilot: Documentation

🌐 **[Versión en español →](../es/docs/README.md)**

Documentation is grouped by purpose. If you are citing this project as background (prior work), start with the analysis.

## Reading order for citing this project as background

1. [project/project-analysis.md](./project/project-analysis.md): objectives vs results, ideas, what is right and wrong, claims you can safely cite.
2. [project/propuesta.md](./project/propuesta.md): the original proposal and hypothesis.
3. [usage/use-cases.md](./usage/use-cases.md): where the model is valid to use and where it is not.
4. [next-steps.md](./next-steps.md): known problems and planned work (dataset first).

---

## `project/`: proposal, ideas and assessment

| Document | Content |
| :-- | :-- |
| [project-analysis.md](./project/project-analysis.md) | Full analysis (2026-11-13): planned vs achieved objectives, the process stage by stage, strengths, findings, errata, safe claims. **Current reference.** |
| [propuesta.md](./project/propuesta.md) | Original proposal: vision, hypothesis, phases, replicability. |
| [ideas.md](./project/ideas.md) | Idea bank: selected idea and alternatives considered (RAG, linters). |
| [final-report-and-presentation.md](./project/final-report-and-presentation.md) | Course final report and 12-slide defense guide (2026-10-23). Some claims are superseded; see the errata in the analysis (§5.5). |

## `usage/`: using the model

| Document | Content |
| :-- | :-- |
| [use-cases.md](./usage/use-cases.md) | Valid use cases, ideal environments, what not to use it for, practical tips. |
| [model-usage-and-sharing-guide.md](./usage/model-usage-and-sharing-guide.md) | Starting and stopping the server, CLI, VS Code routing, sharing via Ollama, LM Studio and Hugging Face. |

## `evaluation/`: benchmark, audit and Spark runs

| Document | Content |
| :-- | :-- |
| [evaluation-audit-2026-11-05.md](./evaluation/evaluation-audit-2026-11-05.md) | Audit of tests, benchmark and dataset; findings F1–F10; measured head-to-head result. |
| [spark-day-plan.md](./evaluation/spark-day-plan.md) | One-command plan for a Spark session. |
| [spark-eval-runbook.md](./evaluation/spark-eval-runbook.md) | Step-by-step manual runbook for the base vs fine-tune comparison. |

## `architecture/`: design

| Document | Content |
| :-- | :-- |
| [model-factory-architecture.md](./architecture/model-factory-architecture.md) | Recipe-driven design for specialising other base models. Only the Qwen 1.5B recipe has been trained. |

## `history/`: logs and plans as written at the time

These documents record what was planned or believed on their dates. Figures in them may be superseded; the analysis is the current reference.

| Document | Content |
| :-- | :-- |
| [progress-and-milestones.md](./history/progress-and-milestones.md) | Phase-by-phase progress log. |
| [detailed-roadmap.md](./history/detailed-roadmap.md) | Execution plan for weeks 4–15. |
| [session-2026-10-22-burst-and-lessons.md](./history/session-2026-10-22-burst-and-lessons.md) | Spark session log: port isolation, teacher data burst, lessons learned. |

## Other

- [next-steps.md](./next-steps.md): known problems and planned work.
- [index.html](./index.html): interactive web showcase (written before the audit; its figures are not authoritative).
- Subsystem READMEs: [dataset](../dataset/README.md), [training](../training/README.md), [evaluation](../evaluation/README.md), [CLI](../cli/README.md).
