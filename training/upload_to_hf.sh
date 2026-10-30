#!/usr/bin/env bash
# ==============================================================================
# Edge Clean Copilot — Upload GGUF Model & Model Card to Hugging Face Hub
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GGUF_DIR="${SCRIPT_DIR}/output/gguf"
GGUF_FILE="${GGUF_DIR}/clean-copilot-1.5b-q4_k_m.gguf"
MODEL_CARD="${SCRIPT_DIR}/../MODEL_CARD.md"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <hf-username>/<repo-name>"
  echo "Example: $0 Jrgil20/edge-clean-copilot-1.5b-gguf"
  exit 1
fi

REPO_ID="$1"

echo "======================================================"
echo "  Uploading Edge Clean Copilot to Hugging Face Hub"
echo "======================================================"
echo "Repository ID : ${REPO_ID}"
echo "Model File    : ${GGUF_FILE}"
echo "Model Card    : ${MODEL_CARD}"
echo ""

# Ensure huggingface_hub is available
if ! python3 -c "import huggingface_hub" 2>/dev/null; then
  echo "[1/3] Installing huggingface_hub..."
  pip install --quiet --upgrade huggingface_hub
else
  echo "[1/3] huggingface_hub already installed."
fi

# Ensure user is logged in
echo "[2/3] Checking Hugging Face authentication..."
if ! hf auth whoami 2>/dev/null && ! python3 -c "from huggingface_hub import HfFolder; assert HfFolder.get_token() is not None" 2>/dev/null; then
  echo ""
  echo "⚠️  You are not logged into Hugging Face."
  echo "Run 'hf auth login' or 'huggingface-cli login' with a Write-permission token first."
  exit 1
fi

# Upload repository folder
echo "[3/3] Uploading GGUF binary and Model Card to https://huggingface.co/${REPO_ID}..."
python3 - <<EOF
import sys
from huggingface_hub import HfApi, create_repo

repo_id = "${REPO_ID}"
api = HfApi()

try:
    create_repo(repo_id=repo_id, repo_type="model", exist_ok=True)
    print(f"--> [OK] Repository verified: {repo_id}")
except Exception as e:
    print(f"--> Note on repo creation: {e}")

# Upload README (Model Card)
api.upload_file(
    path_or_fileobj="${MODEL_CARD}",
    path_in_repo="README.md",
    repo_id=repo_id,
    repo_type="model",
)
print("--> [OK] Uploaded README.md (Model Card)")

# Upload GGUF Binary
api.upload_file(
    path_or_fileobj="${GGUF_FILE}",
    path_in_repo="clean-copilot-1.5b-q4_k_m.gguf",
    repo_id=repo_id,
    repo_type="model",
)
print("--> [OK] Uploaded clean-copilot-1.5b-q4_k_m.gguf")
print(f"\n🎉 Successfully published to: https://huggingface.co/{repo_id}")
EOF
