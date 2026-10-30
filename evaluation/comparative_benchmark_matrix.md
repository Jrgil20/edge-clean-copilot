# Edge Clean Copilot — Comparative Benchmark Evaluation Matrix

> **Evaluation Harness:** [`eval_benchmark.py`](./eval_benchmark.py) (Clean Architecture Score - CAS 0–100)  
> **Benchmark Suite:** [`legacy_benchmark_suite.jsonl`](./legacy_benchmark_suite.jsonl) (30 legacy code samples)
>
> **Figures Source:** [model card](https://huggingface.co/jrgil/edge-clean-copilot-1.5b-gguf) (self-reported). Base and frontier speeds are unverified.
>
> **Last Verification:** 2026-10-30 02:05:04Z

---

## 1. Executive Findings

Measured on the 30-case legacy suite, the fine-tuned **Edge Clean Copilot** improves on its base model by 28.1 CAS points (+58.3%) but does not reach the frontier baseline:

$$\Delta \text{CAS} = +28.1\text{ pts} \quad (+58.3\% \text{ improvement over base foundation model})$$

1. **Domain Boundaries:** ECC scores 30.0 / 30, at the maximum and above the frontier baseline (29.0).
2. **Invariants and Ports:** ECC trails the frontier baseline on invariant safety (11.7 vs 22.5) and port decoupling (16.0 vs 23.0).
3. **Edge Efficiency:** ~12 tokens/sec measured on CPU (Intel i5-10310U) with ~1.5 GB RAM. Slow on long inputs; every output should be reviewed before use.

_Single-run variance: a 2026-10-29 rerun measured 73.8 CAS (invariant 2.0), so the composite can move by several points between runs._

---

## 2. Architectural Scoring Matrix (CAS 0–100)

| Architectural Dimension | Maximum Points | Base Model (Qwen 1.5B) | **Edge Clean Copilot (GGUF)** | Frontier Cloud (Gemini 3.8 Flash) | Net Improvement (ECC vs Base) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Domain Boundary Isolation** | 30 pts | 14.5 pts | **30.0 pts** | 29.0 pts | **+15.5 pts** |
| **Invariant & Result Pattern** | 25 pts | 8.2 pts | **11.7 pts** | 22.5 pts | **+3.5 pts** |
| **Port & Adapter Decoupling** | 25 pts | 10.5 pts | **16.0 pts** | 23.0 pts | **+5.5 pts** |
| **TypeScript Type Rigor (Zero `any`)** | 20 pts | 15.0 pts | **18.7 pts** | 16.0 pts | **+3.7 pts** |
| **TOTAL CAS COMPOSITE** | **100 pts** | **48.2 pts** | **76.3 pts (Grade B)** | **90.5 pts (Grade A)** | **+28.1 pts (+58.3%)** |

---

## 3. Operational Edge Infrastructure Metrics

| Metric | Base Model (1.5B F16) | **Edge Clean Copilot (`Q4_K_M`)** | Frontier Cloud LLM | Operational Advantage |
| :--- | :---: | :---: | :---: | :--- |
| **Generation Speed** | ~52.0 tok/s (unverified) | **~12.0 tok/s (measured, CPU)** | ~85.0 tok/s (unverified) | Usable on CPU; slow on long inputs |
| **System RAM Footprint** | ~3.1 GB | **~1.5 GB** | 0 GB (Cloud) | Runs easily alongside developer IDE |
| **Disk Binary Footprint** | ~3.10 GB | **~0.94 GB** | 0 MB (API) | Lightweight portable distribution |
| **Network & Privacy** | Offline | **100% Offline / Zero Telemetry** | Internet Required | Complete proprietary code protection |
| **Per-Token Cost** | $0.00 | **$0.00** | Metered API billing | Zero recurring API expenditures |

---

## 4. Visual Vector Representation

A vector SVG chart representing this data has been generated at [`benchmark_comparison_chart.svg`](./benchmark_comparison_chart.svg).
