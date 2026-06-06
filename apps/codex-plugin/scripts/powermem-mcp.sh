#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

if [ ! -f "$ENV_FILE" ]; then
  echo "PowerMem Codex plugin is not initialized. Use the powermem-init skill first." >&2
  exit 1
fi

MCP=$(venv_powermem_mcp)
if [ ! -x "$MCP" ]; then
  echo "powermem-mcp is not installed in the plugin venv. Use the powermem-init skill first." >&2
  exit 1
fi

export POWERMEM_ENV_FILE="$ENV_FILE"
exec "$MCP" stdio
