#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

powermem_data_dir() {
  printf '%s\n' "$HOME/.powermem"
}

DATA_DIR="${POWERMEM_DATA_DIR:-$(powermem_data_dir)}"
ENV_FILE="${POWERMEM_ENV_FILE:-$DATA_DIR/.env}"
RUNTIME_FILE="${POWERMEM_RUNTIME_FILE:-$DATA_DIR/runtime.env}"
PID_FILE="${POWERMEM_PID_FILE:-$DATA_DIR/powermem.pid}"
LEGACY_PID_FILE="$DATA_DIR/server.pid"
LOG_FILE="${POWERMEM_LOG_FILE:-$DATA_DIR/powermem-server.log}"
USTC_PYTHON_INSTALL_MIRROR="https://mirrors.ustc.edu.cn/github-release/astral-sh/python-build-standalone/"

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

ensure_bootstrap_python() {
  if [ -n "${POWERMEM_INIT_PYTHON:-}" ]; then
    BOOTSTRAP_PYTHON=$(choose_python) || {
      echo "POWERMEM_INIT_PYTHON must point to Python >= 3.11." >&2
      return 1
    }
  else
    ensure_uv
    configure_uv_python_install_mirror
    echo "Ensuring Python 3.11 is available through uv."
    "$UV_BIN" python install 3.11
    BOOTSTRAP_PYTHON=$("$UV_BIN" python find 3.11) || {
      echo "uv could not locate Python 3.11 after installation." >&2
      return 1
    }
    if [ -z "$BOOTSTRAP_PYTHON" ]; then
      echo "uv returned an empty Python 3.11 path." >&2
      return 1
    fi
  fi

  POWERMEM_BOOTSTRAP_PYTHON=$BOOTSTRAP_PYTHON
  export BOOTSTRAP_PYTHON
  export POWERMEM_BOOTSTRAP_PYTHON
}

configure_uv_python_install_mirror() {
  if [ "${POWERMEM_UV_PYTHON_INSTALL_MIRROR_CONFIGURED:-0}" = "1" ]; then
    return
  fi
  POWERMEM_UV_PYTHON_INSTALL_MIRROR_CONFIGURED=1
  export POWERMEM_UV_PYTHON_INSTALL_MIRROR_CONFIGURED

  if [ -n "${POWERMEM_UV_PYTHON_INSTALL_MIRROR:-}" ]; then
    UV_PYTHON_INSTALL_MIRROR=$POWERMEM_UV_PYTHON_INSTALL_MIRROR
    export UV_PYTHON_INSTALL_MIRROR
    echo "uv Python install mirror: $UV_PYTHON_INSTALL_MIRROR"
    return
  fi

  if [ -n "${UV_PYTHON_INSTALL_MIRROR:-}" ]; then
    export UV_PYTHON_INSTALL_MIRROR
    echo "uv Python install mirror: $UV_PYTHON_INSTALL_MIRROR"
    return
  fi

  country=$(detect_public_ip_country || true)
  case "$country" in
    CN)
      UV_PYTHON_INSTALL_MIRROR=$USTC_PYTHON_INSTALL_MIRROR
      export UV_PYTHON_INSTALL_MIRROR
      echo "Detected public IP country: CN; uv python install will use $UV_PYTHON_INSTALL_MIRROR"
      ;;
    "")
      echo "Public IP country detection failed; uv python install will use the default Python download source."
      ;;
    *)
      echo "Detected public IP country: $country; uv python install will use the default Python download source."
      ;;
  esac
}

python_version() {
  "$1" - <<'PY'
import sys
print(".".join(map(str, sys.version_info[:3])))
PY
}

find_uv_bin() {
  if [ -n "${POWERMEM_UV_BIN:-}" ] && command -v "$POWERMEM_UV_BIN" >/dev/null 2>&1; then
    command -v "$POWERMEM_UV_BIN"
    return
  fi

  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return
  fi

  if [ -n "${HOME:-}" ]; then
    for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
      if [ -x "$candidate" ]; then
        printf '%s\n' "$candidate"
        return
      fi
    done
  fi

  return 1
}

fetch_public_ip_country_url() {
  url=$1
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -m 3 -A "powermem-init/1.0" "$url"
    return
  fi

  if command -v wget >/dev/null 2>&1; then
    wget -qO- -T 3 --user-agent="powermem-init/1.0" "$url"
    return
  fi

  return 1
}

detect_public_ip_country() {
  for url in \
    "https://ipapi.co/country/" \
    "https://ifconfig.co/country-iso" \
    "https://ipinfo.io/country"
  do
    country=$(
      fetch_public_ip_country_url "$url" 2>/dev/null \
        | tr -d '[:space:]' \
        | tr '[:lower:]' '[:upper:]' \
        | cut -c 1-2 \
        || true
    )
    case "$country" in
      [A-Z][A-Z])
        printf '%s\n' "$country"
        return 0
        ;;
    esac
  done

  return 1
}

install_uv_from_url() {
  installer_url=$1
  download_url=${2:-}
  installer_tmp="${TMPDIR:-/tmp}/powermem-uv-installer.$$.sh"

  if command -v curl >/dev/null 2>&1; then
    if curl -fsSL "$installer_url" -o "$installer_tmp"; then
      if [ -n "$download_url" ]; then
        env UV_DOWNLOAD_URL="$download_url" sh "$installer_tmp"
      else
        sh "$installer_tmp"
      fi
      status=$?
      rm -f "$installer_tmp"
      return "$status"
    else
      rm -f "$installer_tmp"
      return 1
    fi
  fi

  if command -v wget >/dev/null 2>&1; then
    if wget -qO "$installer_tmp" "$installer_url"; then
      if [ -n "$download_url" ]; then
        env UV_DOWNLOAD_URL="$download_url" sh "$installer_tmp"
      else
        sh "$installer_tmp"
      fi
      status=$?
      rm -f "$installer_tmp"
      return "$status"
    else
      rm -f "$installer_tmp"
      return 1
    fi
  fi

  echo "Neither curl nor wget is available; install uv manually and retry." >&2
  return 1
}

ensure_uv() {
  if UV_BIN=$(find_uv_bin); then
    export UV_BIN
    return
  fi

  country=$(detect_public_ip_country || true)
  case "$country" in
    CN)
      echo "uv not found; installing uv from the USTC mirror for CN networks."
      install_uv_from_url \
        "https://mirrors.ustc.edu.cn/github-release/astral-sh/uv/LatestRelease/uv-installer.sh" \
        "https://mirrors.ustc.edu.cn/github-release/astral-sh/uv/LatestRelease/" || {
          echo "USTC uv mirror install failed; falling back to the official Astral installer." >&2
          install_uv_from_url "https://astral.sh/uv/install.sh"
        }
      ;;
    "")
      echo "uv not found; region detection failed, installing uv from the official Astral installer."
      install_uv_from_url "https://astral.sh/uv/install.sh"
      ;;
    *)
      echo "uv not found; installing uv from the official Astral installer."
      install_uv_from_url "https://astral.sh/uv/install.sh"
      ;;
  esac

  PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  export PATH
  if command -v uv >/dev/null 2>&1; then
    UV_BIN=$(command -v uv)
    export UV_BIN
    return
  fi

  echo "uv installer finished, but uv is not on PATH. Add ~/.local/bin to PATH and retry." >&2
  return 1
}

configure_uv_index() {
  if [ "${POWERMEM_UV_INDEX_CONFIGURED:-0}" = "1" ]; then
    return
  fi
  POWERMEM_UV_INDEX_CONFIGURED=1
  export POWERMEM_UV_INDEX_CONFIGURED

  country=$(detect_public_ip_country || true)
  case "$country" in
    CN)
      POWERMEM_UV_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
      export POWERMEM_UV_INDEX_URL
      echo "Detected public IP country: CN; uvx will use --default-index $POWERMEM_UV_INDEX_URL"
      ;;
    "")
      echo "Public IP country detection failed; uvx will use the default PyPI index."
      ;;
    *)
      echo "Detected public IP country: $country; uvx will use the default PyPI index."
      ;;
  esac
}

uvx_run() {
  ensure_uv
  configure_uv_index
  if [ -n "${POWERMEM_UV_INDEX_URL:-}" ]; then
    "$UV_BIN" tool run --default-index "$POWERMEM_UV_INDEX_URL" "$@"
  else
    "$UV_BIN" tool run "$@"
  fi
}

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

normalize_base_url() {
  printf '%s\n' "$1" \
    | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's#/*$##'
}

is_loopback_base_url() {
  case "$(normalize_base_url "$1")" in
    http://localhost:*|http://127[.]0[.]0[.]1:*|http://[[]::1[]]:*|http://localhost|http://127[.]0[.]0[.]1|http://[[]::1[]]|https://localhost:*|https://127[.]0[.]0[.]1:*|https://[[]::1[]]:*|https://localhost|https://127[.]0[.]0[.]1|https://[[]::1[]])
      return 0
      ;;
  esac
  return 1
}

configured_remote_base_url() {
  if [ -n "${POWERMEM_INIT_REMOTE_BASE_URL:-}" ]; then
    normalize_base_url "$POWERMEM_INIT_REMOTE_BASE_URL"
    return
  fi
  if [ -n "${POWERMEM_REMOTE_BASE_URL:-}" ]; then
    normalize_base_url "$POWERMEM_REMOTE_BASE_URL"
    return
  fi
  if [ -n "${POWERMEM_BASE_URL:-}" ] && ! is_loopback_base_url "$POWERMEM_BASE_URL"; then
    normalize_base_url "$POWERMEM_BASE_URL"
    return
  fi
  if runtime_remote_mode; then
    normalize_base_url "$(runtime_base_url)"
    return
  fi
  printf '%s\n' ""
}

configured_connection_mode() {
  mode=${POWERMEM_INIT_CONNECTION_MODE:-${POWERMEM_CONNECTION_MODE:-}}
  if [ -z "$mode" ]; then
    mode=$(runtime_connection_mode)
  fi
  mode=${mode:-hook}
  printf '%s\n' "$mode" | tr '[:upper:]' '[:lower:]'
}

validate_connection_mode() {
  case "$1" in
    hook|mcp|both) return 0 ;;
  esac
  echo "Invalid POWERMEM_INIT_CONNECTION_MODE='$1'. Use hook, mcp, or both." >&2
  return 1
}

runtime_connection_mode() {
  if [ -n "${POWERMEM_CONNECTION_MODE:-}" ]; then
    printf '%s\n' "$POWERMEM_CONNECTION_MODE" | tr '[:upper:]' '[:lower:]'
    return
  fi
  if [ -f "$RUNTIME_FILE" ]; then
    # shellcheck disable=SC1090
    . "$RUNTIME_FILE"
    if [ -n "${POWERMEM_CONNECTION_MODE:-}" ]; then
      printf '%s\n' "$POWERMEM_CONNECTION_MODE" | tr '[:upper:]' '[:lower:]'
      return
    fi
  fi
  printf '%s\n' ""
}

runtime_remote_mode() {
  if [ "${POWERMEM_REMOTE_MODE:-}" = "1" ]; then
    return 0
  fi
  if [ -f "$RUNTIME_FILE" ]; then
    # shellcheck disable=SC1090
    . "$RUNTIME_FILE"
    if [ "${POWERMEM_REMOTE_MODE:-}" = "1" ]; then
      return 0
    fi
  fi
  return 1
}

configured_remote_api_key() {
  if [ -n "${POWERMEM_INIT_REMOTE_API_KEY:-}" ]; then
    printf '%s\n' "$POWERMEM_INIT_REMOTE_API_KEY"
    return
  fi
  if [ -n "${POWERMEM_REMOTE_API_KEY:-}" ]; then
    printf '%s\n' "$POWERMEM_REMOTE_API_KEY"
    return
  fi
  if [ -n "${POWERMEM_API_KEY:-}" ]; then
    printf '%s\n' "$POWERMEM_API_KEY"
    return
  fi
  if runtime_remote_mode && [ -f "$RUNTIME_FILE" ]; then
    # shellcheck disable=SC1090
    . "$RUNTIME_FILE"
    if [ -n "${POWERMEM_API_KEY:-}" ]; then
      printf '%s\n' "$POWERMEM_API_KEY"
      return
    fi
  fi
  printf '%s\n' ""
}

quote_runtime_value() {
  value=$1
  if contains_newline "$value"; then
    echo "Remote PowerMem runtime values must be single-line values." >&2
    return 1
  fi
  printf "'"
  printf '%s' "$value" | sed "s/'/'\\\\''/g"
  printf "'"
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

write_remote_runtime_config_file() {
  target=$1
  base_url=$2
  mode=$3
  remote_auth=${4:-}

  quoted_base_url=$(quote_runtime_value "$base_url") || return 1
  quoted_mode=$(quote_runtime_value "$mode") || return 1
  {
    printf 'POWERMEM_BASE_URL=%s\n' "$quoted_base_url"
    printf 'POWERMEM_CONNECTION_MODE=%s\n' "$quoted_mode"
    printf 'POWERMEM_REMOTE_MODE=1\n'
    if [ -n "$remote_auth" ]; then
      quoted_remote_auth=$(quote_runtime_value "$remote_auth") || return 1
      printf 'POWERMEM_API_KEY=%s\n' "$quoted_remote_auth"
    fi
  } > "$target"
}

write_remote_runtime_config() {
  base_url=$1
  mode=$2
  remote_auth=${3:-}
  tmp="$RUNTIME_FILE.tmp"
  write_remote_runtime_config_file "$tmp" "$base_url" "$mode" "$remote_auth" || return 1
  mv "$tmp" "$RUNTIME_FILE"
}

mcp_endpoint_url() {
  base_url=$(normalize_base_url "$1")
  case "$base_url" in
    */mcp) printf '%s\n' "$base_url" ;;
    *) printf '%s/mcp\n' "$base_url" ;;
  esac
}

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

contains_newline() {
  case "$1" in
    *'
'*) return 0 ;;
  esac
  return 1
}

write_http_only_mcp_config() {
  tmp="$PLUGIN_ROOT/.mcp.json.tmp"
  printf '{\n  "mcpServers": {}\n}\n' > "$tmp"
  mv "$tmp" "$PLUGIN_ROOT/.mcp.json"
}

write_remote_mcp_config() {
  base_url=$1
  remote_auth=${2:-}
  mcp_url=$(mcp_endpoint_url "$base_url")
  if contains_newline "$mcp_url" || contains_newline "$remote_auth"; then
    echo "Remote PowerMem URL and API key must be single-line values." >&2
    return 1
  fi

  escaped_url=$(json_escape "$mcp_url")
  tmp="$PLUGIN_ROOT/.mcp.json.tmp"
  if [ -n "$remote_auth" ]; then
    escaped_key=$(json_escape "$remote_auth")
    {
      printf '{\n'
      printf '  "mcpServers": {\n'
      printf '    "powermem": {\n'
      printf '      "transport": "http",\n'
      printf '      "url": "%s",\n' "$escaped_url"
      printf '      "headers": {\n'
      printf '        "X-API-Key": "%s"\n' "$escaped_key"
      printf '      }\n'
      printf '    }\n'
      printf '  }\n'
      printf '}\n'
    } > "$tmp"
  else
    {
      printf '{\n'
      printf '  "mcpServers": {\n'
      printf '    "powermem": {\n'
      printf '      "transport": "http",\n'
      printf '      "url": "%s"\n' "$escaped_url"
      printf '    }\n'
      printf '  }\n'
      printf '}\n'
    } > "$tmp"
  fi
  mv "$tmp" "$PLUGIN_ROOT/.mcp.json"
}

export_env_file_vars() {
  env_file=$1
  [ -f "$env_file" ] || return 0

  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ""|\#*) continue ;;
      *=*)
        key=${line%%=*}
        case "$key" in
          [A-Za-z_]*)
            case "$key" in
              *[!A-Za-z0-9_]*) continue ;;
            esac
            export "$line"
            ;;
        esac
        ;;
    esac
  done < "$env_file"
}

health_url() {
  base_url=$(printf '%s' "$1" | sed 's:/*$::')
  printf '%s/api/v1/system/health\n' "$base_url"
}

is_healthy() {
  url=$(health_url "$1")
  curl -fsS -m 5 "$url" 2>/dev/null | grep -q '"healthy"'
}

announce_dashboard_url() {
  case "$1" in
    */) dashboard_url="${1}dashboard/" ;;
    *) dashboard_url="${1}/dashboard/" ;;
  esac
  echo "Memory dashboard: $dashboard_url"
}

pid_alive() {
  pid=$(managed_pid) || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  pid_is_powermem_server "$pid" || return 1
  pid_uses_env_file "$pid" || return 1
}

managed_pid_file() {
  if [ -f "$PID_FILE" ]; then
    printf '%s\n' "$PID_FILE"
    return
  fi
  if [ -z "${POWERMEM_PID_FILE:-}" ] && [ -f "$LEGACY_PID_FILE" ]; then
    printf '%s\n' "$LEGACY_PID_FILE"
    return
  fi
  printf '%s\n' "$PID_FILE"
}

managed_pid() {
  file=$(managed_pid_file)
  [ -f "$file" ] || return 1
  pid=$(cat "$file" 2>/dev/null | tr -d '[:space:]' || true)
  case "$pid" in
    ""|*[!0-9]*) return 1 ;;
  esac
  printf '%s\n' "$pid"
}

write_managed_pid() {
  printf '%s\n' "$1" > "$PID_FILE"
  if [ -z "${POWERMEM_PID_FILE:-}" ] && [ "$LEGACY_PID_FILE" != "$PID_FILE" ]; then
    rm -f "$LEGACY_PID_FILE" 2>/dev/null || true
  fi
}

remove_managed_pid_files() {
  file=$(managed_pid_file)
  rm -f "$file" 2>/dev/null || true
  if [ -z "${POWERMEM_PID_FILE:-}" ]; then
    rm -f "$PID_FILE" "$LEGACY_PID_FILE" 2>/dev/null || true
  fi
}

pid_is_powermem_server() {
  pid=$1
  args=$(process_args "$pid")
  [ -n "$args" ] || return 0
  printf '%s\n' "$args" | grep -q 'powermem-server'
}

process_args() {
  ps -p "$1" -o args= 2>/dev/null || ps -p "$1" -o command= 2>/dev/null || true
}

managed_base_url() {
  pid=$(managed_pid) || return 1
  args=$(process_args "$pid")
  [ -n "$args" ] || return 1

  host=127.0.0.1
  port=
  next=
  for arg in $args; do
    if [ "$next" = "host" ]; then
      host=$arg
      next=
      continue
    fi
    if [ "$next" = "port" ]; then
      port=$arg
      next=
      continue
    fi
    case "$arg" in
      --host=*) host=${arg#--host=} ;;
      --host) next=host ;;
      --port=*) port=${arg#--port=} ;;
      --port) next=port ;;
    esac
  done

  case "$port" in
    ""|*[!0-9]*) return 1 ;;
  esac
  case "$host" in
    ""|"0.0.0.0"|"::"|"[::]") host=localhost ;;
  esac
  printf 'http://%s:%s\n' "$host" "$port"
}

pid_uses_env_file() {
  pid=$1
  environ="/proc/$pid/environ"
  [ -r "$environ" ] || return 0
  tr '\000' '\n' < "$environ" | grep -Fx "POWERMEM_ENV_FILE=$ENV_FILE" >/dev/null
}

local_port_from_base_url() {
  printf '%s\n' "$1" \
    | sed -n -E 's#^http://(localhost|127\.0\.0\.1|\[::1\]):([0-9]+)(/.*)?$#\2#p'
}

listener_pids_for_port() {
  port=$1
  {
    if command -v lsof >/dev/null 2>&1; then
      lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
    fi
    if command -v ss >/dev/null 2>&1; then
      ss -H -ltnp "sport = :$port" 2>/dev/null \
        | sed -n -E 's/.*pid=([0-9]+).*/\1/p' || true
    fi
    if command -v fuser >/dev/null 2>&1; then
      fuser -n tcp "$port" 2>/dev/null || true
    fi
  } | tr ' ' '\n' | sed -n -E '/^[0-9]+$/p' | sort -u
}

powermem_server_pids_for_port() {
  port=$1
  listener_pids_for_port "$port" | while IFS= read -r pid; do
    [ -n "$pid" ] || continue
    args=$(process_args "$pid")
    [ -n "$args" ] || continue
    printf '%s\n' "$args" | grep -q 'powermem-server' || continue
    pid_uses_env_file "$pid" || continue
    printf '%s\n' "$pid"
  done
}

port_free() {
  py=${POWERMEM_BOOTSTRAP_PYTHON:-python3}
  "$py" - "$1" <<'PY'
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

describe_port() {
  port=$1
  echo "Port $port is occupied."
  if command -v lsof >/dev/null 2>&1; then
    echo "lsof -nP -iTCP:$port -sTCP:LISTEN:"
    lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
  else
    echo "lsof is not installed; run: netstat -anp | grep ':$port'"
  fi
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
