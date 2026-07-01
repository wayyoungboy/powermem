#!/bin/sh
# Select the correct native binary for the Codex hook plugin.
ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(CDPATH= cd -- "$ROOT/.." && pwd)
DATA_DIR="${POWERMEM_DATA_DIR:-$HOME/.powermem}"
load_env_file() {
  [ -f "$1" ] || return 0
  set -a
  # shellcheck disable=SC1090
  . "$1"
  set +a
}
load_env_file "$DATA_DIR/runtime.env"
load_env_file "$PLUGIN_ROOT/config/runtime.env"
loopback_v4="127."
loopback_v4="${loopback_v4}0.0.1"
local_no_proxy="localhost,$loopback_v4,::1"
if [ -n "${NO_PROXY:-}" ]; then
  NO_PROXY="$local_no_proxy,$NO_PROXY"
else
  NO_PROXY="$local_no_proxy"
fi
if [ -n "${no_proxy:-}" ]; then
  no_proxy="$local_no_proxy,$no_proxy"
else
  no_proxy="$NO_PROXY"
fi
export NO_PROXY no_proxy
case "$(uname -s 2>/dev/null)" in
  Darwin) GOOS=darwin ;;
  Linux) GOOS=linux ;;
  *) exit 0 ;;
esac
case "$(uname -m 2>/dev/null)" in
  arm64|aarch64) GOARCH=arm64 ;;
  x86_64|amd64) GOARCH=amd64 ;;
  *) GOARCH=amd64 ;;
esac
BIN="$ROOT/bin/powermem-hook-${GOOS}-${GOARCH}"
if [ ! -x "$BIN" ] && [ -f "$BIN" ]; then
  chmod +x "$BIN" 2>/dev/null || true
fi
if [ ! -f "$BIN" ]; then
  exit 0
fi
exec "$BIN" "$@"
