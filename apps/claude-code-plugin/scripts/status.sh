#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

base_url=$(runtime_base_url)
connection_mode=$(runtime_connection_mode)
mcp_config="$PLUGIN_ROOT/.mcp.json"
mcp_enabled=0
if [ -f "$mcp_config" ] && grep -q '"powermem"' "$mcp_config"; then
  mcp_enabled=1
fi

remote_backend=0
if runtime_remote_mode || ! is_loopback_base_url "$base_url"; then
  remote_backend=1
fi

case "$connection_mode" in
  hook)
    if [ "$remote_backend" = "1" ]; then
      connection_summary="remote hook"
    else
      connection_summary="local hook"
    fi
    ;;
  mcp)
    if [ "$remote_backend" = "1" ]; then
      connection_summary="remote MCP"
    else
      connection_summary="local MCP"
    fi
    ;;
  both)
    if [ "$remote_backend" = "1" ]; then
      connection_summary="remote hook+MCP"
    else
      connection_summary="local hook+MCP"
    fi
    ;;
  *)
    if [ "$remote_backend" = "1" ] && [ "$mcp_enabled" = "1" ]; then
      connection_summary="remote hook+MCP"
    elif [ "$remote_backend" = "1" ]; then
      connection_summary="remote hook"
    elif [ "$mcp_enabled" = "1" ]; then
      connection_summary="local hook+MCP"
    else
      connection_summary="local hook"
    fi
    ;;
esac

echo "PowerMem Claude Code plugin status"
echo "Data dir: $DATA_DIR"
echo "Runtime file: $RUNTIME_FILE"
echo "Env file: $ENV_FILE"
echo "PID file: $(managed_pid_file)"
echo "Base URL: $base_url"
echo "Connection mode: $connection_summary"
if [ "$mcp_enabled" = "1" ]; then
  echo "MCP config: enabled ($mcp_config)"
else
  echo "MCP config: disabled ($mcp_config)"
fi

if [ "$remote_backend" = "1" ]; then
  echo "Bootstrap Python: not required for remote mode"
elif BOOTSTRAP_PYTHON=$(choose_python 2>/dev/null); then
  echo "Bootstrap Python: $BOOTSTRAP_PYTHON ($(python_version "$BOOTSTRAP_PYTHON"))"
else
  echo "Bootstrap Python: missing Python >= 3.11"
fi

if [ "$remote_backend" = "1" ]; then
  echo "Config: not required for remote mode"
elif [ -f "$ENV_FILE" ]; then
  echo "Config: present"
else
  echo "Config: missing"
fi

if [ "$remote_backend" = "1" ]; then
  echo "Managed server PID: not expected in remote mode"
elif pid_alive; then
  echo "Managed server PID: $(managed_pid)"
else
  echo "Managed server PID: not running"
fi

if [ -n "${POWERMEM_UV_BIN:-}" ] && command -v "$POWERMEM_UV_BIN" >/dev/null 2>&1; then
  uv_bin=$(command -v "$POWERMEM_UV_BIN")
elif command -v uv >/dev/null 2>&1; then
  uv_bin=$(command -v uv)
else
  uv_bin=""
fi

if [ "$remote_backend" = "1" ]; then
  echo "uv: not required for remote mode"
elif [ -n "$uv_bin" ]; then
  echo "uv: $uv_bin ($("$uv_bin" --version 2>/dev/null || echo unknown))"
  echo "Backend launcher: uvx --from '${POWERMEM_INIT_PACKAGE:-powermem[server,seekdb]}' powermem-server"
else
  echo "uv: missing"
fi

if [ -d "$DATA_DIR/venv" ]; then
  echo "Legacy venv: $DATA_DIR/venv (unused by uvx init)"
fi

if is_healthy "$base_url"; then
  echo "Health: healthy"
else
  echo "Health: unavailable"
  case "$base_url" in
    http://localhost:*|http://127.0.0.1:*)
      port=$(printf '%s\n' "$base_url" | sed -E 's#^http://(localhost|127\.0\.0\.1):([0-9]+).*#\2#')
      case "$port" in
        *[!0-9]*|"") ;;
        *) describe_port "$port" ;;
      esac
      ;;
  esac
fi

if [ -f "$LOG_FILE" ]; then
  echo "Log: $LOG_FILE"
fi
