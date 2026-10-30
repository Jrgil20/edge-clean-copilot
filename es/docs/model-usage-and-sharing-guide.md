# Guía de Uso, Despliegue y Compartición del Modelo

> **Proyecto:** Edge Clean Copilot (ECC)  
> **Modelo Cuantizado:** `clean-copilot-1.5b-q4_k_m.gguf` (941 MB)  
> **Arquitectura:** Qwen 2.5 Coder 1.5B especializado con LoRA en Clean Architecture  
> **Última actualización:** 29 de octubre de 2026  

---

## 1. Referencia Rápida de Ubicaciones

| Recurso | Ruta / Destino | Tamaño | Descripción |
| :--- | :--- | :---: | :--- |
| **GGUF en tu Laptop (Local)** | `proyecto/models/clean-copilot-1.5b-q4_k_m.gguf` | 941 MB | Modelo edge 100% offline y autocontenido. |
| **GGUFs de Respaldo en Spark** | `dgx-spark:/home/ucab-spark1/proyecto/training/output/gguf/` | 941 MB – 1.6 GB | Versiones `Q4_K_M`, `Q5_K_M` y `Q8_0`. |
| **Pesos Fusionados en Spark** | `dgx-spark:/home/ucab-spark1/proyecto/training/output/merged_model/` | 2.9 GB | Pesos safetensors consolidados en 16-bit. |
| **Binario CLI** | `proyecto/bin/clean-copilot` (`~/.local/bin/clean-copilot`) | Ejecutable | Cliente hexagonal en TypeScript para refactorización. |
| **Switch de Encendido** | `proyecto/bin/toggle-copilot.sh` (`~/toggle-copilot.sh`) | Shell script | Switch rápido para alternar local / Spark / Cloud. |

---

## 2. Encendido y Apagado Rápido

El script `toggle-copilot.sh` gestiona los servidores en segundo plano y actualiza la configuración de GitHub Copilot en VS Code de forma automática:

```bash
# Alternar automáticamente (si está apagado lo prende, si está prendido lo apaga)
~/toggle-copilot.sh

# Forzar encendido local (lanza llama-server en CPU y conecta VS Code a 127.0.0.1:8085)
~/toggle-copilot.sh on

# Forzar apagado (detiene el servidor local y restaura GitHub Copilot a la nube)
~/toggle-copilot.sh off

# Conectar a la Spark (para cuando estés conectado por cable a la DGX Spark, puerto 8085)
~/toggle-copilot.sh spark

# Consultar estado actual del servidor y de VS Code
~/toggle-copilot.sh status
```

> [!NOTE]
> Al cambiar de modo, recargá la ventana de VS Code (`Ctrl+Shift+P` -> `Developer: Reload Window`) para aplicar el cambio inmediatamente.

---

## 3. Uso en Terminal (CLI Hexagonal)

Refactorizá código sin necesidad de abrir un entorno visual:

```bash
# Ver diff unificado (+/-) en la consola comparando el código original vs limpio
clean-copilot refactor ruta/a/SourceFile.ts --diff

# Guardar el código refactorizado directamente en un archivo destino
clean-copilot refactor ruta/a/SourceFile.ts -o ruta/a/RefactoredFile.ts

# Forzar endpoint específico
clean-copilot refactor ruta/a/SourceFile.ts --url http://127.0.0.1:8085 --diff

# Probar el CLI en modo mock determinista offline
clean-copilot refactor ruta/a/SourceFile.ts --mock --diff
```

---

## 4. Cómo Compartir el Modelo con Amigos

El modelo está empaquetado en formato estándar **GGUF (Q4_K_M)**, lo que permite ejecutarlo en Windows, Mac o Linux sin compilar código:

### Opción A: Pasar el archivo directo (Pendrive o Google Drive)
1. Compartí el archivo `clean-copilot-1.5b-q4_k_m.gguf` (941 MB).
2. Tus amigos pueden cargarlo en:
   - **LM Studio:** Arrastrar el archivo `.gguf` dentro de la interfaz gráfica.
   - **Jan.ai o AnythingLLM:** Elegir "Importar modelo GGUF".
   - **Consola con llama.cpp:**
     ```bash
     llama-cli -m clean-copilot-1.5b-q4_k_m.gguf -p "<|im_start|>user\nRefactor this class to Clean Architecture:<|im_end|>\n<|im_start|>assistant\n"
     ```

### Opción B: Compartir para Ollama
Crear un archivo llamado `Modelfile` en la misma carpeta:

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

Luego ejecutar:
```bash
ollama create clean-copilot -f Modelfile
ollama run clean-copilot "Refactoriza este UserService a Clean Architecture"
```

### Opción C: Subirlo a Hugging Face Hub
Para compartirlo públicamente para descarga global:

```bash
# 1. Login en Hugging Face
huggingface-cli login

# 2. Subir el binario cuantizado
huggingface-cli upload <tu-usuario>/edge-clean-copilot-1.5b-GGUF \
  proyecto/models/clean-copilot-1.5b-q4_k_m.gguf \
  clean-copilot-1.5b-q4_k_m.gguf
```

---

## 5. API HTTP Compatible con OpenAI

Cuando el servidor está activo (`http://127.0.0.1:8085`), expone endpoints estándar de OpenAI compatibles con cualquier herramienta externa (Continue, Cursor, Python scripts):

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
