#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

echo "PowerMem Codex plugin uninstall"
echo "Data dir: $DATA_DIR"

delete_data=0
if truthy "${POWERMEM_UNINSTALL_DELETE_DATA:-}"; then
  delete_data=1
  if [ "${POWERMEM_UNINSTALL_CONFIRM:-}" != "delete-powermem-data" ]; then
    echo "Refusing to delete $DATA_DIR without POWERMEM_UNINSTALL_CONFIRM=delete-powermem-data." >&2
    exit 2
  fi
fi

if [ "$delete_data" = "1" ]; then
  echo "Stopping the local managed PowerMem backend before deleting local data."
  sh "$SCRIPT_DIR/stop.sh"
elif truthy "${POWERMEM_UNINSTALL_STOP_SERVER:-}" && ! truthy "${POWERMEM_UNINSTALL_KEEP_SERVER:-}"; then
  sh "$SCRIPT_DIR/stop.sh"
else
  echo "Keeping any local managed PowerMem backend running."
  echo "Set POWERMEM_UNINSTALL_STOP_SERVER=1 to stop it explicitly."
fi

if truthy "${POWERMEM_UNINSTALL_REMOVE_RUNTIME:-}"; then
  rm -f "$RUNTIME_FILE" 2>/dev/null || true
  remove_managed_pid_files
  echo "Removed hook runtime state: $RUNTIME_FILE"
fi

if truthy "${POWERMEM_UNINSTALL_REMOVE_CONFIG:-}" && [ "$delete_data" != "1" ]; then
  rm -f "$ENV_FILE" 2>/dev/null || true
  echo "Removed local PowerMem config: $ENV_FILE"
fi

if [ "$delete_data" = "1" ]; then
  data_abs=$(CDPATH= cd -- "$DATA_DIR" && pwd)
  home_abs=$(CDPATH= cd -- "$HOME" && pwd)
  case "$data_abs" in
    ""|"/"|"$home_abs")
      echo "Refusing to delete unsafe data directory: $data_abs" >&2
      exit 2
      ;;
  esac

  rm -rf -- "$data_abs"
  echo "Deleted PowerMem data directory: $data_abs"
elif truthy "${POWERMEM_UNINSTALL_REMOVE_RUNTIME:-}" || truthy "${POWERMEM_UNINSTALL_REMOVE_CONFIG:-}"; then
  echo "Kept local PowerMem memory data under $DATA_DIR."
else
  echo "Kept memories and configuration under $DATA_DIR."
fi

if truthy "${POWERMEM_UNINSTALL_REMOVE_PLUGIN:-}"; then
  if command -v codex >/dev/null 2>&1; then
    codex plugin remove powermem-codex-plugin 2>/dev/null || true
    echo "Requested Codex plugin removal: powermem-codex-plugin"
  else
    echo "codex command not found; remove the plugin from Codex manually." >&2
  fi
fi

echo "Uninstall step complete."
