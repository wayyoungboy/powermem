#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

powermem_data_dir() {
  if [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
    printf '%s\n' "$CLAUDE_PLUGIN_DATA"
  else
    printf '%s\n' "$HOME/.claude/plugins/data/memory-powermem-powermem"
  fi
}

DATA_DIR=$(powermem_data_dir)
ENV_FILE="$DATA_DIR/.env"
RUNTIME_FILE="$DATA_DIR/runtime.env"
PID_FILE="$DATA_DIR/server.pid"
LOG_FILE="$DATA_DIR/powermem-server.log"
VENV_DIR="$DATA_DIR/venv"

mkdir -p "$DATA_DIR"

runtime_base_url() {
  if [ -n "${POWERMEM_BASE_URL:-}" ]; then
    printf '%s\n' "$POWERMEM_BASE_URL"
    return
  fi
  if [ -f "$RUNTIME_FILE" ]; then
    # shellcheck disable=SC1090
    . "$RUNTIME_FILE"
    if [ -n "${POWERMEM_BASE_URL:-}" ]; then
      printf '%s\n' "$POWERMEM_BASE_URL"
      return
    fi
  fi
  printf '%s\n' "http://localhost:8848"
}

write_runtime_base_url() {
  base_url=$1
  tmp="$RUNTIME_FILE.tmp"
  {
    printf 'POWERMEM_BASE_URL=%s\n' "$base_url"
    printf 'POWERMEM_ENV_FILE=%s\n' "$ENV_FILE"
  } > "$tmp"
  mv "$tmp" "$RUNTIME_FILE"
}

health_url() {
  base_url=$(printf '%s' "$1" | sed 's:/*$::')
  printf '%s/api/v1/system/health\n' "$base_url"
}

is_healthy() {
  url=$(health_url "$1")
  curl -fsS -m 5 "$url" 2>/dev/null | grep -q '"healthy"'
}

pid_alive() {
  [ -f "$PID_FILE" ] || return 1
  pid=$(cat "$PID_FILE" 2>/dev/null || true)
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null
}

venv_python() {
  printf '%s/bin/python\n' "$VENV_DIR"
}

venv_powermem_server() {
  printf '%s/bin/powermem-server\n' "$VENV_DIR"
}

port_free() {
  python3 - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
sock = socket.socket()
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
}

find_free_port() {
  start=${1:-8848}
  end=${2:-8899}
  port=$start
  while [ "$port" -le "$end" ]; do
    if port_free "$port"; then
      printf '%s\n' "$port"
      return 0
    fi
    port=$((port + 1))
  done
  return 1
}

