# Edge Clean Copilot — Technical Knowledge Base & Documentation Index

> **Primary Audience:** AI Agents (Coding assistants, RAG pipelines, Autonomous planners)  
> **Secondary Audience:** Human Engineers & Evaluators  

This directory contains the authoritative technical documentation, session telemetry logs, milestone progress tracking, and engineering roadmaps for the **Edge Clean Copilot** semester project.

---

## 1. Documentation Index

| Document | Purpose | Key Content |
| :--- | :--- | :--- |
| **[Interactive Web Portal (docs/index.html)](./index.html)** | Visual Presentation & Interactive Showcase | Single-file responsive showcase with live Before/After diff comparator and CAS metrics. |
| **[Model Usage & Sharing Guide](./model-usage-and-sharing-guide.md)** | Operational Guide & Distribution Blueprint | How to power on/off, use CLI, run in VS Code, share via Ollama/LM Studio/Hugging Face. |
| **[Model Factory Architecture](./model-factory-architecture.md)** | Scalable SLM Specialization Architecture | Blueprint for ingesting new open-weight SLMs, decoupled factory stages, and reproducibility. |
| **[Final Technical Report & Presentation](./final-report-and-presentation.md)** | Academic Capstone Paper & Defense Guide | Comprehensive engineering report, formal Clean Architecture Score findings, and 12-slide presentation script. |
| **[Detailed Execution Roadmap](./detailed-roadmap.md)** | Operational Master Plan (Weeks 4–15) | Hyperparameters, quantization targets, automated benchmark metrics, and weekly action items. |
| **[Progress & Verified Milestones](./progress-and-milestones.md)** | Live Status Board | Empirical progress breakdown across Phases 1, 2, 3, and 4. |
| **[Session Report: 2026-10-22](./session-2026-10-22-burst-and-lessons.md)** | Technical Log & Root Cause Analysis | Multi-tenant port isolation (8085 vs 8080), 160-sample dataset burst, GB10 ML runtime setup. |

---

## 2. Related Project Assets

- **[Project Vision & Proposal](../propuesta.md):** Academic articulation, core hypothesis, and theoretical framework.
- **[Dataset Directory](../dataset/README.md):** Synthetic dataset generators, seed canonical examples, and validation suites.
- **[LoRA Training Pipeline](../training/README.md):** PyTorch training loop, dynamic collator, and adapter merge utilities.
- **[Hexagonal CLI](../cli/README.md):** Ports & Adapters TypeScript implementation and offline mock adapters.
