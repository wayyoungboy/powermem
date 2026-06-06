#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

base_url=$(runtime_base_url)

echo "PowerMem Claude Code plugin status"
echo "Data dir: $DATA_DIR"
echo "Runtime file: $RUNTIME_FILE"
echo "Env file: $ENV_FILE"
echo "Base URL: $base_url"

if [ -f "$ENV_FILE" ]; then
  echo "Config: present"
else
  echo "Config: missing"
fi

if pid_alive; then
  echo "Managed server PID: $(cat "$PID_FILE")"
else
  echo "Managed server PID: not running"
fi

if is_healthy "$base_url"; then
  echo "Health: healthy"
else
  echo "Health: unavailable"
fi

if [ -f "$LOG_FILE" ]; then
  echo "Log: $LOG_FILE"
fi

