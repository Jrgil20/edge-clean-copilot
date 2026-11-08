#!/usr/bin/env bash
# One-command base-vs-fine-tune evaluation, meant to be run ON the DGX Spark
# after you have connected to it. It never opens SSH connections.
#
#   ./spark_day.sh --preflight-only   # checks only; changes nothing
#   ./spark_day.sh                    # full run
#
# Steps: preflight -> build base GGUF (same pipeline/quant as the fine-tune)
#        -> serve both models (8085 / 8086) -> run_comparison.sh -> RESULT.md
#
# Safety: ports 8080/8084 are never touched. Only processes started by this
# script are stopped. A busy port serving an unexpected model aborts the run.
#
# Overrides (environment): PORT_FT, PORT_BASE, CTX, NGL, LLAMA_SERVER, BASE_GGUF_DIR,
#   LLAMA_CPP_DIR, FT_GGUF, BASE_SNAPSHOT, HF_HOME.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROYECTO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PORT_FT="${PORT_FT:-8085}"
PORT_BASE="${PORT_BASE:-8086}"
CTX="${CTX:-4096}"
NGL="${NGL:-99}"
FT_GGUF="${FT_GGUF:-${PROYECTO_DIR}/training/output/gguf/clean-copilot-1.5b-q4_k_m.gguf}"
BASE_GGUF_DIR="${BASE_GGUF_DIR:-${PROYECTO_DIR}/training/output/gguf-base}"
BASE_NAME="qwen2.5-coder-1.5b-base"
BASE_GGUF="${BASE_GGUF_DIR}/${BASE_NAME}-q4_k_m.gguf"
SUITE="${SCRIPT_DIR}/legacy_benchmark_suite.jsonl"
RUN_DIR="${SCRIPT_DIR}/reports/spark-$(date -u +%Y%m%dT%H%M%SZ)"
PREFLIGHT_ONLY=false
STARTED_PIDS=()

for arg in "$@"; do
  case "$arg" in
    --preflight-only) PREFLIGHT_ONLY=true ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

FAILS=()
pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; FAILS+=("$1"); }

# --- helpers ---------------------------------------------------------------
served_model() {  # prints the model id/path a llama-server on $1 reports, or nothing
  curl -fsS --max-time 3 "http://127.0.0.1:$1/v1/models" 2>/dev/null | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    items=d.get("data") or d.get("models") or []
    print(items[0].get("id") or items[0].get("model") or items[0].get("name") or "")
except Exception:
    pass'
}
port_busy() { ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1$"; }
cleanup() {
  for pid in "${STARTED_PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null && echo "Stopped server PID $pid (started by this run)"
  done
}
trap cleanup EXIT

find_llama_dir() {
  for d in "${LLAMA_CPP_DIR:-}" "${HOME}/llama.cpp" "/home/ucab-spark1/llama.cpp"; do
    [[ -n "$d" && -d "$d" ]] && { echo "$d"; return; }
  done
}

# --- preflight -------------------------------------------------------------
echo "== Preflight =="
LLAMA_DIR="$(find_llama_dir || true)"
SERVER_BIN="${LLAMA_SERVER:-$(command -v llama-server 2>/dev/null || true)}"
[[ -z "$SERVER_BIN" && -n "$LLAMA_DIR" && -x "${LLAMA_DIR}/build/bin/llama-server" ]] && SERVER_BIN="${LLAMA_DIR}/build/bin/llama-server"
[[ -x "${SERVER_BIN:-}" ]] && pass "llama-server: ${SERVER_BIN}" || fail "llama-server not found (set LLAMA_SERVER=/path)"

[[ -n "$LLAMA_DIR" ]] && pass "llama.cpp dir: ${LLAMA_DIR}" || fail "llama.cpp directory not found (set LLAMA_CPP_DIR=/path)"
command -v curl >/dev/null && pass "curl" || fail "curl missing"
command -v python3 >/dev/null && pass "python3" || fail "python3 missing"
[[ -f "$FT_GGUF" ]] && pass "fine-tune GGUF: ${FT_GGUF}" || fail "fine-tune GGUF missing: ${FT_GGUF}"
[[ -f "$SUITE" ]] && pass "suite: ${SUITE}" || fail "suite missing: ${SUITE}"

HF_HUB="${HF_HOME:-${HOME}/.cache/huggingface}/hub"
BASE_SNAPSHOT="${BASE_SNAPSHOT:-$(ls -d "${HF_HUB}"/models--Qwen--Qwen2.5-Coder-1.5B-Instruct/snapshots/*/ 2>/dev/null | head -1)}"
BASE_SNAPSHOT="${BASE_SNAPSHOT%/}"
if [[ -f "$BASE_GGUF" ]]; then
  pass "base GGUF already built: ${BASE_GGUF}"
elif [[ -n "$BASE_SNAPSHOT" && -f "${BASE_SNAPSHOT}/config.json" ]] && ls "${BASE_SNAPSHOT}"/*.safetensors >/dev/null 2>&1; then
  pass "base HF snapshot cached: ${BASE_SNAPSHOT}"
else
  fail "base model not cached (expected under ${HF_HUB}); pre-cache Qwen/Qwen2.5-Coder-1.5B-Instruct or set BASE_SNAPSHOT"
fi

if (cd "${PROYECTO_DIR}/cli" && pnpm exec tsx --version >/dev/null 2>&1); then
  pass "AST engine available (pnpm + tsx)"
else
  fail "AST engine unavailable: run 'cd ${PROYECTO_DIR}/cli && pnpm install --frozen-lockfile' (regex fallback would not be comparable with the earlier 76.3)"
fi

avail_gb=$(df -BG --output=avail "${PROYECTO_DIR}" 2>/dev/null | tail -1 | tr -dc '0-9')
[[ "${avail_gb:-0}" -ge 8 ]] && pass "disk free: ${avail_gb} GB" || fail "less than 8 GB free for conversion (have ${avail_gb:-?} GB)"

for spec in "${PORT_FT}:$(basename "$FT_GGUF")" "${PORT_BASE}:$(basename "$BASE_GGUF")"; do
  port="${spec%%:*}"; expect="${spec#*:}"
  if port_busy "$port"; then
    got="$(served_model "$port")"
    if [[ "$got" == *"$expect"* ]]; then pass "port ${port} already serves ${expect} (will reuse)"
    else fail "port ${port} is busy serving '${got:-unknown}', expected '${expect}' (not touching it; free it or set PORT_*)"; fi
  else
    pass "port ${port} is free"
  fi
done
for p in 8080 8084; do port_busy "$p" && echo "  [INFO] port ${p} in use by other lab services (left untouched)"; done

if [[ ${#FAILS[@]} -gt 0 ]]; then
  echo; echo "Preflight FAILED (${#FAILS[@]} issue(s)). Nothing was started or modified."
  exit 1
fi
echo "Preflight OK."
$PREFLIGHT_ONLY && exit 0

# --- run -------------------------------------------------------------------
mkdir -p "$RUN_DIR"
{
  echo "date_utc: $(date -u +%FT%TZ)"
  echo "host: $(hostname)"
  echo "proyecto_git: $(git -C "$PROYECTO_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "llama_server: $("$SERVER_BIN" --version 2>&1 | head -2 | tr '\n' ' ')"
  echo "gpu: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo none)"
  echo "ctx: ${CTX}  ngl: ${NGL}  ports: ft=${PORT_FT} base=${PORT_BASE}"
} > "${RUN_DIR}/environment.txt"
python3 "${PROYECTO_DIR}/dataset/audit_dataset.py" > "${RUN_DIR}/dataset_audit.txt" 2>&1 || true

if [[ ! -f "$BASE_GGUF" ]]; then
  echo "== Building base GGUF with the same pipeline as the fine-tune =="
  "${PROYECTO_DIR}/training/convert_to_gguf.sh" \
    --input-dir "$BASE_SNAPSHOT" --output-dir "$BASE_GGUF_DIR" \
    --model-name "$BASE_NAME" --llama-dir "$LLAMA_DIR" --clean-f16 \
    || { echo "Base conversion failed." >&2; exit 1; }
fi

start_server() {  # $1=port $2=gguf
  if port_busy "$1"; then echo "Reusing server on :$1"; return 0; fi
  echo "Starting llama-server on :$1 ($(basename "$2"))"
  nohup "$SERVER_BIN" -m "$2" --port "$1" -c "$CTX" -ngl "$NGL" \
    > "${RUN_DIR}/server_$1.log" 2>&1 &
  STARTED_PIDS+=("$!")
  for _ in $(seq 1 90); do
    curl -fsS --max-time 2 "http://127.0.0.1:$1/health" >/dev/null 2>&1 && return 0
    sleep 2
  done
  echo "Server on :$1 did not become healthy; see ${RUN_DIR}/server_$1.log" >&2
  return 1
}
start_server "$PORT_FT" "$FT_GGUF" || exit 1
start_server "$PORT_BASE" "$BASE_GGUF" || exit 1

echo "== Running comparison =="
"${SCRIPT_DIR}/run_comparison.sh" --suite "$SUITE" --out-dir "${RUN_DIR}/cas" \
  --model "ecc-ft=http://127.0.0.1:${PORT_FT}/v1/chat/completions=${FT_GGUF}" \
  --model "qwen-base=http://127.0.0.1:${PORT_BASE}/v1/chat/completions=${BASE_GGUF}" \
  || { echo "Comparison failed." >&2; exit 1; }

# --- verdict ---------------------------------------------------------------
python3 - "$RUN_DIR" <<'PY'
import json, sys, os
run = sys.argv[1]
ft = json.load(open(os.path.join(run, "cas", "report_ecc-ft.json")))
bs = json.load(open(os.path.join(run, "cas", "report_qwen-base.json")))
fm, bm = ft["meta"], bs["meta"]
delta = round(ft["average_score"] - bs["average_score"], 2)
checks = [
    ("No dropped prompts", not fm["prompts_failed"] and not bm["prompts_failed"]),
    ("Same suite", fm["cases_file"] == bm["cases_file"]),
    ("AST engine for both", fm["engine"] == "ast" and bm["engine"] == "ast"),
    ("Models differ (SHA-256)", fm["model_sha256"] and fm["model_sha256"] != bm["model_sha256"]),
    ("No empty/refusal outputs (each scores 50 for free)", not fm["degenerate_samples"] and not bm["degenerate_samples"]),
    ("Full sample count", ft["total_samples"] == bs["total_samples"] == 30),
]
ok = all(c for _, c in checks)
if not ok:
    verdict = "INVALID RUN: fix the failed checks before using any number."
elif delta < 5:
    verdict = f"Difference {delta:+} < 5 points: do NOT claim improvement."
else:
    verdict = f"Fine-tune is {delta:+} CAS points over base on this heuristic suite (30 cases, self-run)."
lines = ["# Spark run result", "",
    f"| Model | Avg CAS | n | failed | sha256 |", "| :-- | --: | --: | --: | :-- |",
    f"| ecc-ft | {ft['average_score']} | {ft['total_samples']} | {len(fm['prompts_failed'] or [])} | {str(fm['model_sha256'])[:12]} |",
    f"| qwen-base | {bs['average_score']} | {bs['total_samples']} | {len(bm['prompts_failed'] or [])} | {str(bm['model_sha256'])[:12]} |",
    "", "## Checks", ""] + [f"- [{'x' if c else ' '}] {n}" for n, c in checks] + ["", f"**Verdict:** {verdict}", "",
    "Manual step still required: read 5 completions per model in `cas/completions_*.jsonl`."]
open(os.path.join(run, "RESULT.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
PY
echo
echo "Run directory: ${RUN_DIR}"
echo "Copy back (run from the laptop): scp -r <spark-host>:${RUN_DIR} <local>/proyecto/evaluation/reports/"
