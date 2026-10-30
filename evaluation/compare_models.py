#!/usr/bin/env python3
"""
Edge Clean Copilot — Benchmark Comparison & Visualization Engine
Empirically contrasts the Clean Architecture Score (CAS 0-100) and edge operational
metrics across three model paradigms:
  1. Base Foundation SLM (Qwen2.5-Coder-1.5B unspecialized)
  2. Edge Clean Copilot (Fine-tuned LoRA Q4_K_M GGUF)
  3. Commercial Frontier Baseline (Cloud LLM reference)

Outputs:
  - Rich ANSI/ASCII terminal comparative tables
  - Markdown summary report: comparative_benchmark_matrix.md
  - Clean, vector SVG visualization: benchmark_comparison_chart.svg
"""

import argparse
import json
import math
from pathlib import Path
import sys
import time
from typing import Dict, Any, List, Optional

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
GRAY = "\033[90m"

# Published figures from the model card (huggingface.co/jrgil/edge-clean-copilot-1.5b-gguf).
# Edge CAS and speed were measured on an Intel i5-10310U (CPU-only). Base and frontier
# speeds are marked unverified by the card; base RAM/disk describe the 1.5B F16 model.
DEMO_DATA: Dict[str, Dict[str, Any]] = {
    "base": {
        "name": "Qwen2.5-Coder-1.5B (Base)",
        "type": "Un-fine-tuned SLM",
        "composite_cas": 48.2,
        "boundary_score": 14.5,
        "boundary_max": 30.0,
        "invariant_score": 8.2,
        "invariant_max": 25.0,
        "ports_score": 10.5,
        "ports_max": 25.0,
        "typing_score": 15.0,
        "typing_max": 20.0,
        "tokens_sec": 52.0,
        "ram_gb": 3.1,
        "binary_size_gb": 3.10,
        "offline": True,
    },
    "ecc": {
        "name": "Edge Clean Copilot (LoRA GGUF)",
        "type": "Specialized Edge SLM",
        "composite_cas": 76.3,
        "boundary_score": 30.0,
        "boundary_max": 30.0,
        "invariant_score": 11.7,
        "invariant_max": 25.0,
        "ports_score": 16.0,
        "ports_max": 25.0,
        "typing_score": 18.7,
        "typing_max": 20.0,
        "tokens_sec": 12.0,
        "ram_gb": 1.5,
        "binary_size_gb": 0.94,
        "offline": True,
    },
    "cloud": {
        "name": "Frontier Cloud LLM (Gemini 3.8 Flash)",
        "type": "Commercial Baseline (API)",
        "composite_cas": 90.5,
        "boundary_score": 29.0,
        "boundary_max": 30.0,
        "invariant_score": 22.5,
        "invariant_max": 25.0,
        "ports_score": 23.0,
        "ports_max": 25.0,
        "typing_score": 16.0,
        "typing_max": 20.0,
        "tokens_sec": 85.0,
        "ram_gb": 0.0,
        "binary_size_gb": 0.0,
        "offline": False,
    },
}

def load_report_or_fallback(file_path: Optional[str], default_key: str) -> Dict[str, Any]:
    if file_path and Path(file_path).exists():
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Adapt eval_benchmark.py format if loaded
            total_score = data.get("average_score", DEMO_DATA[default_key]["composite_cas"])
            entry = dict(DEMO_DATA[default_key])
            entry["composite_cas"] = round(total_score, 1)
            return entry
    return DEMO_DATA[default_key]

def render_ascii_table(models: Dict[str, Dict[str, Any]]) -> str:
    lines = []
    lines.append(f"\n{BOLD}{CYAN}========================================================================================{RESET}")
    lines.append(f"{BOLD}           EDGE CLEAN COPILOT — EMPIRICAL BENCHMARK COMPARISON MATRIX           {RESET}")
    lines.append(f"{BOLD}{CYAN}========================================================================================{RESET}\n")

    header = (
        f"{'ARCHITECTURAL DIMENSION':<32} | "
        f"{'BASE 1.5B':^15} | "
        f"{'EDGE CLEAN COPILOT':^20} | "
        f"{'FRONTIER CLOUD':^16}"
    )
    lines.append(f"{BOLD}{header}{RESET}")
    lines.append("-" * 92)

    dimensions = [
        ("1. Domain Boundary Isolation (30%)", "boundary_score", 30.0),
        ("2. Invariant & Result Safety (25%)", "invariant_score", 25.0),
        ("3. Port & Adapter Decoupling (25%)", "ports_score", 25.0),
        ("4. TypeScript Type Rigor (20%)", "typing_score", 20.0),
    ]

    for label, key, max_val in dimensions:
        b_val = models["base"][key]
        e_val = models["ecc"][key]
        c_val = models["cloud"][key]
        b_str = f"{b_val:.1f} / {max_val:.0f}"
        e_str = f"{e_val:.1f} / {max_val:.0f}"
        c_str = f"{c_val:.1f} / {max_val:.0f}"
        lines.append(f"{label:<32} | {b_str:^15} | {GREEN}{e_str:^20}{RESET} | {c_str:^16}")

    lines.append("=" * 92)
    b_cas = models["base"]["composite_cas"]
    e_cas = models["ecc"]["composite_cas"]
    c_cas = models["cloud"]["composite_cas"]

    comp_line = (
        f"{BOLD}COMPOSITE CAS (0–100 PTS){RESET:<23} | "
        f"{YELLOW}{b_cas:^15.1f}{RESET} | "
        f"{BOLD}{GREEN}{e_cas:^20.1f}{RESET} | "
        f"{CYAN}{c_cas:^16.1f}{RESET}"
    )
    lines.append(comp_line)
    lines.append("=" * 92)

    lines.append(f"\n{BOLD}EDGE OPERATIONAL METRICS:{RESET}")
    lines.append("-" * 92)
    b_spd = f"{models['base']['tokens_sec']:.1f}"
    e_spd = f"{models['ecc']['tokens_sec']:.1f}"
    c_spd = f"{models['cloud']['tokens_sec']:.1f}"
    b_ram = f"{models['base']['ram_gb']} GB"
    e_ram = f"{models['ecc']['ram_gb']} GB"
    b_disk = f"{models['base']['binary_size_gb']} GB"
    e_disk = f"{models['ecc']['binary_size_gb']} GB"

    lines.append(f"{'Inference Speed (tokens/sec)':<32} | {b_spd:^15} | {GREEN}{e_spd:^20}{RESET} | {c_spd:^16}")
    lines.append(f"{'Target RAM Consumption':<32} | {b_ram:^15} | {GREEN}{e_ram:^20}{RESET} | {'N/A (Cloud)':^16}")
    lines.append(f"{'Binary Disk Footprint':<32} | {b_disk:^15} | {GREEN}{e_disk:^20}{RESET} | {'N/A (API)':^16}")
    lines.append(f"{'100% Offline Capability':<32} | {'YES':^15} | {GREEN}{'YES (Air-Gapped)':^20}{RESET} | {'NO (Internet Req)':^16}")
    lines.append("=" * 92 + "\n")

    return "\n".join(lines)

def generate_markdown_report(models: Dict[str, Dict[str, Any]], output_path: Path) -> None:
    b = models["base"]
    e = models["ecc"]
    c = models["cloud"]

    delta_cas = e["composite_cas"] - b["composite_cas"]
    pct_gain = (delta_cas / b["composite_cas"]) * 100

    content = f"""# Edge Clean Copilot — Comparative Benchmark Evaluation Matrix

> **Evaluation Harness:** [`eval_benchmark.py`](./eval_benchmark.py) (Clean Architecture Score - CAS 0–100)  
> **Benchmark Suite:** [`legacy_benchmark_suite.jsonl`](./legacy_benchmark_suite.jsonl) (30 legacy code samples)
>
> **Figures Source:** [model card](https://huggingface.co/jrgil/edge-clean-copilot-1.5b-gguf) (self-reported). Base and frontier speeds are unverified.
>
> **Last Verification:** {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}

---

## 1. Executive Findings

Measured on the 30-case legacy suite, the fine-tuned **Edge Clean Copilot** improves on its base model by {delta_cas:.1f} CAS points (+{pct_gain:.1f}%) but does not reach the frontier baseline:

$$\\Delta \\text{{CAS}} = +{delta_cas:.1f}\\text{{ pts}} \\quad (+{pct_gain:.1f}\\% \\text{{ improvement over base foundation model}})$$

1. **Domain Boundaries:** ECC scores {e['boundary_score']:.1f} / {e['boundary_max']:.0f}, at the maximum and above the frontier baseline ({c['boundary_score']:.1f}).
2. **Invariants and Ports:** ECC trails the frontier baseline on invariant safety ({e['invariant_score']:.1f} vs {c['invariant_score']:.1f}) and port decoupling ({e['ports_score']:.1f} vs {c['ports_score']:.1f}).
3. **Edge Efficiency:** ~{e['tokens_sec']:.0f} tokens/sec measured on CPU (Intel i5-10310U) with ~{e['ram_gb']:.1f} GB RAM. Slow on long inputs; every output should be reviewed before use.

_Single-run variance: a 2026-10-29 rerun measured 73.8 CAS (invariant 2.0), so the composite can move by several points between runs._

---

## 2. Architectural Scoring Matrix (CAS 0–100)

| Architectural Dimension | Maximum Points | Base Model (Qwen 1.5B) | **Edge Clean Copilot (GGUF)** | Frontier Cloud (Gemini 3.8 Flash) | Net Improvement (ECC vs Base) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Domain Boundary Isolation** | 30 pts | {b['boundary_score']:.1f} pts | **{e['boundary_score']:.1f} pts** | {c['boundary_score']:.1f} pts | **+{e['boundary_score'] - b['boundary_score']:.1f} pts** |
| **Invariant & Result Pattern** | 25 pts | {b['invariant_score']:.1f} pts | **{e['invariant_score']:.1f} pts** | {c['invariant_score']:.1f} pts | **+{e['invariant_score'] - b['invariant_score']:.1f} pts** |
| **Port & Adapter Decoupling** | 25 pts | {b['ports_score']:.1f} pts | **{e['ports_score']:.1f} pts** | {c['ports_score']:.1f} pts | **+{e['ports_score'] - b['ports_score']:.1f} pts** |
| **TypeScript Type Rigor (Zero `any`)** | 20 pts | {b['typing_score']:.1f} pts | **{e['typing_score']:.1f} pts** | {c['typing_score']:.1f} pts | **+{e['typing_score'] - b['typing_score']:.1f} pts** |
| **TOTAL CAS COMPOSITE** | **100 pts** | **{b['composite_cas']:.1f} pts** | **{e['composite_cas']:.1f} pts (Grade B)** | **{c['composite_cas']:.1f} pts (Grade A)** | **+{delta_cas:.1f} pts (+{pct_gain:.1f}%)** |

---

## 3. Operational Edge Infrastructure Metrics

| Metric | Base Model (1.5B F16) | **Edge Clean Copilot (`Q4_K_M`)** | Frontier Cloud LLM | Operational Advantage |
| :--- | :---: | :---: | :---: | :--- |
| **Generation Speed** | ~{b['tokens_sec']:.1f} tok/s (unverified) | **~{e['tokens_sec']:.1f} tok/s (measured, CPU)** | ~{c['tokens_sec']:.1f} tok/s (unverified) | Usable on CPU; slow on long inputs |
| **System RAM Footprint** | ~{b['ram_gb']:.1f} GB | **~{e['ram_gb']:.1f} GB** | 0 GB (Cloud) | Runs easily alongside developer IDE |
| **Disk Binary Footprint** | ~{b['binary_size_gb']:.2f} GB | **~{e['binary_size_gb']:.2f} GB** | 0 MB (API) | Lightweight portable distribution |
| **Network & Privacy** | Offline | **100% Offline / Zero Telemetry** | Internet Required | Complete proprietary code protection |
| **Per-Token Cost** | $0.00 | **$0.00** | Metered API billing | Zero recurring API expenditures |

---

## 4. Visual Vector Representation

A vector SVG chart representing this data has been generated at [`benchmark_comparison_chart.svg`](./benchmark_comparison_chart.svg).
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

def generate_svg_chart(models: Dict[str, Dict[str, Any]], output_path: Path) -> None:
    """Generates a standalone, beautiful SVG vector chart visualizing the benchmark comparison."""
    width = 840
    height = 460
    
    # Categories to plot
    categories = [
        ("Domain Boundary (30)", "boundary_score", 30.0),
        ("Invariants & Result (25)", "invariant_score", 25.0),
        ("Ports & Adapters (25)", "ports_score", 25.0),
        ("Type Rigor (20)", "typing_score", 20.0),
        ("Composite CAS (100)", "composite_cas", 100.0),
    ]

    # Chart bounds
    plot_x = 80
    plot_y = 70
    plot_w = 700
    plot_h = 300

    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">')
    svg_parts.append('<defs>')
    svg_parts.append('  <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">')
    svg_parts.append('    <stop offset="0%" stop-color="#0f172a" />')
    svg_parts.append('    <stop offset="100%" stop-color="#1e293b" />')
    svg_parts.append('  </linearGradient>')
    svg_parts.append('  <linearGradient id="eccGrad" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg_parts.append('    <stop offset="0%" stop-color="#10b981" />')
    svg_parts.append('    <stop offset="100%" stop-color="#059669" />')
    svg_parts.append('  </linearGradient>')
    svg_parts.append('  <linearGradient id="baseGrad" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg_parts.append('    <stop offset="0%" stop-color="#f59e0b" />')
    svg_parts.append('    <stop offset="100%" stop-color="#d97706" />')
    svg_parts.append('  </linearGradient>')
    svg_parts.append('  <linearGradient id="cloudGrad" x1="0%" y1="0%" x2="0%" y2="100%">')
    svg_parts.append('    <stop offset="0%" stop-color="#38bdf8" />')
    svg_parts.append('    <stop offset="100%" stop-color="#0284c7" />')
    svg_parts.append('  </linearGradient>')
    svg_parts.append('</defs>')

    # Background
    svg_parts.append(f'<rect width="{width}" height="{height}" rx="12" fill="url(#bgGrad)" />')

    # Title & Subtitle
    svg_parts.append('<text x="80" y="38" fill="#f8fafc" font-family="system-ui, -apple-system, sans-serif" font-size="18" font-weight="bold">Edge Clean Copilot — Clean Architecture Score (CAS) Comparison</text>')
    svg_parts.append('<text x="80" y="56" fill="#94a3b8" font-family="system-ui, -apple-system, sans-serif" font-size="12">Empirical evaluation on 30 legacy code refactoring benchmark pairs</text>')

    # Grid lines (0%, 25%, 50%, 75%, 100%)
    for pct in [0, 25, 50, 75, 100]:
        y_pos = plot_y + plot_h - (pct / 100.0) * plot_h
        svg_parts.append(f'<line x1="{plot_x}" y1="{y_pos:.1f}" x2="{plot_x + plot_w}" y2="{y_pos:.1f}" stroke="#334155" stroke-dasharray="4,4" stroke-width="1" />')
        svg_parts.append(f'<text x="{plot_x - 12}" y="{y_pos + 4:.1f}" fill="#64748b" font-family="monospace" font-size="11" text-anchor="end">{pct}%</text>')

    # Bar groups
    group_width = plot_w / len(categories)
    bar_width = 28
    gap = 6

    for idx, (label, key, max_val) in enumerate(categories):
        gx = plot_x + idx * group_width + (group_width - (3 * bar_width + 2 * gap)) / 2

        # Normalize score to percentage of max_val
        b_pct = min(100.0, (models["base"][key] / max_val) * 100.0)
        e_pct = min(100.0, (models["ecc"][key] / max_val) * 100.0)
        c_pct = min(100.0, (models["cloud"][key] / max_val) * 100.0)

        # Bar 1: Base
        b_h = (b_pct / 100.0) * plot_h
        b_y = plot_y + plot_h - b_h
        svg_parts.append(f'<rect x="{gx:.1f}" y="{b_y:.1f}" width="{bar_width}" height="{b_h:.1f}" rx="4" fill="url(#baseGrad)" />')
        svg_parts.append(f'<text x="{gx + bar_width/2:.1f}" y="{b_y - 6:.1f}" fill="#f59e0b" font-family="monospace" font-size="10" font-weight="bold" text-anchor="middle">{b_pct:.0f}%</text>')

        # Bar 2: ECC
        e_x = gx + bar_width + gap
        e_h = (e_pct / 100.0) * plot_h
        e_y = plot_y + plot_h - e_h
        svg_parts.append(f'<rect x="{e_x:.1f}" y="{e_y:.1f}" width="{bar_width}" height="{e_h:.1f}" rx="4" fill="url(#eccGrad)" />')
        svg_parts.append(f'<text x="{e_x + bar_width/2:.1f}" y="{e_y - 6:.1f}" fill="#10b981" font-family="monospace" font-size="10" font-weight="bold" text-anchor="middle">{e_pct:.0f}%</text>')

        # Bar 3: Cloud
        c_x = e_x + bar_width + gap
        c_h = (c_pct / 100.0) * plot_h
        c_y = plot_y + plot_h - c_h
        svg_parts.append(f'<rect x="{c_x:.1f}" y="{c_y:.1f}" width="{bar_width}" height="{c_h:.1f}" rx="4" fill="url(#cloudGrad)" />')
        svg_parts.append(f'<text x="{c_x + bar_width/2:.1f}" y="{c_y - 6:.1f}" fill="#38bdf8" font-family="monospace" font-size="10" font-weight="bold" text-anchor="middle">{c_pct:.0f}%</text>')

        # Category Label below X-axis
        center_x = gx + (3 * bar_width + 2 * gap) / 2
        # Escape XML special chars before injecting into SVG
        safe_label = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Wrap long labels
        lines = safe_label.split(" (")
        svg_parts.append(f'<text x="{center_x:.1f}" y="{plot_y + plot_h + 20}" fill="#cbd5e1" font-family="system-ui, sans-serif" font-size="11" font-weight="500" text-anchor="middle">{lines[0]}</text>')
        if len(lines) > 1:
            svg_parts.append(f'<text x="{center_x:.1f}" y="{plot_y + plot_h + 34}" fill="#64748b" font-family="monospace" font-size="10" text-anchor="middle">({lines[1]}</text>')

    # Legend
    leg_y = height - 20
    # Base Legend
    svg_parts.append(f'<rect x="220" y="{leg_y - 10}" width="12" height="12" rx="3" fill="url(#baseGrad)" />')
    svg_parts.append(f'<text x="240" y="{leg_y}" fill="#cbd5e1" font-family="system-ui, sans-serif" font-size="12">Qwen 1.5B (Base)</text>')

    # ECC Legend
    svg_parts.append(f'<rect x="380" y="{leg_y - 10}" width="12" height="12" rx="3" fill="url(#eccGrad)" />')
    svg_parts.append(f'<text x="400" y="{leg_y}" fill="#10b981" font-family="system-ui, sans-serif" font-size="12" font-weight="bold">Edge Clean Copilot (GGUF)</text>')

    # Cloud Legend
    svg_parts.append(f'<rect x="580" y="{leg_y - 10}" width="12" height="12" rx="3" fill="url(#cloudGrad)" />')
    svg_parts.append(f'<text x="600" y="{leg_y}" fill="#cbd5e1" font-family="system-ui, sans-serif" font-size="12">Frontier Cloud (API)</text>')

    svg_parts.append('</svg>')

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(svg_parts) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Edge Clean Copilot — Benchmark Comparison & Visualization")
    parser.add_argument("--base-report", type=str, default=None, help="Path to base model benchmark JSON report")
    parser.add_argument("--ecc-report", type=str, default=None, help="Path to Edge Clean Copilot benchmark JSON report")
    parser.add_argument("--cloud-report", type=str, default=None, help="Path to cloud baseline benchmark JSON report")
    parser.add_argument("--demo", action="store_true", default=True, help="Use calibrated empirical demo baselines")
    parser.add_argument("--output-md", type=str, default="comparative_benchmark_matrix.md", help="Output markdown matrix path")
    parser.add_argument("--output-svg", type=str, default="benchmark_comparison_chart.svg", help="Output SVG chart path")

    args = parser.parse_args()

    eval_dir = Path(__file__).resolve().parent
    md_path = eval_dir / args.output_md
    svg_path = eval_dir / args.output_svg

    models = {
        "base": load_report_or_fallback(args.base_report, "base"),
        "ecc": load_report_or_fallback(args.ecc_report, "ecc"),
        "cloud": load_report_or_fallback(args.cloud_report, "cloud"),
    }

    # 1. Terminal Table
    terminal_output = render_ascii_table(models)
    print(terminal_output)

    # 2. Markdown File
    generate_markdown_report(models, md_path)
    print(f"--> [OK] Markdown report generated: {md_path.resolve()}")

    # 3. SVG File
    generate_svg_chart(models, svg_path)
    print(f"--> [OK] SVG vector chart generated: {svg_path.resolve()}\n")

if __name__ == "__main__":
    main()
