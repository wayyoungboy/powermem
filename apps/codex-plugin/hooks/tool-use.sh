#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
phase=${1:-post}
case "$phase" in
  pre) event=PreToolUse ;;
  *) event=PostToolUse ;;
esac
python3 "$SCRIPT_DIR/powermem-hook.py" "$event"
