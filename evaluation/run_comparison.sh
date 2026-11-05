#!/usr/bin/env bash
# Run the CAS benchmark against one or more already-running llama-server endpoints
# with an identical suite, so every score in the report has a traceable model.
#
# Usage:
#   ./run_comparison.sh \
#     --suite legacy_benchmark_suite.jsonl \
#     --model "ecc-ft=http://127.0.0.1:8085/v1/chat/completions=../training/output/gguf/clean-copilot-1.5b-q4_k_m.gguf" \
#     --model "qwen-base=http://127.0.0.1:8086/v1/chat/completions=/path/to/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
#
# Each --model is NAME=URL[=MODEL_FILE]. MODEL_FILE is optional and, when it exists
# locally, its SHA-256 is recorded in the report meta block.
# This script never starts servers and never opens SSH connections.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUITE="${SCRIPT_DIR}/legacy_benchmark_suite.jsonl"
OUT_DIR="${SCRIPT_DIR}/reports/$(date -u +%Y%m%dT%H%M%SZ)"
MODELS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --suite)   SUITE="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --model)   MODELS+=("$2"); shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ ${#MODELS[@]} -gt 0 ]] || { echo "At least one --model NAME=URL[=FILE] is required." >&2; exit 2; }
[[ -f "$SUITE" ]] || { echo "Suite not found: $SUITE" >&2; exit 2; }

# Preflight: every endpoint must answer /health before any benchmark starts.
for spec in "${MODELS[@]}"; do
  IFS='=' read -r name url _ <<<"$spec"
  base="${url%/v1/*}"
  if ! curl -fsS --max-time 5 "${base}/health" >/dev/null; then
    echo "Preflight failed: ${name} is not healthy at ${base}/health" >&2
    exit 1
  fi
done

mkdir -p "$OUT_DIR"
cp "$SUITE" "${OUT_DIR}/suite.jsonl"
sha256sum "$SUITE" | awk '{print $1}' > "${OUT_DIR}/suite.sha256"

for spec in "${MODELS[@]}"; do
  IFS='=' read -r name url file <<<"$spec"
  args=(--url "$url" --prompts "$SUITE" --model-name "$name"
        --output "${OUT_DIR}/report_${name}.json"
        --save-completions "${OUT_DIR}/completions_${name}.jsonl")
  [[ -n "${file:-}" ]] && args+=(--model-file "$file")
  echo "==> ${name}"
  python3 "${SCRIPT_DIR}/eval_benchmark.py" "${args[@]}"
done

python3 - "$OUT_DIR" <<'PY'
import json, sys, glob, os
out = sys.argv[1]
print("\n== Summary (check prompts_failed before comparing averages) ==")
for path in sorted(glob.glob(os.path.join(out, "report_*.json"))):
    d = json.load(open(path))
    m = d.get("meta", {})
    print(f"{m.get('model_name')}: avg={d['average_score']} n={d['total_samples']} "
          f"failed={len(m.get('prompts_failed') or [])} sha256={str(m.get('model_sha256'))[:12]}")
PY
echo "Reports saved to: ${OUT_DIR}"
