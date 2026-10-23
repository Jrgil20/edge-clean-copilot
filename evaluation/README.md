# Edge Clean Copilot — Automated Architectural Benchmark Harness

> **Module:** Architectural Compliance & Evaluation Harness  
> **Target Models:** Base SLM (`Qwen-2.5-Coder-1.5B/3B`), LoRA Specialized Model, and Commercial Frontier Baselines  
> **Execution Engine:** Dual-Engine (Deterministic TypeScript Compiler AST via [`ast_analyzer.ts`](./ast_analyzer.ts) with Pure Python Regex Fallback)  

This directory contains the automated benchmark harness ([`eval_benchmark.py`](./eval_benchmark.py)) and AST parser ([`ast_analyzer.ts`](./ast_analyzer.ts)) designed to empirically measure, score, and prove the core hypothesis of the **Edge Clean Copilot** project.

---

## 1. Core Hypothesis Verification Formula

$$\text{Clean Architecture Score (CAS)} = S_{\text{boundary}} + S_{\text{invariant}} + S_{\text{ports}} + S_{\text{typing}}$$

Where:
- **$S_{\text{boundary}} \in [0, 30]$ (Domain Boundary Isolation):**
  - **30 pts:** Zero prohibited database, ORM, or web framework imports (`express`, `fastapi`, `typeorm`, `prisma`, `axios`, `mongoose`, `pg`, `redis`).
  - **15 pts:** Exactly 1 prohibited import.
  - **0 pts:** 2 or more prohibited imports.
- **$S_{\text{invariant}} \in [0, 25]$ (Invariant & Result Pattern Safety):**
  - **15 pts:** Functional `Result<T, E>` return type and `Result.ok` / `Result.fail` handling.
  - **10 pts:** Explicit constructor invariant validation guards (`throw new ValidationError` or length/type checks).
- **$S_{\text{ports}} \in [0, 25]$ (Port & Adapter Decoupling):**
  - **15 pts:** Explicit abstraction interface definition (`interface I...Repository`, `interface I...Port`, `interface I...Gateway`).
  - **10 pts:** Dependency injection via constructor (`constructor(private readonly repo: I...Repository)`) or adapter implementation (`implements I...Port`).
- **$S_{\text{typing}} \in [0, 20]$ (TypeScript Type Rigor):**
  - Base score: **20 pts**.
  - **Penalty:** $-5\text{ pts}$ per explicit `any` usage (`: any`, `<any>`, `as any`).
  - Comments and string literals are automatically stripped prior to inspection to avoid false positives (e.g. `company`, `many`).
  - Floor: **0 pts**.

---

## 2. Qualitative Grade Thresholds

| Total Score Range | Architectural Classification | Description |
| :--- | :--- | :--- |
| **85 – 100 pts** | **Grade A (Clean Architecture Certified)** | Strictly complies with Dependency Rule, invariant safety, and typed ports. |
| **70 – 84 pts** | **Grade B (Partially Clean)** | Minor omission (e.g., missing port interface or singular `any` type). |
| **50 – 69 pts** | **Grade C (Architectural Violations)** | Conflates infrastructure logic with domain rules; throws unhandled exceptions. |
| **0 – 49 pts** | **Grade F (Coupled Anti-Pattern)** | Imports ORMs or web frameworks directly into business entities. |

---

## 3. Usage & Recipes

### 3.1 Offline Evaluation (Batch JSONL)
Evaluate generated datasets or model completion files without needing an active inference server:

```bash
# Evaluate using the deterministic TypeScript Compiler AST Engine (default):
python3 eval_benchmark.py --cases legacy_benchmark_suite.jsonl

# Force heuristic regex fallback engine:
python3 eval_benchmark.py --cases legacy_benchmark_suite.jsonl --no-ast

# Evaluate the initial 10 control test cases
python3 eval_benchmark.py --cases test_benchmark_cases.jsonl
```

### 3.2 Live Evaluation (Real-Time Endpoint)
Evaluate live inference responses against a local or remote `llama-server` (e.g., port 8085 on DGX Spark):

```bash
python3 eval_benchmark.py \
  --url "http://192.168.6.35:8085/v1/chat/completions" \
  --prompts "legacy_benchmark_suite.jsonl" \
  --output "live_report.json"
```

---

## 4. Benchmark Suites & Datasets

| File | Cases | Scope & Antipatterns |
| :--- | :---: | :--- |
| **[`legacy_benchmark_suite.jsonl`](./legacy_benchmark_suite.jsonl)** | **30** | Full empirical benchmark covering ORMs/Prisma (7), HTTP/SDK leakage (7), Primitive Obsession (8), `any` proliferation (5), and God Classes (3). |
| **[`test_benchmark_cases.jsonl`](./test_benchmark_cases.jsonl)** | **10** | Control validation dataset for harness calibration and quick dry-runs. |
| **[`generate_benchmark_suite.py`](./generate_benchmark_suite.py)** | — | Synthetic deterministic generator for the 30-case benchmark suite. |

---

## 5. Model Comparison & Visualization Tool

Compare the Base SLM, Edge Clean Copilot, and Commercial Baselines across all CAS dimensions:

```bash
# Generate comparison matrix and SVG chart using empirical baselines
python3 compare_models.py --demo

# Generate comparison using specific benchmark JSON reports
python3 compare_models.py \
  --base-report base_report.json \
  --ecc-report ecc_report.json \
  --cloud-report cloud_report.json
```

### Generated Artifacts
- **[`comparative_benchmark_matrix.md`](./comparative_benchmark_matrix.md):** Consolidated comparative report with delta percentages and edge operational metrics.
- **[`benchmark_comparison_chart.svg`](./benchmark_comparison_chart.svg):** High-resolution vector chart ready for academic presentations.
