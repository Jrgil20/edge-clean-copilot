#!/usr/bin/env bash
# ==============================================================================
# Edge Clean Copilot — Switch Rápido de Encendido / Apagado (Laptop)
#
# Uso:
#   ./toggle-copilot.sh         -> Alterna automáticamente (Toggle ON <-> OFF)
#   ./toggle-copilot.sh on      -> Enciende modelo local y conecta VS Code
#   ./toggle-copilot.sh off     -> Apaga modelo local y restaura Copilot Cloud
#   ./toggle-copilot.sh spark   -> Conecta VS Code al modelo en la DGX Spark (8085)
#   ./toggle-copilot.sh status  -> Muestra estado actual del servidor y VS Code
# ==============================================================================

set -eo pipefail

MODEL_PATH="/home/jr_g/Develop/IA_Aplicada/proyecto/models/clean-copilot-1.5b-q4_k_m.gguf"
PID_FILE="$HOME/.local/share/clean-copilot-server.pid"
LOG_FILE="$HOME/.local/share/clean-copilot-server.log"
SETTINGS_FILE="$HOME/.config/Code/User/settings.json"
PORT=8085

# Colores para salida limpia
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        fi
        rm -f "$PID_FILE"
    fi
    # Verificación secundaria por puerto
    local port_pid
    port_pid=$(ss -tlpn 2>/dev/null | grep ":$PORT " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -n1 || true)
    if [[ -n "$port_pid" ]]; then
        echo "$port_pid"
        return 0
    fi
    return 1
}

start_local() {
    local pid
    if pid=$(is_running); then
        echo -e "${YELLOW}⚡ El servidor local ya está corriendo (PID: ${pid}) en http://127.0.0.1:${PORT}${NC}"
    else
        if [[ ! -f "$MODEL_PATH" ]]; then
            echo -e "${RED}❌ Error: No se encontró el modelo en: ${MODEL_PATH}${NC}"
            exit 1
        fi

        mkdir -p "$(dirname "$PID_FILE")"
        echo -e "${CYAN}🚀 Iniciando modelo local en la CPU de la laptop...${NC}"
        
        nohup llama-server \
            -m "$MODEL_PATH" \
            --port "$PORT" \
            --host 127.0.0.1 \
            --alias clean-copilot,edge-clean-copilot-q4_k_m \
            -c 4096 \
            --jinja > "$LOG_FILE" 2>&1 &
        
        local new_pid=$!
        echo "$new_pid" > "$PID_FILE"
        sleep 2
        echo -e "${GREEN}✅ Servidor local encendido (PID: ${new_pid}) en http://127.0.0.1:${PORT}${NC}"
    fi

    # Configurar VS Code para usar local
    copilot-local on local > /dev/null 2>&1 || true
    echo -e "${GREEN}🔗 VS Code GitHub Copilot conectado a: http://127.0.0.1:${PORT} (100% Offline)${NC}"
    echo -e "${BOLD}💡 Tip: Recargá la ventana de VS Code (Ctrl+Shift+P -> 'Developer: Reload Window') si lo tenés abierto.${NC}"
}

stop_local() {
    local pid
    if pid=$(is_running); then
        echo -e "${YELLOW}🛑 Deteniendo servidor local (PID: ${pid})...${NC}"
        kill "$pid" 2>/dev/null || true
        sleep 1
        rm -f "$PID_FILE"
        echo -e "${RED}🔴 Servidor local apagado.${NC}"
    else
        echo -e "${YELLOW}ℹ️  El servidor local no estaba corriendo.${NC}"
    fi

    # Restaurar VS Code a Cloud
    copilot-local off > /dev/null 2>&1 || true
    echo -e "${CYAN}☁️  VS Code GitHub Copilot restaurado a: GitHub Cloud Oficial${NC}"
    echo -e "${BOLD}💡 Tip: Recargá la ventana de VS Code para aplicar el cambio.${NC}"
}

connect_spark() {
    copilot-local on > /dev/null 2>&1 || true
    echo -e "${CYAN}⚡ VS Code GitHub Copilot conectado a NVIDIA DGX Spark: http://192.168.6.35:${PORT}${NC}"
    echo -e "${BOLD}💡 Tip: Recargá la ventana de VS Code para aplicar el cambio.${NC}"
}

show_status() {
    echo -e "${BOLD}======================================================${NC}"
    echo -e "${BOLD}  Estado de Edge Clean Copilot en la Laptop           ${NC}"
    echo -e "${BOLD}======================================================${NC}"
    local pid
    if pid=$(is_running); then
        echo -e "  Servidor CPU Local : ${GREEN}🟢 ACTIVO${NC} (PID: ${pid}, Puerto: ${PORT})"
    else
        echo -e "  Servidor CPU Local : ${RED}⚪ APAGADO${NC}"
    fi
    echo -e "  Archivo de Modelo  : ${CYAN}${MODEL_PATH}${NC}"
    echo -e "------------------------------------------------------"
    copilot-local status | grep -E "Routing|Status|Endpoint|Target" || true
    echo -e "${BOLD}======================================================${NC}"
}

# Lógica del Toggle
ACTION="${1:-toggle}"

case "$ACTION" in
    on|start)
        start_local
        ;;
    off|stop)
        stop_local
        ;;
    spark)
        connect_spark
        ;;
    status)
        show_status
        ;;
    toggle)
        if is_running >/dev/null; then
            stop_local
        else
            start_local
        fi
        ;;
    *)
        echo "Uso: $0 [on|off|toggle|spark|status]"
        exit 1
        ;;
esac
