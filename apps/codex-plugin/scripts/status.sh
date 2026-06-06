#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

echo "PowerMem Codex plugin status"
echo "Data dir: $DATA_DIR"
echo "Env file: $ENV_FILE"
echo "Runtime file: $RUNTIME_FILE"
echo "Bundled MCP: $PLUGIN_ROOT/.mcp.json"
echo "Bundled hooks: $PLUGIN_ROOT/hooks/hooks.codex.json"
echo "Codex hooks: $CODEX_HOOKS_FILE"

if BOOTSTRAP_PYTHON=$(choose_python 2>/dev/null); then
  echo "Bootstrap Python: $BOOTSTRAP_PYTHON ($(python_version "$BOOTSTRAP_PYTHON"))"
else
  echo "Bootstrap Python: missing Python >= 3.11"
fi

if [ -f "$ENV_FILE" ]; then
  echo "Config: present"
else
  echo "Config: missing"
fi

if [ -x "$(venv_python)" ]; then
  PYTHON=$(venv_python)
  echo "Venv Python: $PYTHON ($(python_version "$PYTHON"))"
else
  echo "Venv Python: missing"
fi

if [ -x "$(venv_powermem_mcp)" ]; then
  echo "powermem-mcp: $(venv_powermem_mcp)"
else
  echo "powermem-mcp: missing"
fi

if [ -f "$PLUGIN_ROOT/.mcp.json" ]; then
  echo "Bundled MCP config: present"
else
  echo "Bundled MCP config: missing"
fi

if [ -f "$PLUGIN_ROOT/hooks/hooks.codex.json" ]; then
  echo "Bundled hook config: present"
else
  echo "Bundled hook config: missing"
fi

if [ -f "$CODEX_HOOKS_FILE" ]; then
  echo "Codex hooks: present"
  if grep -q '"__powermem_codex_hook__"' "$CODEX_HOOKS_FILE"; then
    echo "PowerMem fallback hooks: present"
  else
    echo "PowerMem fallback hooks: missing"
  fi
else
  echo "Codex hooks: missing"
fi

if pid_alive; then
  echo "Managed server PID: $(cat "$PID_FILE")"
else
  echo "Managed server PID: not running"
fi
