# Model Usage, Deployment & Sharing Guide

> **Project:** Edge Clean Copilot (ECC)  
> **Target Checkpoint:** `clean-copilot-1.5b-q4_k_m.gguf` (941 MB)  
> **Architecture:** Qwen 2.5 Coder 1.5B with Clean Architecture LoRA specialization  
> **Last Updated:** October 29, 2026  

---

## 1. Quick Location Reference

| Resource | Path / Destination | Size | Description |
| :--- | :--- | :---: | :--- |
| **Local Laptop GGUF** | `proyecto/models/clean-copilot-1.5b-q4_k_m.gguf` | 941 MB | Self-contained, 100% offline edge model. |
| **Spark Backup GGUFs** | `dgx-spark:/home/ucab-spark1/proyecto/training/output/gguf/` | 941 MB – 1.6 GB | `Q4_K_M`, `Q5_K_M`, and `Q8_0` quantizations. |
| **Spark Merged HF Weights** | `dgx-spark:/home/ucab-spark1/proyecto/training/output/merged_model/` | 2.9 GB | Consolidated 16-bit safetensors base. |
| **CLI Binary** | `proyecto/bin/clean-copilot` (`~/.local/bin/clean-copilot`) | Executable | Hexagonal TypeScript refactoring client. |
| **Toggle Utility** | `proyecto/bin/toggle-copilot.sh` (`~/toggle-copilot.sh`) | Shell script | Fast toggle for local/remote/cloud switching. |

---

## 2. Power On & Power Off (Fast Switch)

The `toggle-copilot.sh` script manages background model servers and automatically updates VS Code GitHub Copilot configuration.

```bash
# Toggle mode (automatically switches between ON and OFF)
~/toggle-copilot.sh

# Force ON (launches local llama-server on laptop CPU and routes VS Code)
~/toggle-copilot.sh on

# Force OFF (terminates local server and restores official GitHub Copilot Cloud)
~/toggle-copilot.sh off

# Route to Spark cluster (when connected via Ethernet to DGX Spark port 8085)
~/toggle-copilot.sh spark

# Inspect current status of the local server and VS Code proxy
~/toggle-copilot.sh status
```

> [!NOTE]
> When switching modes, reload your VS Code window (`Ctrl+Shift+P` -> `Developer: Reload Window`) to apply changes immediately.

---

## 3. Terminal Usage (Hexagonal CLI)

Refactor code without launching an IDE using the built-in TypeScript CLI:

```bash
# View unified terminal diff (+/-) comparing legacy vs refactored code
clean-copilot refactor path/to/SourceFile.ts --diff

# Write refactored code directly to a destination file
clean-copilot refactor path/to/SourceFile.ts -o path/to/RefactoredFile.ts

# Override endpoint URL (defaults to Spark port 8085 or localhost:8085)
clean-copilot refactor path/to/SourceFile.ts --url http://127.0.0.1:8085 --diff

# Test CLI offline using deterministic Mock Inference Engine
clean-copilot refactor path/to/SourceFile.ts --mock --diff
```

---

## 4. How to Share the Model with Others

The model is exported in standard **GGUF format (Q4_K_M)**, which allows anyone to run it on Windows, macOS, or Linux without compiling source code.

### Option A: Direct File Sharing (Pendrive / Cloud Drive)
1. Copy the file `clean-copilot-1.5b-q4_k_m.gguf` (941 MB).
2. Friends can run it immediately on:
   - **LM Studio:** Drag and drop `clean-copilot-1.5b-q4_k_m.gguf` into the application.
   - **Jan.ai / AnythingLLM:** Select "Import GGUF model".
   - **llama.cpp CLI:**
     ```bash
     llama-cli -m clean-copilot-1.5b-q4_k_m.gguf -p "<|im_start|>user\nRefactor this class to Clean Architecture:<|im_end|>\n<|im_start|>assistant\n"
     ```

### Option B: Sharing via Ollama
Create a `Modelfile` next to the GGUF file:

```dockerfile
FROM ./clean-copilot-1.5b-q4_k_m.gguf

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>"""

PARAMETER temperature 0.1
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"
```

Then create and run the model in Ollama:
```bash
ollama create clean-copilot -f Modelfile
ollama run clean-copilot "Refactor this UserService to Clean Architecture"
```

### Option C: Upload to Hugging Face Hub
To publish the model for global public download:

```bash
# 1. Login to Hugging Face
huggingface-cli login

# 2. Upload quantized GGUF
huggingface-cli upload <your-username>/edge-clean-copilot-1.5b-GGUF \
  proyecto/models/clean-copilot-1.5b-q4_k_m.gguf \
  clean-copilot-1.5b-q4_k_m.gguf
```

---

## 5. OpenAI-Compatible HTTP API

When the server is active (`http://127.0.0.1:8085` or `http://192.168.6.35:8085`), it exposes standard OpenAI endpoints for integration into third-party tools (Continue, OpenCode, Cursor, Python scripts):

```bash
curl http://127.0.0.1:8085/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "clean-copilot",
    "messages": [
      {
        "role": "system",
        "content": "You are Edge Clean Copilot. Enforce Clean Architecture, Domain Entities, Ports, and zero-any."
      },
      {
        "role": "user",
        "content": "Refactor this service: class OrderService { save() { db.execute(); } }"
      }
    ],
    "temperature": 0.1,
    "max_tokens": 1024
  }'
```
