#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

powermem_data_dir() {
  if [ -n "${POWERMEM_PLUGIN_DATA:-}" ]; then
    printf '%s\n' "$POWERMEM_PLUGIN_DATA"
  elif [ -n "${PLUGIN_DATA:-}" ]; then
    printf '%s\n' "$PLUGIN_DATA"
  elif [ -n "${CODEX_PLUGIN_DATA:-}" ]; then
    printf '%s\n' "$CODEX_PLUGIN_DATA"
  elif [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
    printf '%s\n' "$CLAUDE_PLUGIN_DATA"
  else
    printf '%s\n' "$HOME/.codex/plugins/data/memory-powermem"
  fi
}

DATA_DIR=$(powermem_data_dir)
ENV_FILE="$DATA_DIR/.env"
RUNTIME_FILE="$DATA_DIR/runtime.env"
PID_FILE="$DATA_DIR/server.pid"
LOG_FILE="$DATA_DIR/powermem.log"
VENV_DIR="$DATA_DIR/venv"
CODEX_HOOKS_FILE="${CODEX_HOOKS_FILE:-$HOME/.codex/hooks.json}"

mkdir -p "$DATA_DIR"

choose_python() {
  if [ -n "${POWERMEM_INIT_PYTHON:-}" ]; then
    candidates=$POWERMEM_INIT_PYTHON
  else
    candidates="python3.11 python3 python"
  fi
  for candidate in $candidates; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
      then
        command -v "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

python_version() {
  "$1" - <<'PY'
import sys
print(".".join(map(str, sys.version_info[:3])))
PY
}

venv_python() {
  printf '%s/bin/python\n' "$VENV_DIR"
}

venv_powermem_mcp() {
  printf '%s/bin/powermem-mcp\n' "$VENV_DIR"
}

write_runtime_file() {
  tmp="$RUNTIME_FILE.tmp"
  {
    printf 'POWERMEM_ENV_FILE=%s\n' "$ENV_FILE"
    printf 'POWERMEM_MCP_COMMAND=%s\n' "$(venv_powermem_mcp)"
    printf 'POWERMEM_PLUGIN_ROOT=%s\n' "$PLUGIN_ROOT"
    printf 'PLUGIN_ROOT=%s\n' "$PLUGIN_ROOT"
    printf 'CODEX_HOOKS_FILE=%s\n' "$CODEX_HOOKS_FILE"
  } > "$tmp"
  mv "$tmp" "$RUNTIME_FILE"
}

pid_alive() {
  [ -f "$PID_FILE" ] || return 1
  pid=$(cat "$PID_FILE" 2>/dev/null || true)
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null
}
