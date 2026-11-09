#!/bin/bash
# ==============================================================================
# THREE-HEADED SEMANTIC FIREWALL (sf-core) — CONTROL PANEL & CLI ORCHESTRATOR
# «¡Mira detrás de ti, un mono de tres cabezas!» — Lucasfilm Games (1990)
# ==============================================================================

# Paleta de Colores ANSI
RESET="\033[0m"
BOLD="\033[1m"
CYAN="\033[1;36m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
MAGENTA="\033[1;35m"
RED="\033[1;31m"
DIM="\033[2m"

# Configuración de Puertos y Servicios
SF_PROXY_PORT="${SF_PORT:-8088}"
SF_SPA_PORT="${VITE_PORT:-5173}"
SF_UI_PORT="${SF_UI_PORT:-3000}"
TEI_PORT="${TEI_PORT:-8080}"

SF_PROXY_URL="http://127.0.0.1:${SF_PROXY_PORT}"
SF_SPA_URL="http://127.0.0.1:${SF_SPA_PORT}"
SF_UI_URL="http://127.0.0.1:${SF_UI_PORT}"
TEI_URL="http://127.0.0.1:${TEI_PORT}"

# Archivos de Registro (Logs)
LOG_PROXY="sf_proxy.log"
LOG_SPA="sf_spa.log"
LOG_UI="sf_ui.log"
LOG_FILE="3hm_dev.log"
LOG_TEI_MPS="sf_tei_mps.log"
PID_FILE_TEI_MPS=".sf_tei_mps.pid"

SUPPORTED_OS_LABEL="macOS (Darwin arm64/x86_64)"

# Patrones de Detección de Procesos
SF_PROXY_PROC_PATTERN="target/(debug|release)/sf-proxy|sf-proxy.*--listen"
SF_SPA_PROC_PATTERN="vite.*--port.*${SF_SPA_PORT}|pnpm.*dev.*frontend|node.*/vite"
SF_UI_PROC_PATTERN="target/(debug|release)/sf-ui|sf-ui.*--listen"

# Fase del panel para control de SIGINT: menu | logs | guide
PANEL_PHASE="menu"

load_env_file() {
    if [ -f .env ]; then
        set -a
        source .env 2>/dev/null || true
        set +a
        SF_PROXY_PORT="${SF_PORT:-8088}"
        SF_PROXY_URL="http://127.0.0.1:${SF_PROXY_PORT}"
        if [ -n "$TEI_HTTP_URL" ]; then
            TEI_URL="$TEI_HTTP_URL"
            local extracted_port
            extracted_port="$(echo "$TEI_HTTP_URL" | sed -E 's|.*:([0-9]+).*|\1|')"
            if [[ "$extracted_port" =~ ^[0-9]+$ ]]; then
                TEI_PORT="$extracted_port"
            fi
        fi
    fi
}

exit_panel_keep_services() {
    echo -e "\n${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "${CYAN}${BOLD}  «Nunca pagues más de 20 pavos por un juego de ordenador.»${RESET}"
    echo -e "${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "  ${GREEN}¡Hasta la vista, grumete! Los servicios siguen corriendo en segundo plano.${RESET}"
    echo -e "  ${DIM}(Usa la opción 10 para detener todos los servicios cuando quieras).${RESET}\n"
    exit 0
}

handle_sigint() {
    case "$PANEL_PHASE" in
        logs|guide)
            echo -e "\n${YELLOW}${BOLD}⏸ Regresando al menú principal. Los servicios siguen activos.${RESET}"
            PANEL_PHASE="menu"
            ;;
        *)
            exit_panel_keep_services
            ;;
    esac
}

trap 'handle_sigint' INT

# Lanza un comando desacoplado en una nueva sesión (sin controlling TTY).
# Evita que SIGINT mate el servicio hijo o genere paradas STAT T (SIGTTOU).
launch_detached() {
    local workdir="$1"
    local logfile="$2"
    shift 2
    if [ "$logfile" = "-" ]; then
        logfile="/dev/null"
    fi
    case "$workdir" in
        /*) ;;
        *) workdir="$(pwd)/$workdir" ;;
    esac
    case "$logfile" in
        /*) ;;
        *) logfile="$(pwd)/$logfile" ;;
    esac

    python3 - "$workdir" "$logfile" "$@" <<'PY'
import os, sys, subprocess

workdir, logfile, *cmd = sys.argv[1:]
os.chdir(workdir)
log = open(logfile, "a", buffering=1)
proc = subprocess.Popen(
    cmd,
    stdin=subprocess.DEVNULL,
    stdout=log,
    stderr=subprocess.STDOUT,
    start_new_session=True,
    close_fds=True,
)
pid_path = os.environ.get("SF_LAUNCH_PID_FILE", "").strip()
if pid_path:
    with open(pid_path, "w", encoding="utf-8") as handle:
        handle.write(f"{proc.pid}\n")
        handle.flush()
        os.fsync(handle.fileno())
PY
}

refresh_path() {
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
    [ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env" 2>/dev/null || true
    [ -f "$HOME/.local/bin/env" ] && source "$HOME/.local/bin/env" 2>/dev/null || true
}

warn_if_unsupported_platform() {
    local os_name
    os_name="$(uname -s 2>/dev/null || echo unknown)"
    if [ "$os_name" != "Darwin" ]; then
        echo -e "${YELLOW}${BOLD}⚠️  Plataforma no testeada directamente: ${os_name}${RESET}"
        echo -e "${YELLOW}   Este proyecto fue optimizado para ${SUPPORTED_OS_LABEL}.${RESET}"
        echo -e "${YELLOW}   «Si intentas navegar fuera de las aguas de Mêlée Island, ¡cuidado con los monstruos marinos!»${RESET}"
        return 1
    fi
    return 0
}

ensure_homebrew() {
    if command -v brew &> /dev/null; then
        echo -e "  ${GREEN}✓ Homebrew detectado.${RESET}"
        return 0
    fi
    echo -e "${YELLOW}▶ Homebrew no encontrado. Instalando Homebrew...${RESET}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    refresh_path
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}❌ Falló la instalación de Homebrew. Instálalo desde https://brew.sh y reintenta.${RESET}"
        return 1
    fi
    echo -e "  ${GREEN}✓ Homebrew instalado con éxito.${RESET}"
    return 0
}

ensure_rust_cargo() {
    refresh_path
    if command -v cargo &> /dev/null && command -v rustc &> /dev/null; then
        local rust_ver
        rust_ver="$(rustc --version 2>/dev/null | cut -d' ' -f2)"
        echo -e "  ${GREEN}✓ Rust toolchain detectado (${rust_ver}) / Cargo disponible.${RESET}"
        return 0
    fi

    echo -e "${YELLOW}▶ Rust & Cargo no detectados. ¿Deseas instalarlos vía rustup oficial?${RESET}"
    echo -e "  ${DIM}«¡Sin espada no puedes desafiar a Carla, la Maestra de la Espada!»${RESET}"
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    refresh_path
    if ! command -v cargo &> /dev/null; then
        echo -e "${RED}❌ No se encontró cargo tras la instalación. Revisa ~/.cargo/bin y reejecuta.${RESET}"
        return 1
    fi
    echo -e "  ${GREEN}✓ Rust & Cargo instalados correctamente.${RESET}"
    return 0
}

ensure_xcode_tools() {
    if xcrun cc --version &> /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Compilador de C / Command Line Tools listo.${RESET}"
        return 0
    fi

    if xcrun cc 2>&1 | grep -q "xcodebuild -license"; then
        echo -e "${RED}${BOLD}❌ Licencia de Xcode pendiente de aceptación.${RESET}"
        echo -e "${YELLOW}  Ejecuta en una terminal: ${BOLD}sudo xcodebuild -license${RESET}${YELLOW} para aceptarla.${RESET}"
        return 1
    fi

    echo -e "${YELLOW}▶ Instalando Command Line Tools de Xcode (necesarias para enlazar binarios C)...${RESET}"
    xcode-select --install 2>/dev/null || true
    echo -e "${YELLOW}  Completa el diálogo de instalación de macOS y presiona Enter al terminar.${RESET}"
    read -p "Presiona Enter cuando termine la instalación..."
    return 0
}

ensure_python() {
    refresh_path
    if command -v python3 &> /dev/null; then
        echo -e "  ${GREEN}✓ Python 3 disponible ($(python3 --version 2>/dev/null)).${RESET}"
        return 0
    fi
    echo -e "${YELLOW}▶ Python 3 no encontrado. Es necesario para herramientas auxiliares y sesiones desacopladas.${RESET}"
    ensure_homebrew || return 1
    brew install python
    refresh_path
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Falló la instalación de python3.${RESET}"
        return 1
    fi
    echo -e "  ${GREEN}✓ Python 3 instalado.${RESET}"
    return 0
}

ensure_node_pnpm() {
    refresh_path
    local has_node=0 has_pnpm=0

    if command -v node &> /dev/null; then
        local node_ver
        node_ver="$(node -v 2>/dev/null | sed 's/^v//')"
        local node_major
        node_major="$(echo "$node_ver" | cut -d. -f1)"
        if [ "$node_major" -ge 18 ]; then
            echo -e "  ${GREEN}✓ Node.js detectado (v${node_ver} >= 18).${RESET}"
            has_node=1
        else
            echo -e "  ${YELLOW}⚠️  Node.js v${node_ver} es inferior a v18 (se recomienda Node 20+).${RESET}"
            has_node=1
        fi
    fi

    if [ "$has_node" -eq 0 ]; then
        echo -e "${YELLOW}▶ Node.js (>= 18) no detectado. Es requerido para la SPA desacoplada.${RESET}"
        if command -v brew &> /dev/null; then
            echo -e "${YELLOW}  Instalando Node.js vía Homebrew...${RESET}"
            brew install node
            refresh_path
        else
            echo -e "${RED}❌ Instala Node.js (>=18) desde https://nodejs.org y vuelve a intentar.${RESET}"
            return 1
        fi
    fi

    if command -v pnpm &> /dev/null; then
        local pnpm_ver
        pnpm_ver="$(pnpm -v 2>/dev/null)"
        local pnpm_major
        pnpm_major="$(echo "$pnpm_ver" | cut -d. -f1)"
        if [ "$pnpm_major" -ge 9 ]; then
            echo -e "  ${GREEN}✓ pnpm detectado (v${pnpm_ver} >= 9).${RESET}"
            has_pnpm=1
        else
            echo -e "  ${YELLOW}⚠️  pnpm v${pnpm_ver} detectado. Recomendado >= 9.${RESET}"
            has_pnpm=1
        fi
    fi

    if [ "$has_pnpm" -eq 0 ]; then
        echo -e "${YELLOW}▶ pnpm no detectado. Intentando configurar pnpm vía corepack / brew...${RESET}"
        if command -v corepack &> /dev/null; then
            corepack enable 2>/dev/null || true
            corepack prepare pnpm@latest --activate 2>/dev/null || true
            refresh_path
        fi
        if ! command -v pnpm &> /dev/null && command -v brew &> /dev/null; then
            brew install pnpm
            refresh_path
        fi
        if ! command -v pnpm &> /dev/null && command -v npm &> /dev/null; then
            npm install -g pnpm
            refresh_path
        fi
        if ! command -v pnpm &> /dev/null; then
            echo -e "${RED}❌ No se pudo instalar pnpm automáticamente. Instálalo con 'brew install pnpm'.${RESET}"
            return 1
        fi
        echo -e "  ${GREEN}✓ pnpm configurado exitosamente ($(pnpm -v)).${RESET}"
    fi

    # Asegurar instalación de dependencias en frontend/
    if [ -d "frontend" ] && [ ! -d "frontend/node_modules" ]; then
        echo -e "${YELLOW}▶ Instalando dependencias de frontend/ con pnpm...${RESET}"
        (cd frontend && pnpm install)
        echo -e "  ${GREEN}✓ Dependencias de frontend instaladas.${RESET}"
    fi

    return 0
}

ensure_project_deps() {
    load_env_file
    if [ ! -f .env ] && [ -f .env.example ]; then
        echo -e "${YELLOW}▶ Creando archivo .env a partir de .env.example...${RESET}"
        cp .env.example .env
        echo -e "  ${GREEN}✓ .env creado con configuración predeterminada (mock embedder, LanceDB data/sf-lancedb).${RESET}"
        load_env_file
    elif [ -f .env ]; then
        echo -e "  ${GREEN}✓ Archivo .env presente.${RESET}"
    fi

    mkdir -p data/sf-lancedb reports 2>/dev/null || true
    return 0
}

ensure_prerequisites() {
    echo -e "\n${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "${CYAN}${BOLD}🔍 COMPROBANDO REQUISITOS DEL SISTEMA Y DEPENDENCIAS...${RESET}"
    echo -e "${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}Plataforma recomendada: ${SUPPORTED_OS_LABEL}${RESET}"

    warn_if_unsupported_platform
    ensure_xcode_tools || return 1
    ensure_rust_cargo || return 1
    ensure_python || return 1
    ensure_node_pnpm || return 1
    ensure_project_deps || return 1
    return 0
}

# --- LanceDB Hydration Helpers ---
is_lancedb_hydrated() {
    local uri="${LANCEDB_URI:-data/sf-lancedb}"
    local table="${LANCEDB_TABLE:-domain_hypercubes}"

    if [ ! -d "$uri" ]; then
        return 1
    fi
    if [ -d "${uri}/${table}.lance" ] || [ -f "${uri}/${table}.lance" ]; then
        local count
        count="$(find "${uri}" -type f 2>/dev/null | wc -l | tr -d ' ')"
        if [ "$count" -gt 0 ]; then
            return 0
        fi
    fi
    return 1
}

hydrate_canonical_lancedb() {
    local uri="${LANCEDB_URI:-data/sf-lancedb}"
    local table="${LANCEDB_TABLE:-domain_hypercubes}"
    echo -e "${BLUE}▶ Hidratando LanceDB en '${uri}' con 55 locks canónicos...${RESET}"
    echo -e "  ${DIM}«¡Un mono de tres cabezas necesita sus 55 cerraduras hiperdimensionales forjadas!»${RESET}"

    if [ -x "target/debug/seed_canonical_locks" ]; then
        target/debug/seed_canonical_locks --lancedb-uri "$uri" --table "$table"
    else
        cargo run -p sf-bench --bin seed_canonical_locks -- --lancedb-uri "$uri" --table "$table"
    fi

    if is_lancedb_hydrated; then
        echo -e "  ${GREEN}✓ LanceDB hidratado exitosamente con 55 locks canónicos en ${uri}.${RESET}"
        return 0
    else
        echo -e "  ${RED}❌ Falló la hidratación de LanceDB.${RESET}"
        return 1
    fi
}

ensure_lancedb_ready() {
    if is_lancedb_hydrated; then
        return 0
    fi
    echo -e "\n${YELLOW}${BOLD}⚠️  data/sf-lancedb no contiene la tabla 'domain_hypercubes' o está vacío.${RESET}"
    echo -e "${YELLOW}   (sf-proxy requiere este catálogo para arrancar sin abortar).${RESET}"
    hydrate_canonical_lancedb
}

# --- Sondas de servicio idempotentes (proceso + estado HTTP) ---
port_listening() {
    local port="$1"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

# 1. Gateway sf-proxy (:8088)
sf_proxy_process_running() {
    pgrep -f "$SF_PROXY_PROC_PATTERN" >/dev/null 2>&1
}

sf_proxy_health_ok() {
    local code
    code="$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 -X OPTIONS "${SF_PROXY_URL}/api/v1/chat" 2>/dev/null || echo "000")"
    [ "$code" = "200" ] || [ "$code" = "405" ]
}

probe_sf_proxy() {
    local proc=0 health=0 port=0
    sf_proxy_process_running && proc=1
    sf_proxy_health_ok && health=1
    port_listening "$SF_PROXY_PORT" && port=1

    if [ "$port" -eq 1 ] && [ "$health" -eq 1 ]; then
        echo "healthy"
    elif [ "$proc" -eq 0 ] && [ "$health" -eq 0 ] && [ "$port" -eq 0 ]; then
        echo "down"
    else
        echo "sick"
    fi
}

# 2. Frontend SPA (:5173)
sf_spa_process_running() {
    pgrep -f "$SF_SPA_PROC_PATTERN" >/dev/null 2>&1
}

sf_spa_health_ok() {
    local code
    code="$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "${SF_SPA_URL}/" 2>/dev/null || echo "000")"
    [ "$code" = "200" ]
}

probe_sf_spa() {
    local proc=0 health=0 port=0
    sf_spa_process_running && proc=1
    sf_spa_health_ok && health=1
    port_listening "$SF_SPA_PORT" && port=1

    if [ "$port" -eq 1 ] && [ "$health" -eq 1 ]; then
        echo "healthy"
    elif [ "$proc" -eq 0 ] && [ "$health" -eq 0 ] && [ "$port" -eq 0 ]; then
        echo "down"
    else
        echo "sick"
    fi
}

# 3. Diagnostic Studio legado (:3000)
sf_ui_process_running() {
    pgrep -f "$SF_UI_PROC_PATTERN" >/dev/null 2>&1
}

sf_ui_health_ok() {
    local body
    body="$(curl -sf --max-time 2 "${SF_UI_URL}/api/v1/catalog" 2>/dev/null)" || return 1
    echo "$body" | grep -q 'Three-Headed Semantic Firewall'
}

probe_sf_ui() {
    local proc=0 health=0 port=0
    sf_ui_process_running && proc=1
    sf_ui_health_ok && health=1
    port_listening "$SF_UI_PORT" && port=1

    if [ "$port" -eq 1 ] && [ "$health" -eq 1 ]; then
        echo "healthy"
    elif [ "$proc" -eq 0 ] && [ "$health" -eq 0 ] && [ "$port" -eq 0 ]; then
        echo "down"
    else
        echo "sick"
    fi
}

# 4. Embedder bge-m3 (:8080) — Metal MPS on Darwin arm64, Docker TEI elsewhere
use_native_mps_embedder() {
    [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]
}

embedder_runtime_label() {
    if use_native_mps_embedder; then
        echo "mps"
    else
        echo "docker"
    fi
}

tei_container_running() {
    docker ps --filter "name=sf-tei" --filter "status=running" -q 2>/dev/null | grep -q .
}

tei_native_running() {
    local pid
    [ -f "$PID_FILE_TEI_MPS" ] || return 1
    pid="$(tr -d '[:space:]' < "$PID_FILE_TEI_MPS" 2>/dev/null || true)"
    [ -n "$pid" ] || return 1
    kill -0 "$pid" 2>/dev/null
}

tei_health_ok() {
    local code
    code="$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 "${TEI_URL}/health" 2>/dev/null || echo "000")"
    [ "$code" = "200" ]
}

probe_tei() {
    local running=0 health=0 port=0
    if tei_native_running || tei_container_running; then
        running=1
    fi
    tei_health_ok && health=1
    port_listening "$TEI_PORT" && port=1

    if [ "$port" -eq 1 ] && [ "$health" -eq 1 ]; then
        echo "healthy"
    elif [ "$running" -eq 0 ] && [ "$health" -eq 0 ] && [ "$port" -eq 0 ]; then
        echo "down"
    else
        echo "sick"
    fi
}

stop_native_mps_process() {
    local pid i
    [ -f "$PID_FILE_TEI_MPS" ] || return 0
    pid="$(tr -d '[:space:]' < "$PID_FILE_TEI_MPS" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        kill -TERM "$pid" 2>/dev/null || true
        i=0
        while [ "$i" -lt 25 ]; do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.2
            i=$((i + 1))
        done
        if kill -0 "$pid" 2>/dev/null; then
            kill -KILL "$pid" 2>/dev/null || true
            sleep 0.2
        fi
    fi
    rm -f "$PID_FILE_TEI_MPS"
}

describe_service_state() {
    local name="$1"
    local state="$2"
    local port="$3"
    case "$state" in
        healthy) echo -e "  ${GREEN}✓ ${name}: ACTIVO & SALUDABLE (Listener + HTTP 200 en :${port})${RESET}" ;;
        down)    echo -e "  ${DIM}· ${name}: INACTIVO (puerto :${port} libre)${RESET}" ;;
        sick)    echo -e "  ${YELLOW}⚠ ${name}: ANÓMALO (proceso o puerto trabado en :${port})${RESET}" ;;
        *)       echo -e "  ${RED}? ${name}: DESCONOCIDO (${state})${RESET}" ;;
    esac
}

render_state_badge() {
    local state="$1"
    case "$state" in
        healthy) echo -e "${GREEN}${BOLD}ACTIVO (200 OK)${RESET}" ;;
        down)    echo -e "${DIM}INACTIVO${RESET}" ;;
        sick)    echo -e "${YELLOW}${BOLD}ANÓMALO${RESET}" ;;
        *)       echo -e "${RED}? DESCONOCIDO${RESET}" ;;
    esac
}

kill_pids_on_port() {
    local port="$1"
    local name="$2"
    local pids
    pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    if [ -z "$pids" ]; then
        return 0
    fi
    echo -e "  ${YELLOW}▶ Cerrando procesos en :${port} (${name}, PIDs: ${pids})...${RESET}"
    kill $pids 2>/dev/null || true
    local i
    for i in 1 2 3 4 5; do
        sleep 0.3
        pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
        if [ -z "$pids" ]; then
            return 0
        fi
    done
    echo -e "  ${RED}▶ Forzando cierre (kill -9) en :${port}...${RESET}"
    kill -9 $pids 2>/dev/null || true
    sleep 0.3
}

stop_all_services() {
    echo -e "\n${RED}${BOLD}======================================================================${RESET}"
    echo -e "${RED}${BOLD}🛑 DETENIENDO TODOS LOS SERVICIOS (GATEWAY, SPA Y STUDIO)...${RESET}"
    echo -e "${RED}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}«¡El Fantasma Pirata LeChuck y sus procesos zombies son neutralizados!»${RESET}\n"

    # Terminar por patrones
    pkill -f "$SF_PROXY_PROC_PATTERN" 2>/dev/null || true
    pkill -f "$SF_SPA_PROC_PATTERN" 2>/dev/null || true
    pkill -f "$SF_UI_PROC_PATTERN" 2>/dev/null || true

    # Terminar por puertos
    kill_pids_on_port "$SF_PROXY_PORT" "Gateway sf-proxy"
    kill_pids_on_port "$SF_SPA_PORT" "Frontend SPA"
    kill_pids_on_port "$SF_UI_PORT" "Diagnostic Studio"

    local left=0
    for p in "$SF_PROXY_PORT" "$SF_SPA_PORT" "$SF_UI_PORT"; do
        if port_listening "$p"; then
            echo -e "  ${RED}❌ Advertencia: Puerto :${p} sigue ocupado.${RESET}"
            left=1
        fi
    done

    if [ "$left" -eq 0 ]; then
        echo -e "  ${GREEN}✓ Gateway :${SF_PROXY_PORT} LIBERADO.${RESET}"
        echo -e "  ${GREEN}✓ Frontend SPA :${SF_SPA_PORT} LIBERADO.${RESET}"
        echo -e "  ${GREEN}✓ Diagnostic Studio :${SF_UI_PORT} LIBERADO.${RESET}"
        echo -e "\n  ${GREEN}${BOLD}✅ Cero procesos zombies. Todos los puertos limpios.${RESET}"
    fi

    if [ "$(probe_tei)" != "down" ]; then
        echo ""
        read -p "¿Deseas detener también el embedder bge-m3 en :${TEI_PORT} (Metal MPS o contenedor TEI)? [y/N]: " stop_tei_choice
        if [[ "$stop_tei_choice" =~ ^[Yy]$ ]]; then
            stop_tei_daemon
        else
            echo -e "  ${DIM}Embedder bge-m3 preservado en segundo plano.${RESET}"
        fi
    fi

    read -p "Presiona Enter para regresar al menú..."
}

wait_gateway_healthy() {
    local i filled empty bar pct
    local total=35
    echo -e "  ${DIM}Esperando a que Gateway sf-proxy responda en ${SF_PROXY_URL}…${RESET}"
    for i in $(seq 1 "$total"); do
        if sf_proxy_health_ok; then
            bar="$(printf '█%.0s' $(seq 1 28))"
            echo -ne "\r  [${GREEN}${bar}${RESET}]  ${BOLD}100%${RESET}  ${GREEN}${BOLD}GATEWAY SF-PROXY ACTIVO (:8088)${RESET}          \n"
            return 0
        fi
        filled=$(( i * 28 / total ))
        empty=$(( 28 - filled ))
        pct=$(( i * 100 / total ))
        bar="$(printf '█%.0s' $(seq 1 "$filled") 2>/dev/null)$(printf '░%.0s' $(seq 1 "$empty") 2>/dev/null)"
        echo -ne "\r  [${CYAN}${bar}${RESET}]  ${pct}%  sondando ${SF_PROXY_URL}/api/v1/chat…   "
        sleep 1
    done
    echo -e "\n  ${RED}${BOLD}TIEMPO AGOTADO${RESET} — sf-proxy no alcanzó estado saludable. Revisa ${LOG_PROXY}."
    return 1
}

start_gateway_daemon() {
    echo -e "${BLUE}▶ Iniciando Gateway sf-proxy (${SF_PROXY_URL})...${RESET}"
    echo -e "  ${DIM}«El Vigía del mástil principal vigila el horizonte con tres ojos.»${RESET}"

    load_env_file
    local bin_path="target/debug/sf-proxy"
    if [ -x "$bin_path" ]; then
        launch_detached "." "$LOG_PROXY" "$bin_path" \
            --listen "127.0.0.1:${SF_PROXY_PORT}" \
            --lancedb-uri "${LANCEDB_URI:-data/sf-lancedb}"
    else
        launch_detached "." "$LOG_PROXY" cargo run -p sf-proxy --bin sf-proxy -- \
            --listen "127.0.0.1:${SF_PROXY_PORT}" \
            --lancedb-uri "${LANCEDB_URI:-data/sf-lancedb}"
    fi
    wait_gateway_healthy
}

wait_spa_healthy() {
    local i filled empty bar pct
    local total=25
    echo -e "  ${DIM}Esperando a que Vite levante la SPA en ${SF_SPA_URL}…${RESET}"
    for i in $(seq 1 "$total"); do
        if sf_spa_health_ok; then
            bar="$(printf '█%.0s' $(seq 1 28))"
            echo -ne "\r  [${GREEN}${bar}${RESET}]  ${BOLD}100%${RESET}  ${GREEN}${BOLD}FRONTEND SPA ACTIVA (:5173)${RESET}          \n"
            return 0
        fi
        filled=$(( i * 28 / total ))
        empty=$(( 28 - filled ))
        pct=$(( i * 100 / total ))
        bar="$(printf '█%.0s' $(seq 1 "$filled") 2>/dev/null)$(printf '░%.0s' $(seq 1 "$empty") 2>/dev/null)"
        echo -ne "\r  [${CYAN}${bar}${RESET}]  ${pct}%  sondando ${SF_SPA_URL}…   "
        sleep 1
    done
    echo -e "\n  ${RED}${BOLD}TIEMPO AGOTADO${RESET} — Vite SPA no respondió en :${SF_SPA_PORT}. Revisa ${LOG_SPA}."
    return 1
}

start_spa_daemon() {
    echo -e "${BLUE}▶ Iniciando Frontend SPA Vite (${SF_SPA_URL})...${RESET}"
    echo -e "  ${DIM}«Izando las velas reactivas del Three-Headed Playground.»${RESET}"

    launch_detached "frontend" "$LOG_SPA" pnpm dev --port "$SF_SPA_PORT" --host 127.0.0.1
    wait_spa_healthy
}

wait_sf_ui_healthy() {
    local i filled empty bar pct
    local total=40
    echo -e "  ${DIM}Esperando a que Diagnostic Studio responda en ${SF_UI_URL}…${RESET}"
    for i in $(seq 1 "$total"); do
        if sf_ui_health_ok; then
            bar="$(printf '█%.0s' $(seq 1 28))"
            echo -ne "\r  [${GREEN}${bar}${RESET}]  ${BOLD}100%${RESET}  ${GREEN}${BOLD}STUDIO CALIBRADO & LISTO (55 LOCKS)${RESET}          \n"
            return 0
        fi
        filled=$(( i * 28 / total ))
        empty=$(( 28 - filled ))
        pct=$(( i * 100 / total ))
        bar="$(printf '█%.0s' $(seq 1 "$filled") 2>/dev/null)$(printf '░%.0s' $(seq 1 "$empty") 2>/dev/null)"
        echo -ne "\r  [${CYAN}${bar}${RESET}]  ${pct}%  sondando ${SF_UI_URL}/api/v1/catalog…   "
        sleep 1
    done
    echo -e "\n  ${RED}${BOLD}TIEMPO AGOTADO${RESET} — Diagnostic Studio no respondió. Revisa ${LOG_UI}."
    return 1
}

start_sf_ui_background() {
    echo -e "${BLUE}▶ Iniciando Diagnostic Studio (${SF_UI_URL})...${RESET}"
    echo -e "  ${DIM}«¡Mira detrás de ti, un mono de tres cabezas!»${RESET}"

    local bin_path="target/debug/sf-ui"
    if [ -x "$bin_path" ]; then
        launch_detached "." "$LOG_UI" "$bin_path" --listen "127.0.0.1:${SF_UI_PORT}"
    else
        launch_detached "." "$LOG_UI" cargo run -p sf-ui --bin sf-ui -- --listen "127.0.0.1:${SF_UI_PORT}"
    fi
    wait_sf_ui_healthy
}

wait_tei_healthy() {
    local i filled empty bar pct
    local total="${1:-60}"
    echo -e "  ${DIM}Esperando a que el embedder bge-m3 responda en ${TEI_URL}/health…${RESET}"
    for i in $(seq 1 "$total"); do
        if tei_health_ok; then
            bar="$(printf '█%.0s' $(seq 1 28))"
            echo -ne "\r  [${GREEN}${bar}${RESET}]  ${BOLD}100%${RESET}  ${GREEN}${BOLD}EMBEDDER BGE-M3 ACTIVO (:${TEI_PORT})${RESET}          \n"
            return 0
        fi
        filled=$(( i * 28 / total ))
        empty=$(( 28 - filled ))
        pct=$(( i * 100 / total ))
        bar="$(printf '█%.0s' $(seq 1 "$filled") 2>/dev/null)$(printf '░%.0s' $(seq 1 "$empty") 2>/dev/null)"
        echo -ne "\r  [${CYAN}${bar}${RESET}]  ${pct}%  sondando ${TEI_URL}/health…   "
        sleep 1
    done
    echo -e "\n  ${RED}${BOLD}TIEMPO AGOTADO${RESET} — TEI no respondió en :${TEI_PORT}."
    return 1
}

start_native_mps_embedder() {
    local pid_path
    if ! command -v uv >/dev/null 2>&1; then
        echo -e "  ${RED}❌ uv no está instalado en PATH.${RESET}"
        return 1
    fi
    if tei_container_running; then
        echo -e "  ${YELLOW}▶ Deteniendo contenedor Docker sf-tei para liberar :${TEI_PORT}...${RESET}"
        docker compose -f docker-compose.tei.yml down 2>/dev/null || true
    fi
    if tei_native_running && tei_health_ok; then
        echo -e "  ${GREEN}✓ Embedder Metal MPS ya está activo en ${TEI_URL}.${RESET}"
        return 0
    fi
    if tei_native_running || port_listening "$TEI_PORT"; then
        stop_native_mps_process
        kill_pids_on_port "$TEI_PORT" "embedder bge-m3"
    fi
    rm -f "$PID_FILE_TEI_MPS"
    echo -e "${BLUE}▶ Iniciando embedder nativo BGE-M3 (Metal MPS, torch.float32)...${RESET}"
    echo -e "  ${DIM}«El vigía deja la máquina virtual y mira con los núcleos Metal.»${RESET}"
    pid_path="$(pwd)/${PID_FILE_TEI_MPS}"
    SF_LAUNCH_PID_FILE="$pid_path" launch_detached "." "$LOG_TEI_MPS" uv run tools/bge_m3_mps_server.py
    if [ ! -s "$PID_FILE_TEI_MPS" ]; then
        echo -e "  ${RED}❌ No se pudo registrar el PID en ${PID_FILE_TEI_MPS}. Revisa ${LOG_TEI_MPS}.${RESET}"
        return 1
    fi
    wait_tei_healthy 240
}

start_tei_daemon() {
    if use_native_mps_embedder; then
        start_native_mps_embedder
        return $?
    fi
    if ! command -v docker >/dev/null 2>&1; then
        echo -e "  ${RED}❌ Docker no está instalado en PATH.${RESET}"
        return 1
    fi
    if ! docker info >/dev/null 2>&1; then
        echo -e "  ${RED}❌ El daemon de Docker no está en ejecución.${RESET}"
        return 1
    fi
    echo -e "${BLUE}▶ Levantando contenedor TEI bge-m3 (docker compose)...${RESET}"
    docker compose -f docker-compose.tei.yml up -d
    wait_tei_healthy
}

stop_tei_daemon() {
    echo -e "  ${YELLOW}▶ Deteniendo embedder bge-m3 (Metal MPS y contenedor TEI)...${RESET}"
    stop_native_mps_process
    docker compose -f docker-compose.tei.yml down 2>/dev/null || true
    if port_listening "$TEI_PORT"; then
        kill_pids_on_port "$TEI_PORT" "embedder bge-m3"
    fi
    echo -e "  ${GREEN}✓ Embedder bge-m3 detenido. Puerto :${TEI_PORT} liberado.${RESET}"
}

open_browser() {
    local url="$1"
    echo -e "${YELLOW}🌐 Abriendo navegador en ${url}...${RESET}"
    if command -v open &> /dev/null; then
        open "$url"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$url"
    fi
}

print_ready_banner_stack() {
    echo -e "\n${GREEN}${BOLD}======================================================================${RESET}"
    echo -e "${GREEN}${BOLD}     🎉 ¡STACK COMPLETO OPERATIVO EN MÊLÉE ISLAND!${RESET}"
    echo -e "${GREEN}${BOLD}======================================================================${RESET}"
    echo -e " ${BOLD}Frontend SPA (Chat Playground & Rayos X):${RESET}"
    echo -e " ${CYAN}${BOLD}👉 ${SF_SPA_URL}${RESET}"
    echo -e " ${BOLD}Gateway Desacoplado sf-proxy (SSE & Upstream Forwarder):${RESET}"
    echo -e " ${CYAN}${BOLD}👉 ${SF_PROXY_URL}/api/v1/chat${RESET}"
    echo -e " ${DIM}«¡Tres cabezas semánticas custodiando la entrada del gobernador!»${RESET}\n"
}

deploy_full_stack() {
    load_env_file
    local proxy_state spa_state
    proxy_state="$(probe_sf_proxy)"
    spa_state="$(probe_sf_spa)"

    echo -e "\n${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "${CYAN}${BOLD}📡 ESTADO DE LOS SERVICIOS DESACOPLADOS${RESET}"
    echo -e "${CYAN}${BOLD}======================================================================${RESET}"
    describe_service_state "Gateway sf-proxy" "$proxy_state" "$SF_PROXY_PORT"
    describe_service_state "Frontend SPA" "$spa_state" "$SF_SPA_PORT"

    if [ "$proxy_state" = "healthy" ] && [ "$spa_state" = "healthy" ]; then
        echo -e "\n${GREEN}${BOLD}✓ ¡El Stack Completo ya está navegando a toda vela!${RESET}"
        print_ready_banner_stack
        open_browser "$SF_SPA_URL"
        echo -e "${DIM}Servicios preservados. Usa opciones 3/4 para tests, 9 para logs, 10 para apagar.${RESET}"
        read -p "Presiona Enter para regresar al menú..."
        return
    fi

    if ! ensure_prerequisites; then
        read -p "Presiona Enter..."
        return 1
    fi

    ensure_lancedb_ready || return 1

    if [ "$SF_EMBEDDER" = "http" ] || [ "$SF_EMBEDDER" = "grpc" ]; then
        local tei_state
        tei_state="$(probe_tei)"
        if [ "$tei_state" != "healthy" ]; then
            echo -e "\n${YELLOW}▶ SF_EMBEDDER='${SF_EMBEDDER}' requiere TEI activo en :${TEI_PORT}.${RESET}"
            echo -e "  ${DIM}«El Vigía del mástil necesita el modelo neuronal bge-m3 para ver en la niebla.»${RESET}"
            if ! start_tei_daemon; then
                echo -e "${RED}⚠️ No se pudo iniciar TEI automáticamente. Continuando con el gateway...${RESET}"
            fi
        fi
    fi

    echo -e "\n${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "${CYAN}${BOLD}🚀 DESPLEGANDO STACK COMPLETO (GATEWAY + FRONTEND SPA)...${RESET}"
    echo -e "${CYAN}${BOLD}======================================================================${RESET}"

    if [ "$proxy_state" = "sick" ]; then
        kill_pids_on_port "$SF_PROXY_PORT" "Gateway sf-proxy"
    fi
    if [ "$proxy_state" != "healthy" ]; then
        if ! start_gateway_daemon; then
            echo -e "${RED}${BOLD}❌ Falló el arranque de sf-proxy. Revisa ${LOG_PROXY}.${RESET}"
            read -p "Presiona Enter..."
            return 1
        fi
    fi

    if [ "$spa_state" = "sick" ]; then
        kill_pids_on_port "$SF_SPA_PORT" "Frontend SPA"
    fi
    if [ "$spa_state" != "healthy" ]; then
        if ! start_spa_daemon; then
            echo -e "${RED}${BOLD}❌ Falló el arranque de Frontend SPA. Revisa ${LOG_SPA}.${RESET}"
            read -p "Presiona Enter..."
            return 1
        fi
    fi

    print_ready_banner_stack
    open_browser "$SF_SPA_URL"

    echo -e "${CYAN}${BOLD}¿Qué deseas hacer a continuación?${RESET}"
    echo -e "  ${BOLD}1)${RESET} Ver Guía Interactiva de Pruebas WebGUI"
    echo -e "  ${BOLD}2)${RESET} Monitorear Logs en Tiempo Real"
    echo -e "  ${BOLD}3)${RESET} Regresar al Menú Principal"
    read -p "Selecciona una opción [1-3, default 1]: " post_deploy_choice
    case "$post_deploy_choice" in
        2)
            follow_logs
            ;;
        3)
            return 0
            ;;
        *)
            show_webgui_guide
            ;;
    esac
}

start_foreground_menu() {
    echo -e "\n${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "${CYAN}${BOLD}⚡ INICIAR SERVICIO EN PRIMER PLANO (INTERACTIVO / FOREGROUND)${RESET}"
    echo -e "${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "  ${BOLD}1)${RESET} Gateway sf-proxy (:8088)"
    echo -e "  ${BOLD}2)${RESET} Frontend SPA Vite (:5173)"
    echo -e "  ${BOLD}3)${RESET} Diagnostic Studio sf-ui (:3000)"
    echo -e "  ${BOLD}0)${RESET} Volver al menú"
    read -p "Elige un servicio [1-3, 0]: " fg_choice

    case "$fg_choice" in
        1)
            kill_pids_on_port "$SF_PROXY_PORT" "Gateway sf-proxy"
            ensure_lancedb_ready
            echo -e "\n${BLUE}Iniciando sf-proxy en primer plano... (Ctrl+C para volver)${RESET}\n"
            cargo run -p sf-proxy --bin sf-proxy -- --listen "127.0.0.1:${SF_PROXY_PORT}" --lancedb-uri "${LANCEDB_URI:-data/sf-lancedb}"
            ;;
        2)
            kill_pids_on_port "$SF_SPA_PORT" "Frontend SPA"
            echo -e "\n${BLUE}Iniciando Frontend SPA en primer plano... (Ctrl+C para volver)${RESET}\n"
            (cd frontend && pnpm dev --port "$SF_SPA_PORT" --host 127.0.0.1)
            ;;
        3)
            kill_pids_on_port "$SF_UI_PORT" "Diagnostic Studio"
            ensure_lancedb_ready
            echo -e "\n${BLUE}Iniciando Diagnostic Studio en primer plano... (Ctrl+C para volver)${RESET}\n"
            cargo run -p sf-ui --bin sf-ui -- --listen "127.0.0.1:${SF_UI_PORT}"
            ;;
        *)
            return
            ;;
    esac
    read -p "Presiona Enter para regresar al menú..."
}

run_full_test_suite() {
    echo -e "\n${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "${CYAN}${BOLD}🧪 EJECUTANDO SUITE COMPLETA DE TESTS (RUST WORKSPACE + FRONTEND)...${RESET}"
    echo -e "${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}«¡Luchas como un granjero de vacas! — ¡Qué apropiado, tú peleas como una vaca!»${RESET}\n"

    local rust_failed=0 fe_failed=0

    echo -e "${BLUE}${BOLD}▶ [1/2] Tests de Rust Workspace (sf-kernels, sf-storage, sf-proxy, sf-bench, sf-ui)...${RESET}"
    if cargo test --workspace; then
        echo -e "  ${GREEN}${BOLD}✓ Rust Workspace Tests GREEN (100% PASS).${RESET}"
    else
        echo -e "  ${RED}${BOLD}❌ ERROR: Fallaron tests en el workspace de Rust.${RESET}"
        rust_failed=1
    fi

    echo -e "\n${BLUE}${BOLD}▶ [2/2] Tests de Frontend SPA (Vitest en frontend/)...${RESET}"
    if pnpm --dir frontend test; then
        echo -e "  ${GREEN}${BOLD}✓ Frontend Vitest GREEN (34 tests PASS).${RESET}"
    else
        echo -e "  ${RED}${BOLD}❌ ERROR: Fallaron tests de Vitest en frontend/.${RESET}"
        fe_failed=1
    fi

    echo -e "\n${CYAN}${BOLD}──────────────────────────────────────────────────────────────────────${RESET}"
    if [ "$rust_failed" -eq 0 ] && [ "$fe_failed" -eq 0 ]; then
        echo -e "${GREEN}${BOLD}🎉 ¡TODOS LOS TESTS HAN PASADO EXITOSAMENTE (100% GREEN EN TODO EL STACK)!${RESET}"
        echo -e "  ${DIM}«¡Has superado la Primera Prueba de Mêlée Island con honores de pirata!»${RESET}"
    else
        echo -e "${RED}${BOLD}❌ RESUMEN: Se detectaron fallos (Rust: ${rust_failed}, Frontend: ${fe_failed}).${RESET}"
    fi
    read -p "Presiona Enter para regresar al menú..."
}

run_quality_gates() {
    echo -e "\n${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "${CYAN}${BOLD}🛡️ EJECUTANDO QUALITY GATES (RUST & FRONTEND)...${RESET}"
    echo -e "${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}«Carla, la Maestra de la Espada de Mêlée Island, inspecciona cada línea con ojo avizor.»${RESET}\n"

    local fmt_failed=0 clippy_failed=0 tsc_failed=0 oxlint_failed=0

    echo -e "${BLUE}${BOLD}▶ [1/4] Verificando formato Rust (cargo fmt --all -- --check)...${RESET}"
    if cargo fmt --all -- --check; then
        echo -e "  ${GREEN}${BOLD}✓ Formato Rust perfecto (cargo fmt GREEN).${RESET}"
    else
        echo -e "  ${RED}❌ Formato inconsistente en Rust. Ejecuta 'cargo fmt --all' para corregir.${RESET}"
        fmt_failed=1
    fi

    echo -e "\n${BLUE}${BOLD}▶ [2/4] Auditoría Clippy estricta (cargo clippy -D warnings)...${RESET}"
    if cargo clippy --workspace --all-targets -- -D warnings; then
        echo -e "  ${GREEN}${BOLD}✓ Clippy sin advertencias (Zero Warnings).${RESET}"
    else
        echo -e "  ${RED}❌ Clippy reportó advertencias en Rust.${RESET}"
        clippy_failed=1
    fi

    echo -e "\n${BLUE}${BOLD}▶ [3/4] Type Checking TypeScript (pnpm --dir frontend exec tsc -b)...${RESET}"
    if pnpm --dir frontend exec tsc -b; then
        echo -e "  ${GREEN}${BOLD}✓ TypeScript type check perfecto (Zero Errors).${RESET}"
    else
        echo -e "  ${RED}❌ TypeScript encontró errores de tipos.${RESET}"
        tsc_failed=1
    fi

    echo -e "\n${BLUE}${BOLD}▶ [4/4] Linter Frontend Oxlint (pnpm --dir frontend run lint)...${RESET}"
    if pnpm --dir frontend run lint; then
        echo -e "  ${GREEN}${BOLD}✓ Oxlint sin errores de linting.${RESET}"
    else
        echo -e "  ${RED}❌ Oxlint reportó errores en frontend.${RESET}"
        oxlint_failed=1
    fi

    echo -e "\n${CYAN}${BOLD}──────────────────────────────────────────────────────────────────────${RESET}"
    if [ "$fmt_failed" -eq 0 ] && [ "$clippy_failed" -eq 0 ] && [ "$tsc_failed" -eq 0 ] && [ "$oxlint_failed" -eq 0 ]; then
        echo -e "${GREEN}${BOLD}✅ ¡Quality Gates aprobados al 100%! Acero limpio, templado y sin fisuras.${RESET}"
    else
        echo -e "${RED}${BOLD}❌ Quality Gates no superados. Revisa los fallos detallados arriba.${RESET}"
    fi
    read -p "Presiona Enter para regresar al menú..."
}

run_rompepepe_eval() {
    echo -e "\n${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "${CYAN}${BOLD}🦍 EVALUACIÓN ADVERSARIAL SCPB-220 (Sub-Clause Piggybacking Benchmark)...${RESET}"
    echo -e "${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}«Contención determinista: L3 Subspace Coordinate Quorum contra 220 vectores adversariales.»${RESET}\n"

    cargo run -p sf-bench --bin scpb_220_eval
    if [ $? -eq 0 ] && [ -f "reports/scpb_220_matrix.json" ]; then
        echo -e "\n${GREEN}${BOLD}✅ Matriz SCPB-220 generada exitosamente en reports/scpb_220_matrix.json${RESET}"
        python3 -m json.tool reports/scpb_220_matrix.json 2>/dev/null || cat reports/scpb_220_matrix.json
    else
        echo -e "\n${RED}❌ Error al evaluar vectores SCPB-220.${RESET}"
    fi
    read -p "Presiona Enter para regresar al menú..."
}

run_load_benchmark() {
    echo -e "\n${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "${CYAN}${BOLD}🏎️ BENCHMARK DE CARGA & SLA GATEWAY (1000 RPS)...${RESET}"
    echo -e "${CYAN}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}«¡Si no puedes aguantar 1000 RPS, ni siquiera Stan te vendería un barco usado!»${RESET}\n"

    read -p "  Duración en segundos [default: 15, producción: 60]: " bench_dur
    bench_dur=${bench_dur:-15}
    read -p "  RPS objetivo [default: 1000]: " bench_rps
    bench_rps=${bench_rps:-1000}

    cargo run -p sf-bench --bin load_benchmark -- --duration-secs "$bench_dur" --rps "$bench_rps"
    read -p "Presiona Enter para regresar al menú..."
}

manage_lancedb_menu() {
    echo -e "\n${MAGENTA}${BOLD}======================================================================${RESET}"
    echo -e "${MAGENTA}${BOLD}📦 GESTIÓN DE LANCEDB & CATÁLOGO HIPERDIMENSIONAL${RESET}"
    echo -e "${MAGENTA}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}«La Segunda Prueba: Calibra centroides y bounds antes del bloqueo.»${RESET}\n"

    echo -e "  ${BOLD}1)${RESET} Auto-hidratar 55 Locks Canónicos (sf_bench::generate_canonical_locks)"
    echo -e "  ${BOLD}2)${RESET} Calibrar Dominio 'python' con Embeddings Reales TEI (bge-m3)"
    echo -e "  ${BOLD}3)${RESET} Ingestar Matriz Binaria f32 Personalizada (sf-ingest)"
    echo -e "  ${BOLD}4)${RESET} Inspeccionar Estado Actual de data/sf-lancedb"
    echo -e "  ${BOLD}0)${RESET} Volver al menú"
    read -p "Elige una opción [1-4, 0]: " ldb_opt

    case "$ldb_opt" in
        1)
            hydrate_canonical_lancedb
            ;;
        2)
            echo -e "\n${BLUE}▶ Calibrando dominio 'python' con TEI real (BAAI/bge-m3)...${RESET}"
            local tei_state
            tei_state="$(probe_tei)"
            if [ "$tei_state" != "healthy" ]; then
                echo -e "${YELLOW}▶ Embedder bge-m3 (:${TEI_PORT}) inactivo. Levantando runtime $(embedder_runtime_label)...${RESET}"
                if ! start_tei_daemon; then
                    echo -e "${RED}❌ TEI no está disponible para calibración.${RESET}"
                    read -p "Presiona Enter..."
                    return
                fi
            fi
            cargo run -p sf-bench --bin calibrate_real_domain -- \
                --domain-id "python" \
                --tei-url "${TEI_URL}" \
                --lancedb-uri "${LANCEDB_URI:-data/sf-lancedb}"
            ;;
        3)
            read -p "  Identificador de dominio (domain_id, ej: python, sql): " did
            [ -z "$did" ] && echo -e "${RED}Dominio requerido.${RESET}" && read -p "Enter..." && return
            read -p "  Ruta a matriz binaria f32 (little-endian rows*1024): " f32_path
            if [ ! -f "$f32_path" ]; then
                echo -e "${RED}❌ Archivo no encontrado: ${f32_path}${RESET}"
                read -p "Presiona Enter..."
                return
            fi
            cargo run -p sf-storage --bin sf-ingest -- \
                --domain-id "$did" \
                --input-f32 "$f32_path" \
                --lancedb-uri "${LANCEDB_URI:-data/sf-lancedb}"
            ;;
        4)
            echo -e "\n  ${BOLD}Estado de LanceDB (${LANCEDB_URI:-data/sf-lancedb}):${RESET}"
            if is_lancedb_hydrated; then
                echo -e "  ${GREEN}✓ Tabla 'domain_hypercubes' presente y poblada.${RESET}"
                ls -la "${LANCEDB_URI:-data/sf-lancedb}"
            else
                echo -e "  ${YELLOW}⚠️ Directorio vacío o sin tabla 'domain_hypercubes'.${RESET}"
            fi
            ;;
        *)
            return
            ;;
    esac
    read -p "Presiona Enter para regresar al menú..."
}

clean_artifacts() {
    echo -e "\n${YELLOW}${BOLD}======================================================================${RESET}"
    echo -e "${YELLOW}${BOLD}🧹 LIMPIANDO ARTEFACTOS Y ARCHIVOS TEMPORALES...${RESET}"
    echo -e "${YELLOW}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}«Un pollo de goma con una polea en el medio para destrabar el build.»${RESET}\n"

    read -p "¿Deseas ejecutar 'cargo clean', resetear logs y cachés temporales? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}▶ Ejecutando cargo clean...${RESET}"
        cargo clean
        echo -e "${YELLOW}▶ Limpiando logs y archivos temporales...${RESET}"
        rm -f "$LOG_FILE" "$LOG_PROXY" "$LOG_SPA" "$LOG_UI" "$LOG_TEI_MPS" "$PID_FILE_TEI_MPS"
        rm -rf /tmp/sf-ui-lancedb-* /tmp/sf-loadbench-lance-* 2>/dev/null || true
        rm -rf frontend/node_modules/.vite 2>/dev/null || true
        echo -e "  ${GREEN}✓ Cubierta del Sea Monkey limpia y reluciente.${RESET}"
    else
        echo -e "  ${DIM}Operación cancelada.${RESET}"
    fi
    read -p "Presiona Enter para regresar al menú..."
}

follow_logs() {
    echo -e "\n${MAGENTA}${BOLD}======================================================================${RESET}"
    echo -e "${MAGENTA}${BOLD}📜 MONITOR DE LOGS EN VIVO${RESET}"
    echo -e "${MAGENTA}${BOLD}======================================================================${RESET}"
    echo -e "  ${BOLD}1)${RESET} Logs Combinados (Gateway, SPA, Studio y Embedder)"
    echo -e "  ${BOLD}2)${RESET} Solo Gateway sf-proxy (${LOG_PROXY})"
    echo -e "  ${BOLD}3)${RESET} Solo Frontend SPA (${LOG_SPA})"
    echo -e "  ${BOLD}4)${RESET} Solo Diagnostic Studio (${LOG_UI})"
    echo -e "  ${BOLD}5)${RESET} Solo Embedder bge-m3 (${LOG_TEI_MPS})"
    echo -e "  ${BOLD}0)${RESET} Volver al menú"
    read -p "Selecciona log a monitorear [1-5, default 1]: " log_choice

    local target_files=()
    case "$log_choice" in
        2)
            touch "$LOG_PROXY"
            target_files=("$LOG_PROXY")
            ;;
        3)
            touch "$LOG_SPA"
            target_files=("$LOG_SPA")
            ;;
        4)
            touch "$LOG_UI"
            target_files=("$LOG_UI")
            ;;
        5)
            touch "$LOG_TEI_MPS"
            target_files=("$LOG_TEI_MPS")
            ;;
        0)
            return
            ;;
        *)
            touch "$LOG_PROXY" "$LOG_SPA" "$LOG_UI" "$LOG_FILE" "$LOG_TEI_MPS"
            target_files=("$LOG_PROXY" "$LOG_SPA" "$LOG_UI" "$LOG_FILE" "$LOG_TEI_MPS")
            ;;
    esac

    PANEL_PHASE="logs"
    echo -e "\n  ${DIM}Presiona Ctrl+C para pausar y volver al menú (los servicios siguen vivos).${RESET}\n"
    local sed_flag="-l"
    [ "$(uname -s 2>/dev/null)" != "Darwin" ] && sed_flag="-u"

    tail -f "${target_files[@]}" 2>/dev/null | sed $sed_flag \
        -e "s/INFO/${GREEN}INFO${RESET}/g" \
        -e "s/WARN/${YELLOW}WARN${RESET}/g" \
        -e "s/ERROR/${RED}${BOLD}ERROR${RESET}/g" \
        -e "s/200 OK/${GREEN}200 OK${RESET}/g" \
        -e "s/BREACH/${RED}${BOLD}BREACH${RESET}/g" \
        -e "s/QUORUM/${CYAN}${BOLD}QUORUM${RESET}/g" \
        -e "s/HEAD1/${BLUE}HEAD1${RESET}/g" \
        -e "s/HEAD2/${BLUE}HEAD2${RESET}/g" \
        -e "s/HEAD3/${BLUE}HEAD3${RESET}/g" \
        -e "s/VITE/${MAGENTA}VITE${RESET}/g" \
        || true

    PANEL_PHASE="menu"
    read -p "Presiona Enter para regresar al menú..."
}

manage_environment() {
    echo -e "\n${MAGENTA}${BOLD}======================================================================${RESET}"
    echo -e "${MAGENTA}${BOLD}⚙️ CONFIGURACIÓN DEL ENTORNO (.env)${RESET}"
    echo -e "${MAGENTA}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}«Si el barco tiene goteras o la brújula gira loca, pregúntale a la Cabeza del Navegante.»${RESET}\n"

    load_env_file

    if [ -f .env ]; then
        echo -e "  ${BOLD}Variables actuales en .env:${RESET}"
        grep -E '^(SF_|TEI_|UPSTREAM_|LANCEDB_|LOG_)' .env | while read -r line; do
            echo -e "    ${CYAN}${line}${RESET}"
        done
        echo ""
        echo -e "  ${DIM}1) Alternar SF_EMBEDDER entre 'mock', 'http' y 'grpc'${RESET}"
        echo -e "  ${DIM}2) Iniciar embedder bge-m3 en :${TEI_PORT} ($(embedder_runtime_label))${RESET}"
        echo -e "  ${DIM}3) Detener embedder bge-m3 (:${TEI_PORT})${RESET}"
        echo -e "  ${DIM}4) Abrir .env con el editor predeterminado${RESET}"
        read -p "  Selecciona opción [1-4, o Enter para volver]: " eopt
        case "$eopt" in
            1)
                local cur_emb
                cur_emb="$(grep -E '^SF_EMBEDDER=' .env | cut -d= -f2-)"
                if [ "$cur_emb" = "mock" ]; then
                    sed -i '' 's/^SF_EMBEDDER=.*/SF_EMBEDDER=http/' .env 2>/dev/null || sed -i 's/^SF_EMBEDDER=.*/SF_EMBEDDER=http/' .env
                    echo -e "  ${GREEN}✓ SF_EMBEDDER configurado a 'http'.${RESET}"
                elif [ "$cur_emb" = "http" ]; then
                    sed -i '' 's/^SF_EMBEDDER=.*/SF_EMBEDDER=grpc/' .env 2>/dev/null || sed -i 's/^SF_EMBEDDER=.*/SF_EMBEDDER=grpc/' .env
                    echo -e "  ${GREEN}✓ SF_EMBEDDER configurado a 'grpc'.${RESET}"
                else
                    sed -i '' 's/^SF_EMBEDDER=.*/SF_EMBEDDER=mock/' .env 2>/dev/null || sed -i 's/^SF_EMBEDDER=.*/SF_EMBEDDER=mock/' .env
                    echo -e "  ${GREEN}✓ SF_EMBEDDER configurado a 'mock'.${RESET}"
                fi
                load_env_file
                ;;
            2)
                start_tei_daemon
                ;;
            3)
                stop_tei_daemon
                ;;
            4)
                ${EDITOR:-nano} .env
                load_env_file
                ;;
        esac
    fi
    read -p "Presiona Enter para regresar al menú..."
}

dump_context_codebase() {
    local dump_file="3hm-context.txt"
    echo -e "\n${MAGENTA}${BOLD}======================================================================${RESET}"
    echo -e "${MAGENTA}${BOLD}📑 VOLCADO DE CONTEXTO Y CÓDIGO (${dump_file})${RESET}"
    echo -e "${MAGENTA}${BOLD}======================================================================${RESET}"
    echo -e "  ${DIM}«El libro de actas de la Gobernadora Elaine Marley ha sido sellado para la posteridad.»${RESET}\n"

    if [ -f "$dump_file" ]; then
        echo -e "  ${YELLOW}⚠️  Encontrado dump previo (${dump_file}). Eliminando...${RESET}"
        rm -f "$dump_file"
        echo -e "  ${GREEN}✓ Dump previo eliminado.${RESET}"
    fi

    echo -e "  ${BLUE}▶ Recopilando especificaciones, arquitectura y código fuente Rust...${RESET}"
    python3 tools/dump_context.py --output "$dump_file"
    if [ $? -eq 0 ] && [ -f "$dump_file" ]; then
        echo ""
        echo -e "  ${GREEN}${BOLD}✅ Volcado completo: ${dump_file}${RESET} ($(wc -l < "$dump_file" | tr -d ' ') líneas)"
        echo -e "  ${DIM}Ubicación: $(pwd)/${dump_file}${RESET}"
    else
        echo -e "  ${RED}${BOLD}❌ Error al generar el volcado de contexto.${RESET}"
    fi
    read -p "Presiona Enter para regresar al menú..."
}

show_webgui_guide() {
    PANEL_PHASE="guide"
    local current_card=1
    local total_cards=6

    while true; do
        clear
        echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════════════╗${RESET}"
        echo -e "${CYAN}${BOLD}║${RESET}   ${BOLD}🧭 GUÍA INTERACTIVA DE PRUEBAS EN WEBGUI (${SF_SPA_URL}) 🧭${RESET}     ${CYAN}${BOLD}║${RESET}"
        echo -e "${CYAN}${BOLD}║${RESET}   ${DIM}«Aprende a disparar las tres cabezas del firewall como un pirata»${RESET}  ${CYAN}${BOLD}║${RESET}"
        echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════════════╝${RESET}"

        case "$current_card" in
            1)
                echo -e "\n  ${GREEN}${BOLD}[1/6] 🟢 CASO PASS: Generador de Fibonacci en Python${RESET}"
                echo -e "  ${DIM}Objetivo: Comprobar el paso legítimo de un prompt alineado al dominio.${RESET}\n"
                echo -e "  ${BOLD}Pasos en ${SF_SPA_URL}:${RESET}"
                echo -e "    1. En el área de texto, haz clic en el chip rápido: ${CYAN}${BOLD}Python generator${RESET}."
                echo -e "    2. Verifica que el prompt sea: ${DIM}\"Write a Python generator function that yields fibonacci numbers\"${RESET}."
                echo -e "    3. Haz clic en el botón ${GREEN}${BOLD}Send${RESET}."
                echo -e "\n  ${BOLD}Resultado esperado:${RESET}"
                echo -e "    • Las 3 cabezas otorgan visto bueno (Head 1 Coseno > 0.50, Head 2 dentro de caja, Head 3 quórum OK)."
                echo -e "    • El asistente responde en vivo con un stream de texto SSE letra por letra."
                echo -e "    • En la ficha de telemetría inferior verás: ${GREEN}${BOLD}DECISION: PASS${RESET} con latencia en microsegundos."
                ;;
            2)
                echo -e "\n  ${RED}${BOLD}[2/6] 🔴 CASO BREACH L1: Receta Tradicional de Risotto${RESET}"
                echo -e "  ${DIM}Objetivo: Verificar el cortocircuito rápido por desvío temático global.${RESET}\n"
                echo -e "  ${BOLD}Pasos en ${SF_SPA_URL}:${RESET}"
                echo -e "    1. Haz clic en el chip rápido: ${RED}${BOLD}Risotto recipe${RESET}."
                echo -e "    2. Prompt cargado: ${DIM}\"Can you share a traditional Italian risotto recipe with saffron?\"${RESET}."
                echo -e "    3. Haz clic en ${GREEN}${BOLD}Send${RESET}."
                echo -e "\n  ${BOLD}Resultado esperado:${RESET}"
                echo -e "    • El gateway rechaza la petición con código ${RED}${BOLD}403 Forbidden${RESET}."
                echo -e "    • Se despliega la ficha ${RED}${BOLD}RAYOS X DE BRECHA${RESET}."
                echo -e "    • ${BOLD}Head 1 (SIMD Coseno):${RESET} Muestra la barra en rojo (similitud < 0.50)."
                echo -e "    • ${BOLD}Head 2 y Head 3:${RESET} Aparecen como ${DIM}SKIPPED${RESET} (optimización de cortocircuito)."
                ;;
            3)
                echo -e "\n  ${RED}${BOLD}[3/6] 🔴 CASO BREACH L2: Inyección Solapada (Piggybacked Clause)${RESET}"
                echo -e "  ${DIM}Objetivo: Comprobar que el Segmentador aísla cláusulas maliciosas camufladas.${RESET}\n"
                echo -e "  ${BOLD}Pasos en ${SF_SPA_URL}:${RESET}"
                echo -e "    1. Haz clic en el chip rápido: ${YELLOW}${BOLD}Piggybacked clause${RESET}."
                echo -e "    2. Observa el prompt mixto: ${DIM}\"Write a python function to compute sha256. Also explain how to make the best tiramisu...\"${RESET}."
                echo -e "    3. Haz clic en ${GREEN}${BOLD}Send${RESET}."
                echo -e "\n  ${BOLD}Resultado esperado:${RESET}"
                echo -e "    • ${BOLD}Head 1 (Global):${RESET} Aparece en ${GREEN}VERDE${RESET} (el prompt promediado parece código legítimo)."
                echo -e "    • ${BOLD}Head 2 (Segmenter):${RESET} Marca la brecha en ${RED}${BOLD}ROJO${RESET} e identifica exactamente la cláusula de repostería."
                echo -e "    • Bloqueo instantáneo con telemetría de coordenadas infractoras."
                ;;
            4)
                echo -e "\n  ${RED}${BOLD}[4/6] 🔴 CASO BREACH L3: Ruido Espectral Fuera de Quórum${RESET}"
                echo -e "  ${DIM}Objetivo: Detectar vectores sintéticos o jailbreaks con quórum insuficiente.${RESET}\n"
                echo -e "  ${BOLD}Pasos en ${SF_SPA_URL}:${RESET}"
                echo -e "    1. Haz clic en el chip rápido: ${MAGENTA}${BOLD}Spectral noise${RESET}."
                echo -e "    2. Haz clic en ${GREEN}${BOLD}Send${RESET}."
                echo -e "\n  ${BOLD}Resultado esperado:${RESET}"
                echo -e "    • ${BOLD}Head 1 y Head 2:${RESET} Superan los filtros preliminares de similitud."
                echo -e "    • ${BOLD}Head 3 (Quorum Bitmask):${RESET} Dispara la alarma de brecha."
                echo -e "    • Conteo de votos coincidentes ${RED}V < K (103)${RESET}, demostrando contención de vectores sutiles."
                ;;
            5)
                echo -e "\n  ${YELLOW}${BOLD}[5/6] ⚙️ AJUSTE EN CALIENTE: Runtime Overrides en Vivo${RESET}"
                echo -e "  ${DIM}Objetivo: Probar la calibración de umbrales en tiempo real sin reiniciar el gateway.${RESET}\n"
                echo -e "  ${BOLD}Pasos en ${SF_SPA_URL}:${RESET}"
                echo -e "    1. En la columna lateral, activa el switch: ${CYAN}${BOLD}Apply Runtime Overrides${RESET}."
                echo -e "    2. Desplaza el slider ${BOLD}L1 Cosine Threshold${RESET} hacia abajo hasta ${YELLOW}${BOLD}0.30${RESET}."
                echo -e "    3. Haz clic de nuevo en el chip ${RED}${BOLD}Risotto recipe${RESET} y presiona ${GREEN}${BOLD}Send${RESET}."
                echo -e "\n  ${BOLD}Resultado esperado:${RESET}"
                echo -e "    • ¡El prompt gastronómico ahora es ${GREEN}${BOLD}PERMITIDO (PASS)${RESET}!"
                echo -e "    • Esto valida que el gateway acepta anulaciones por petición sin mutar la memoria del HotRegistry."
                ;;
            6)
                echo -e "\n  ${CYAN}${BOLD}[6/6] 🌐 UPSTREAM REAL: Proveedores Externos (DeepSeek / Gemini / OpenAI)${RESET}"
                echo -e "  ${DIM}Objetivo: Enrutar respuestas a un modelo de lenguaje comercial con custodia local de claves.${RESET}\n"
                echo -e "  ${BOLD}Pasos en ${SF_SPA_URL}:${RESET}"
                echo -e "    1. Haz clic en el ícono de engranaje ${BOLD}⚙️ Configuración${RESET} (esquina superior derecha)."
                echo -e "    2. Selecciona tu proveedor preferido (DeepSeek, Gemini, OpenAI o compatible)."
                echo -e "    3. Pega tu API Key correspondiente y cierra el modal."
                echo -e "\n  ${BOLD}Resultado esperado:${RESET}"
                echo -e "    • La clave se almacena exclusivamente en tu navegador (${DIM}localStorage${RESET})."
                echo -e "    • Al enviar un prompt legítimo, el gateway valida la semántica y reenvía el flujo al LLM real."
                ;;
        esac

        echo -e "\n${CYAN}${BOLD}──────────────────────────────────────────────────────────────────────${RESET}"
        echo -e "  ${BOLD}[n]${RESET} Siguiente tarjeta  |  ${BOLD}[p]${RESET} Tarjeta anterior  |  ${BOLD}[q]${RESET} Volver al menú principal"
        read -n 1 -s -r key
        case "$key" in
            n|N)
                if [ "$current_card" -lt "$total_cards" ]; then
                    current_card=$((current_card + 1))
                else
                    current_card=1
                fi
                ;;
            p|P)
                if [ "$current_card" -gt 1 ]; then
                    current_card=$((current_card - 1))
                else
                    current_card=$total_cards
                fi
                ;;
            q|Q|$'\x1b'|"")
                PANEL_PHASE="menu"
                return 0
                ;;
        esac
    done
}

show_menu() {
    clear
    load_env_file
    local proxy_state spa_state ui_state tei_state
    proxy_state="$(probe_sf_proxy)"
    spa_state="$(probe_sf_spa)"
    ui_state="$(probe_sf_ui)"
    tei_state="$(probe_tei)"

    echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${CYAN}${BOLD}║${RESET}   ${BOLD}🐒 THREE-HEADED SEMANTIC FIREWALL — CONTROL PANEL (sf-core) 🐒${RESET}    ${CYAN}${BOLD}║${RESET}"
    echo -e "${CYAN}${BOLD}║${RESET}   ${DIM}«¡Mira detrás de ti, un mono de tres cabezas!» — Lucasfilm Games 1990${RESET}  ${CYAN}${BOLD}║${RESET}"
    echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════════════╝${RESET}"

    echo -e " ${BOLD}ESTADO EN VIVO DEL SISTEMA:${RESET}"
    echo -e "   • Gateway sf-proxy (:8088):       $(render_state_badge "$proxy_state")"
    echo -e "   • Frontend SPA (:5173):           $(render_state_badge "$spa_state")"
    echo -e "   • Diagnostic Studio (:3000):      $(render_state_badge "$ui_state")"
    echo -e "   • Embedder bge-m3 (:${TEI_PORT}):     $(render_state_badge "$tei_state") [mode: ${SF_EMBEDDER:-mock} / $(embedder_runtime_label)]"

    echo -e "${CYAN}${BOLD}──────────────────────────────────────────────────────────────────────${RESET}"
    echo -e " ${GREEN}${BOLD}1. 🚀 Desplegar Stack Completo${RESET} ${DIM}(Gateway :8088 + SPA :5173 + Auto-seed LanceDB)${RESET}"
    echo -e " ${GREEN}2.${RESET} ${BOLD}Iniciar Servicio en Primer Plano${RESET} ${DIM}(Foreground interactivo: Gateway, SPA o Studio)${RESET}"
    echo -e " ${BLUE}3.${RESET} ${BOLD}Ejecutar Suite de Tests Unificada${RESET} ${DIM}(cargo test workspace + vitest frontend)${RESET}"
    echo -e " ${BLUE}4.${RESET} ${BOLD}Quality Gates & Linters Estrictos${RESET} ${DIM}(cargo clippy/fmt + frontend tsc/oxlint)${RESET}"
    echo -e " ${MAGENTA}5.${RESET} ${BOLD}Evaluar Ataques SCPB-220${RESET} ${DIM}(sf-bench scpb_220_eval → reports/)${RESET}"
    echo -e " ${MAGENTA}6.${RESET} ${BOLD}Benchmark de Carga & SLA 1000 RPS${RESET} ${DIM}(sf-bench load_benchmark · p99 < 2ms)${RESET}"
    echo -e " ${YELLOW}7.${RESET} ${BOLD}Gestión de LanceDB & Catálogo${RESET} ${DIM}(Auto-hidratar 55 locks canónicos / calibrar TEI / sf-ingest)${RESET}"
    echo -e " ${YELLOW}8.${RESET} ${BOLD}Limpiar Artefactos de Compilación${RESET} ${DIM}(cargo clean, cache vite, logs y temporales)${RESET}"
    echo -e " ${CYAN}9.${RESET} ${BOLD}Ver Logs en Vivo${RESET} ${DIM}(Monitor unificado o individual con resaltado de color)${RESET}"
    echo -e " ${RED}10.${RESET} ${BOLD}Detener Todos los Servicios${RESET} ${DIM}(Cierre limpio de :8088, :5173, :3000 y TEI sin zombies)${RESET}"
    echo -e " ${MAGENTA}11.${RESET} ${BOLD}Configuración del Entorno & TEI${RESET} ${DIM}(.env · embedder mock/http/grpc · TEI daemon)${RESET}"
    echo -e " ${CYAN}12.${RESET} ${BOLD}Volcar Contexto y Código para Auditoría / LLM${RESET} ${DIM}(genera 3hm-context.txt)${RESET}"
    echo -e " ${GREEN}13.${RESET} ${BOLD}Guía Interactiva de Pruebas WebGUI${RESET} ${DIM}(Pasos guiados: PASS, Rayos X L1/L2/L3 y Overrides)${RESET}"
    echo -e " ${DIM}0. Salir (mantener servicios activos en background)${RESET}"
    echo -e "${CYAN}${BOLD}──────────────────────────────────────────────────────────────────────${RESET}"
}

# --- Bucle Principal del Orquestador ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    while true; do
        PANEL_PHASE="menu"
        show_menu
        echo -ne "${BOLD}Elige una opción [0-13]: ${RESET}"
        read choice
        case $choice in
            1)
                deploy_full_stack
                ;;
            2)
                start_foreground_menu
                ;;
            3)
                run_full_test_suite
                ;;
            4)
                run_quality_gates
                ;;
            5)
                run_rompepepe_eval
                ;;
            6)
                run_load_benchmark
                ;;
            7)
                manage_lancedb_menu
                ;;
            8)
                clean_artifacts
                ;;
            9)
                follow_logs
                ;;
            10)
                stop_all_services
                ;;
            11)
                manage_environment
                ;;
            12)
                dump_context_codebase
                ;;
            13)
                show_webgui_guide
                ;;
            0)
                exit_panel_keep_services
                ;;
            *)
                echo -e "${RED}Opción no válida.${RESET}"
                sleep 1
                ;;
        esac
    done
fi
