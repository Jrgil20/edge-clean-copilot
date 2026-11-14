# Edge Clean Copilot — Dataset Specification

## 1. Objective
Curate high-quality, canonical Clean Architecture and Spec-Driven Development synthetic pairs to fine-tune Small Language Models (SLMs: Qwen-2.5-Coder-1.5B/3B) using LoRA.

---

## 2. Target Format: OpenAI / ChatML Format
To ensure full compatibility with Hugging Face `trl` (`SFTTrainer`) and Qwen's native chat template, all samples must follow standard ChatML structure in JSONL format:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are Edge Clean Copilot, an expert software architect specialized in Clean Architecture, Domain-Driven Design (DDD), and SOLID principles. You strictly enforce the Dependency Rule: domain and application layers must never depend on external libraries, frameworks, databases, or infrastructure."
    },
    {
      "role": "user",
      "content": "<Task instruction + context or dirty code snippet>"
    },
    {
      "role": "assistant",
      "content": "<Canonical Clean Architecture solution with clear layer separation>"
    }
  ]
}
```

---

## 3. Dataset Taxonomy (Target Distribution)

| Category ID | Category Name | Description | Target % |
| :--- | :--- | :--- | :--- |
| `ARCH_REFACTOR` | Coupled to Clean Refactor | Taking messy, framework-coupled code (e.g., Express + raw SQL) and decomposing it into Domain, Application, Port, and Adapter. | 40% |
| `USE_CASE_GEN` | Use Case & Domain Impl | Given a business spec, producing pure Domain Entities, Value Objects, and Application Use Cases with DTOs and `Result<T, E>`. | 30% |
| `AAA_TEST_GEN` | Isolated Unit Testing | Generating Arrange-Act-Assert unit tests for Use Cases using pure in-memory test doubles (fakes/mocks) without external DBs. | 20% |
| `SOLID_CRITIQUE` | Architecture Lint / Critique | Analyzing a code snippet, pointing out Clean Architecture violations (Dependency Inversion, layer leakage), and providing targeted fixes. | 10% |

---

## 4. Quality Rules for Every Sample
1. **Zero Domain Pollution:** Domain entities and use cases must not import ORMs (Prisma, Mongoose, TypeORM), HTTP frameworks (Express, Nest, FastAPI), or external SDKs.
2. **Explicit Contracts:** Every infrastructure dependency must be inverted through an interface (Port) defined in Application or Domain.
3. **Deterministic Error Handling:** Domain/Application layers must return explicit `Result` types or typed domain errors, avoiding untyped exception throwing.

---

## 5. Stratified Partitioning & Data Leakage Prevention

To uphold strict scientific and academic validity, the cumulative dataset of 168 unified samples (`seed_examples.jsonl` + `generated_examples.jsonl`) is partitioned into two mutually exclusive sets using [`split_dataset.py`](./split_dataset.py) with a fixed random seed (`seed=42`):

> **Note (2026-11-08):** the figures below describe the dataset the published model was trained on. `split_dataset.py` now splits by normalized prompt and drops answers with unbalanced code fences, and, since 2026-11-13, also drops answers with explicit `any` or that fail an isolated `tsc` type-check, so rerunning it yields 82 samples (67 train / 15 holdout, 32 distinct prompts). The holdout takes the smallest prompt groups first and is capped at 15 rows so no category is drained. `ARCH_REFACTOR` and `SOLID_CRITIQUE` were rebuilt from 19 hand-authored examples (10 per category after the split) in `authored_examples.jsonl`; they are still thin, so generate more with `generate_with_teacher.py` before retraining.
>
> **Update (2026-11-13):** `claude_authored_examples.jsonl` adds a pilot of 20 `ARCH_REFACTOR` examples written by Claude (Opus 5.5) in a Claude Code session, each a distinct task (Express, NestJS, Fastify, Next.js, Hono, React, Angular, Redux, Kafka, SQS, BullMQ, cron, Socket.IO, GraphQL and CLI code; two inputs are plain JavaScript). They use the CLI's system prompt and `Result<T, E>` with typed errors, and all pass the audit. They are kept in their own file for provenance and are pending manual review. A second batch of 20 adds more variety: 10 rows use the CLI's exact refactor prompt with whole files as input, some inputs are small and get short answers, one models errors as `DomainError` subclasses, and one input is already well layered and only needs a minimal fix. `classify_sample` now ignores code blocks and the phrase "Ports & Adapters" so these rows count as `ARCH_REFACTOR`. With the 40 rows, the split yields 123 samples (108 train / 15 holdout, 73 distinct prompts, 49 `ARCH_REFACTOR`).
>
> **Update (2026-11-13, third batch):** the file now has 100 rows. Four parallel Claude subagents added 20 `USE_CASE` (business spec → domain + use case with `Result`), 20 `AAA_TEST` (vitest tests with in-memory fakes; all 20 also compile against the real vitest types together with the use case in their prompt), 10 `SOLID_CRITIQUE` and 10 `PORT_ADAPTER` rows, and an adversarial reviewer checked the first 40 rows for behavior changes the type-check cannot see; its 3 high and 2 medium findings (and most low ones) were fixed. The split then yielded 183 samples (168 train / 15 holdout, 133 distinct prompts); superseded by the next update. Vendor details in the port rows (error codes, status strings) were written from memory and not checked against live documentation.
>
> **Update (2026-11-13, holdout and audit):** the holdout cap is now 30 rows (`--eval-target-count`), giving 153 train / 30 holdout rows (25 distinct holdout prompts, at least 4 rows per category). `audit_dataset.py` also flags near-duplicate code inside prompts (`--near-dup-threshold`); `--strict` fails if a holdout prompt's code is near a training one. The split the published model was trained on is kept as `published_model_train.jsonl` / `published_model_holdout.jsonl` (commit `64f3c6c`); `split_dataset.py` does not read them.


```text
======================================================================
168 Unified Canonical Samples (~191,364 Total Tokens)
  ├── train.jsonl         : 138 samples (82.1%) — ~156,395 tokens
  └── eval_holdout.jsonl  :  30 samples (17.9%) —  ~34,969 tokens
======================================================================
```

| Architectural Category | Total Samples | Training Set (`train.jsonl`) | Holdout Evaluation Set (`eval_holdout.jsonl`) |
| :--- | :--- | :--- | :--- |
| **Port & Adapter Decoupling** | 68 | 56 | 12 |
| **Entity & Value Objects** | 46 | 38 | 8 |
| **AAA Unit Testing** | 30 | 25 | 5 |
| **SOLID Lint & Critiques** | 13 | 11 | 2 |
| **Architecture Refactoring** | 11 | 9 | 2 |
| **TOTAL** | **168** | **138** | **30** |

> [!IMPORTANT]
> The `eval_holdout.jsonl` produced by the current `split_dataset.py` is split by prompt: no prompt appears in both `train.jsonl` and the holdout (check with `python3 audit_dataset.py`). The published model, however, was trained on the older split (`published_model_train.jsonl`), where 28/30 holdout prompts were also in train, and 11 of the 30 rows of the current `eval_holdout.jsonl` have their prompt in `published_model_train.jsonl`. So the current holdout cannot evaluate the published model; the disjoint legacy suite in `evaluation/` is the real evaluation set for it. It is reserved for the post-training benchmark in [`evaluation/`](../evaluation/).
