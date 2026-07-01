#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

echo "PowerMem Codex plugin init"
echo "Data dir: $DATA_DIR"

base_url=$(runtime_base_url)
if [ -n "${POWERMEM_CONNECT_BASE_URL:-}" ]; then
  base_url=$(printf '%s' "$POWERMEM_CONNECT_BASE_URL" | sed 's:/*$::')
fi
if [ -z "${POWERMEM_INIT_PORT:-}" ] && [ -n "${POWERMEM_SERVER_PORT:-}" ]; then
  POWERMEM_INIT_PORT=$POWERMEM_SERVER_PORT
  export POWERMEM_INIT_PORT
fi

connect_existing_requested() {
  loopback_v4="127."
  loopback_v4="${loopback_v4}0.0.1"
  if truthy "${POWERMEM_CONNECT_EXISTING:-}"; then
    return 0
  fi
  if [ -n "${POWERMEM_CONNECT_BASE_URL:-}" ]; then
    return 0
  fi
  case "${POWERMEM_BASE_URL:-}" in
    http://localhost:8848|http://localhost:8848/|http://$loopback_v4:8848|http://$loopback_v4:8848/|"")
      return 1
      ;;
    *)
      return 0
      ;;
  esac
}

if connect_existing_requested; then
  echo "Connecting Codex hooks to an existing PowerMem backend: $base_url"
  if is_healthy "$base_url"; then
    write_runtime_base_url "$base_url"
    echo "Existing PowerMem backend is healthy: $base_url"
    echo "Memory dashboard: ${base_url%/}/dashboard/"
    echo "Hook runtime written to $RUNTIME_FILE."
    if [ -n "${POWERMEM_API_KEY:-}" ]; then
      echo "API key: configured (value hidden)"
    fi
    if [ -n "${POWERMEM_USER_ID:-}" ]; then
      echo "User ID: $POWERMEM_USER_ID"
    fi
    if [ -n "${POWERMEM_AGENT_ID:-}" ]; then
      echo "Agent ID: $POWERMEM_AGENT_ID"
    fi
    echo "Not starting a managed local powermem-server."
    exit 0
  fi
  echo "Existing PowerMem backend is not healthy or is unreachable: $base_url" >&2
  echo "Check POWERMEM_CONNECT_BASE_URL/POWERMEM_BASE_URL, POWERMEM_API_KEY, and network access." >&2
  exit 1
fi

ensure_bootstrap_python || exit 1
echo "Bootstrap Python: $BOOTSTRAP_PYTHON ($(python_version "$BOOTSTRAP_PYTHON"))"

backup_env_file() {
  [ -f "$ENV_FILE" ] || return 0
  backup="$ENV_FILE.bak.$(date +%Y%m%d%H%M%S)"
  cp "$ENV_FILE" "$backup"
  echo "Backed up existing plugin .env to $backup"
}

resolve_import_env_file() {
  src=$1
  case "$src" in
    "~") src=$HOME ;;
    "~/"*) src=$HOME/${src#~/} ;;
  esac
  printf '%s\n' "$src"
}

import_env_file() {
  src=$(resolve_import_env_file "$1")
  if [ ! -f "$src" ]; then
    echo "POWERMEM_IMPORT_ENV_FILE does not point to a readable file: $src" >&2
    exit 2
  fi
  src_dir=$(CDPATH= cd -- "$(dirname "$src")" && pwd)
  src_abs="$src_dir/$(basename "$src")"
  env_dir=$(CDPATH= cd -- "$(dirname "$ENV_FILE")" && pwd)
  env_abs="$env_dir/$(basename "$ENV_FILE")"
  if [ "$src_abs" = "$env_abs" ]; then
    echo "Using imported .env already in place: $ENV_FILE"
    return 0
  fi
  backup_env_file
  cp "$src_abs" "$ENV_FILE"
  chmod 600 "$ENV_FILE" 2>/dev/null || true
  echo "Imported PowerMem .env from $src_abs to $ENV_FILE"
}

server_port_from_env_file() {
  [ -f "$ENV_FILE" ] || return 1
  port=$(sed -n 's/^POWERMEM_SERVER_PORT=//p' "$ENV_FILE" 2>/dev/null \
    | tail -n 1 \
    | tr -d '[:space:]')
  case "$port" in
    ""|*[!0-9]*) return 1 ;;
  esac
  printf '%s\n' "$port"
}

use_imported_server_port() {
  if [ -n "${POWERMEM_INIT_PORT:-}" ]; then
    base_url="http://localhost:$POWERMEM_INIT_PORT"
    return
  fi
  imported_port=$(server_port_from_env_file || true)
  if [ -n "$imported_port" ]; then
    POWERMEM_INIT_PORT=$imported_port
    export POWERMEM_INIT_PORT
    base_url="http://localhost:$POWERMEM_INIT_PORT"
  fi
}

create_env_file() {
  "$BOOTSTRAP_PYTHON" - "$ENV_FILE" "$DATA_DIR" <<'PY'
import os
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
data_dir = Path(sys.argv[2]).expanduser()

def env_first(*names):
    value, _ = env_first_with_source(*names)
    return value

def env_first_with_source(*names):
    for name in names:
        value = os.environ.get(name)
        if value is not None and value.strip():
            return value.strip(), f"env:{name}"
    return "", ""

def settings_first(settings_env, *names):
    value, _ = settings_first_with_source(settings_env, *names)
    return value

def settings_first_with_source(settings_env, *names):
    for name in names:
        value = settings_env.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip(), f"settings.env:{name}"
    return "", ""

def first_value(*items):
    for value, source in items:
        if value:
            return value, source
    return "", ""

def path_value(*parts):
    return str(data_dir.joinpath(*parts))

def provider_base_url_from_env(provider):
    value, _ = provider_base_url_from_env_source(provider)
    return value

def provider_base_url_from_env_source(provider):
    provider_base_envs = {
        "anthropic": ("ANTHROPIC_BASE_URL",),
        "openai": ("OPENAI_BASE_URL",),
        "qwen": ("QWEN_BASE_URL",),
        "siliconflow": ("SILICONFLOW_BASE_URL",),
        "deepseek": ("DEEPSEEK_BASE_URL",),
    }
    return env_first_with_source(*provider_base_envs.get(provider, ()))

def provider_base_url_from_settings(settings_env, provider):
    value, _ = provider_base_url_from_settings_source(settings_env, provider)
    return value

def provider_base_url_from_settings_source(settings_env, provider):
    provider_base_keys = {
        "anthropic": ("ANTHROPIC_BASE_URL",),
        "openai": ("OPENAI_BASE_URL",),
        "qwen": ("QWEN_BASE_URL",),
        "siliconflow": ("SILICONFLOW_BASE_URL",),
        "deepseek": ("DEEPSEEK_BASE_URL",),
    }
    return settings_first_with_source(settings_env, *(provider_base_keys.get(provider, ()) + ("LLM_BASE_URL",)))

settings_env = {}
settings_model = ""
force_no_llm = os.environ.get("POWERMEM_INIT_NO_LLM", "").strip().lower() in {"1", "true", "yes", "on"}
raw_model, model_source = first_value(
    env_first_with_source("POWERMEM_INIT_LLM_MODEL", "LLM_MODEL", "ANTHROPIC_MODEL"),
    settings_first_with_source(settings_env, "ANTHROPIC_MODEL", "LLM_MODEL"),
    (settings_model.strip(), "settings.model" if settings_model.strip() else ""),
)
raw_model = raw_model.strip()

explicit_base_url, explicit_base_url_source = env_first_with_source("POWERMEM_INIT_LLM_BASE_URL", "LLM_BASE_URL")
env_llm_credential, env_llm_credential_source = first_value(
    env_first_with_source("POWERMEM_INIT_LLM_API_KEY", "LLM_API_KEY"),
    env_first_with_source("ANTHROPIC_API_KEY"),
)
env_auth_credential, env_auth_credential_source = first_value(
    env_first_with_source("POWERMEM_INIT_LLM_AUTH_TOKEN", "LLM_AUTH_TOKEN"),
    env_first_with_source("ANTHROPIC_AUTH_TOKEN"),
)
env_anthropic_base_url, env_anthropic_base_url_source = env_first_with_source("ANTHROPIC_BASE_URL")
env_auth_base_url, env_auth_base_url_source = first_value(
    (explicit_base_url, explicit_base_url_source),
    (env_anthropic_base_url, env_anthropic_base_url_source),
)
settings_llm_credential, settings_llm_credential_source = settings_first_with_source(settings_env, "ANTHROPIC_API_KEY")
settings_auth_credential, settings_auth_credential_source = settings_first_with_source(settings_env, "ANTHROPIC_AUTH_TOKEN")
settings_auth_base_value, settings_auth_base_source = settings_first_with_source(
    settings_env,
    "ANTHROPIC_BASE_URL",
    "LLM_BASE_URL",
)
settings_auth_base_url, settings_auth_base_url_source = first_value(
    (explicit_base_url, explicit_base_url_source),
    (settings_auth_base_value, settings_auth_base_source),
)

llm_credential = ""
llm_credential_source = ""
auth_credential = ""
auth_credential_source = ""
base_url = ""
base_url_source = ""
credential_source_group = ""
if env_llm_credential:
    llm_credential = env_llm_credential
    llm_credential_source = env_llm_credential_source
    credential_source_group = "env"
elif env_auth_credential and env_auth_base_url:
    auth_credential = env_auth_credential
    auth_credential_source = env_auth_credential_source
    base_url = env_auth_base_url
    base_url_source = env_auth_base_url_source
    credential_source_group = "env"
elif settings_llm_credential:
    llm_credential = settings_llm_credential
    llm_credential_source = settings_llm_credential_source
    credential_source_group = "settings"
elif settings_auth_credential and settings_auth_base_url:
    auth_credential = settings_auth_credential
    auth_credential_source = settings_auth_credential_source
    base_url = settings_auth_base_url
    base_url_source = settings_auth_base_url_source
    credential_source_group = "settings"
elif env_auth_credential:
    auth_credential = env_auth_credential
    auth_credential_source = env_auth_credential_source
    credential_source_group = "env"
elif settings_auth_credential:
    auth_credential = settings_auth_credential
    auth_credential_source = settings_auth_credential_source
    credential_source_group = "settings"

key_provider = "anthropic" if auth_credential or llm_credential else ""

model_prefix = raw_model.split("/", 1)[0].strip().lower() if "/" in raw_model else ""
explicit_provider, explicit_provider_source = env_first_with_source("POWERMEM_INIT_LLM_PROVIDER", "LLM_PROVIDER")
settings_provider, settings_provider_source = settings_first_with_source(settings_env, "LLM_PROVIDER")
provider_candidates = [
    (explicit_provider, explicit_provider_source),
]
if credential_source_group != "env":
    provider_candidates.append((settings_provider, settings_provider_source))
provider_candidates.extend(
    [
        (key_provider, "inferred:anthropic credential" if key_provider else ""),
        (model_prefix, "inferred:LLM model prefix" if model_prefix else ""),
    ]
)
provider, provider_source = first_value(*provider_candidates)
provider = provider.lower()

model = raw_model

if force_no_llm:
    provider = "noop"
    provider_source = "env:POWERMEM_INIT_NO_LLM"
    model = "noop"
    model_source = "env:POWERMEM_INIT_NO_LLM"
    llm_credential = ""
    llm_credential_source = ""
    auth_credential = ""
    auth_credential_source = ""
    base_url = ""
    base_url_source = ""
    credential_source_group = "no-llm"

if not force_no_llm and not base_url and not auth_credential:
    base_url = explicit_base_url
    base_url_source = explicit_base_url_source
if not force_no_llm and not base_url and not auth_credential:
    if credential_source_group == "env":
        base_url, base_url_source = provider_base_url_from_env_source(provider)
    elif credential_source_group == "settings":
        base_url, base_url_source = provider_base_url_from_settings_source(settings_env, provider)
    else:
        base_url, base_url_source = provider_base_url_from_env_source(provider)
        if not base_url:
            base_url, base_url_source = provider_base_url_from_settings_source(settings_env, provider)
base_url = base_url.strip()

missing = []
llm_credentials_missing = False
if not provider:
    missing.append("POWERMEM_INIT_LLM_PROVIDER")
    llm_credentials_missing = True
if not model:
    missing.append("POWERMEM_INIT_LLM_MODEL")
if provider not in {"ollama", "vllm", "noop"}:
    if provider == "anthropic":
        if not auth_credential and not llm_credential:
            llm_credentials_missing = True
            missing.append(
                "ANTHROPIC_AUTH_TOKEN + ANTHROPIC_BASE_URL, "
                "ANTHROPIC_API_KEY, or POWERMEM_INIT_LLM_API_KEY"
            )
        if auth_credential and not base_url:
            llm_credentials_missing = True
            missing.append("ANTHROPIC_BASE_URL or POWERMEM_INIT_LLM_BASE_URL")
    elif not llm_credential:
        llm_credentials_missing = True
        missing.append("POWERMEM_INIT_LLM_API_KEY or LLM_API_KEY")

if missing:
    if llm_credentials_missing:
        print("No complete LLM configuration found: " + ", ".join(missing))
        print(
            "PowerMem will run in no-LLM mode. Basic memory add/search/update/delete "
            "will work, while fact extraction, profile extraction, query rewrite, "
            "compression, and graph extraction will be skipped."
        )
        provider = "noop"
        provider_source = "fallback:no complete LLM config"
        model = "noop"
        model_source = "fallback:no complete LLM config"
        llm_credential = ""
        llm_credential_source = ""
        auth_credential = ""
        auth_credential_source = ""
        base_url = ""
        base_url_source = ""
    else:
        print("Missing configuration: " + ", ".join(missing), file=sys.stderr)
        print("Run init again with these environment variables set.", file=sys.stderr)
        sys.exit(2)

VALID_PROVIDERS = {"sqlite", "oceanbase"}
db_provider = (env_first("POWERMEM_INIT_DATABASE_PROVIDER") or "sqlite").lower()
if db_provider not in VALID_PROVIDERS:
    print(f"Warning: unknown DATABASE_PROVIDER '{db_provider}', falling back to sqlite",
          file=sys.stderr)
    db_provider = "sqlite"

# For the SQLite path, use huggingface (sentence-transformers, local, no API key)
# instead of `default` which requires the seekdb extra.  OceanBase keeps `default`.
_embedding_fallback = "huggingface" if db_provider == "sqlite" else "default"

embedding_provider = env_first("POWERMEM_INIT_EMBEDDING_PROVIDER", "EMBEDDING_PROVIDER") or _embedding_fallback
embedding_provider = embedding_provider.lower()

embedding_model_defaults = {
    "default": "all-MiniLM-L6-v2",
    "huggingface": "all-MiniLM-L6-v2",
    "qwen": "text-embedding-v4",
    "openai": "text-embedding-3-small",
    "siliconflow": "BAAI/bge-m3",
    "ollama": "nomic-embed-text",
    "lmstudio": "text-embedding-nomic-embed-text-v1.5",
}
embedding_dim_defaults = {
    "default": "384",
    "huggingface": "384",
    "qwen": "1536",
    "openai": "1536",
    "siliconflow": "1024",
    "ollama": "768",
    "lmstudio": "768",
}
embedding_model = (
    env_first("POWERMEM_INIT_EMBEDDING_MODEL", "EMBEDDING_MODEL")
    or embedding_model_defaults.get(embedding_provider, embedding_model_defaults["default"])
)
embedding_dims = (
    env_first("POWERMEM_INIT_EMBEDDING_DIMS", "EMBEDDING_DIMS")
    or embedding_dim_defaults.get(embedding_provider, embedding_dim_defaults["default"])
)
embedding_llm_credential = env_first("POWERMEM_INIT_EMBEDDING_API_KEY", "EMBEDDING_API_KEY")
if not embedding_llm_credential:
    if embedding_provider == "qwen":
        embedding_llm_credential = env_first("QWEN_API_KEY", "DASHSCOPE_API_KEY") or settings_first(settings_env, "QWEN_API_KEY", "DASHSCOPE_API_KEY")
    elif embedding_provider == "openai":
        embedding_llm_credential = env_first("OPENAI_API_KEY") or settings_first(settings_env, "OPENAI_API_KEY")
    elif embedding_provider == "siliconflow":
        embedding_llm_credential = env_first("SILICONFLOW_API_KEY") or settings_first(settings_env, "SILICONFLOW_API_KEY")

if embedding_provider not in {"default", "huggingface", "ollama", "lmstudio"} and not embedding_llm_credential:
    print(
        "Missing configuration: POWERMEM_INIT_EMBEDDING_API_KEY "
        f"for EMBEDDING_PROVIDER={embedding_provider}",
        file=sys.stderr,
    )
    sys.exit(2)

server_port = env_first("POWERMEM_SERVER_PORT", "POWERMEM_INIT_PORT") or "8848"
server_host = env_first("POWERMEM_SERVER_HOST") or ("127." "0.0.1")
server_workers = env_first("POWERMEM_SERVER_WORKERS") or "1"
server_log_file = env_first("POWERMEM_SERVER_LOG_FILE") or path_value("powermem-server." "log")
logging_level = env_first("LOGGING_LEVEL") or "INFO"

if db_provider == "sqlite":
    db_lines = [
        "# Database: SQLite (lightweight, no external service required)",
        "DATABASE_PROVIDER=sqlite",
        f"SQLITE_PATH={path_value('powermem.db')}",
        "SQLITE_COLLECTION=memories",
        "SQLITE_ENABLE_WAL=true",
        "SQLITE_TIMEOUT=30",
    ]
else:
    db_lines = [
        "# Database: embedded seekdb through the OceanBase provider",
        "DATABASE_PROVIDER=oceanbase",
        "OCEANBASE_HOST=",
        f"OCEANBASE_PATH={path_value('seekdb_data')}",
        "OCEANBASE_PORT=2881",
        "OCEANBASE_USER=root@sys",
        "OCEANBASE_PASSWORD=",
        "OCEANBASE_DATABASE=powermem",
        "OCEANBASE_COLLECTION=memories",
        "OCEANBASE_INDEX_TYPE=HNSW",
        "OCEANBASE_VECTOR_METRIC_TYPE=cosine",
        f"OCEANBASE_EMBEDDING_MODEL_DIMS={embedding_dims}",
        "OCEANBASE_TEXT_FIELD=document",
        "OCEANBASE_VECTOR_FIELD=embedding",
        "OCEANBASE_PRIMARY_FIELD=id",
        "OCEANBASE_METADATA_FIELD=metadata",
        "OCEANBASE_VIDX_NAME=memories_vidx",
        "OCEANBASE_INCLUDE_SPARSE=false",
        "OCEANBASE_ENABLE_NATIVE_HYBRID=false",
    ]

lines = [
    "# Generated by the PowerMem Codex plugin.",
    "",
    "# Core paths",
    f"POWERMEM_DATA_DIR={data_dir}",
    "",
    *db_lines,
    "",
    "# LLM",
    f"LLM_PROVIDER={provider}",
    f"LLM_MODEL={model}",
]
if llm_credential:
    lines.append(f"LLM_API_KEY={llm_credential}")
if auth_credential:
    lines.append(f"LLM_AUTH_TOKEN={auth_credential}")
if base_url:
    key = f"{provider.upper()}_LLM_BASE_URL"
    if provider == "qwen":
        key = "QWEN_LLM_BASE_URL"
    lines.append(f"{key}={base_url}")
else:
    key = ""

lines.extend(
    [
        "",
        "# Embedding",
        f"EMBEDDING_PROVIDER={embedding_provider}",
        f"EMBEDDING_MODEL={embedding_model}",
        f"EMBEDDING_DIMS={embedding_dims}",
    ]
)
if embedding_llm_credential:
    lines.append(f"EMBEDDING_API_KEY={embedding_llm_credential}")
# Note: do NOT write HF_HUB_OFFLINE=1 here. PowerMem's HuggingFaceEmbedding
# manages offline behaviour itself via SentenceTransformer(local_files_only=True)
# and runs an internal ModelScope/HF download when the cache is empty. Forcing
# HF_HUB_OFFLINE=1 globally would block that download for non-CN users.

embedding_base_override = env_first("POWERMEM_INIT_EMBEDDING_BASE_URL", "EMBEDDING_BASE_URL")
embedding_base_keys = {
    "qwen": "QWEN_EMBEDDING_BASE_URL",
    "openai": "OPENAI_EMBEDDING_BASE_URL",
    "siliconflow": "SILICONFLOW_EMBEDDING_BASE_URL",
    "ollama": "OLLAMA_EMBEDDING_BASE_URL",
    "lmstudio": "LMSTUDIO_EMBEDDING_BASE_URL",
}
if embedding_base_override and embedding_provider in embedding_base_keys:
    lines.append(f"{embedding_base_keys[embedding_provider]}={embedding_base_override}")

lines.extend(
    [
        "# Server",
        f"POWERMEM_SERVER_HOST={server_host}",
        f"POWERMEM_SERVER_PORT={server_port}",
        f"POWERMEM_SERVER_WORKERS={server_workers}",
        "POWERMEM_SERVER_RELOAD=false",
        "POWERMEM_SERVER_AUTH_ENABLED=false",
        "POWERMEM_SERVER_API_KEYS=",
        "POWERMEM_SERVER_RATE_LIMIT_ENABLED=true",
        "POWERMEM_SERVER_RATE_LIMIT_PER_MINUTE=100",
        f"POWERMEM_SERVER_LOG_FILE={server_log_file}",
        "POWERMEM_SERVER_LOG_LEVEL=INFO",
        "POWERMEM_SERVER_LOG_FORMAT=json",
        "POWERMEM_SERVER_API_TITLE=PowerMem API",
        "POWERMEM_SERVER_API_VERSION=v1",
        "POWERMEM_SERVER_CORS_ENABLED=true",
        "POWERMEM_SERVER_CORS_ORIGINS=*",
        "",
        "# Logging",
        f"LOGGING_LEVEL={logging_level}",
        "LOGGING_FORMAT=json",
        f"LOGGING_FILE={path_value('powermem.' 'log')}",
        f"AUDIT_LOG_FILE={path_value('audit.' 'log')}",
        "",
        "# Vector store tuning",
        "VECTOR_STORE_BATCH_SIZE=50",
        "VECTOR_STORE_CACHE_SIZE=500",
        "VECTOR_STORE_INDEX_REBUILD_INTERVAL=86400",
        "",
        "# Optional retrieval features",
        "SPARSE_VECTOR_ENABLE=false",
        "",
    ]
)

env_path.parent.mkdir(parents=True, exist_ok=True)
env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(
    f"Wrote {env_path} with db_provider={db_provider}, llm_provider={provider}, llm_model={model}, "
    f"embedding_provider={embedding_provider}, embedding_model={embedding_model}, "
    f"embedding_dims={embedding_dims}, server_port={server_port}"
)
print("LLM config sources:")
print(f"  LLM_PROVIDER: {provider_source or 'not set'}")
print(f"  LLM_MODEL: {model_source or 'not set'}")
if llm_credential:
    print(f"  LLM_API_KEY: {llm_credential_source or 'unknown'} (value hidden)")
elif auth_credential:
    print(f"  LLM_AUTH_TOKEN: {auth_credential_source or 'unknown'} (value hidden)")
else:
    print("  LLM_API_KEY/LLM_AUTH_TOKEN: not required")
if key and base_url:
    print(f"  {key}: {base_url_source or 'unknown'} (value hidden)")
else:
    print("  *_LLM_BASE_URL: not set")
PY
}

validate_llm_config() {
  "$BOOTSTRAP_PYTHON" - "$ENV_FILE" <<'PY'
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

env = {}
for line in Path(sys.argv[1]).read_text().splitlines():
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

def env_value_with_source(*names):
    for name in names:
        value = env.get(name, '')
        if value:
            return value, f".env:{name}"
    return '', ''

provider = env.get('LLM_PROVIDER', '')
model    = env.get('LLM_MODEL', '')
llm_credential, llm_credential_source = env_value_with_source('LLM_API_KEY')
auth_credential, auth_credential_source = env_value_with_source('LLM_AUTH_TOKEN', 'ANTHROPIC_AUTH_TOKEN')
base_url_name = f'{provider.upper()}_LLM_BASE_URL' if provider else ''
base_url, base_url_source = env_value_with_source(base_url_name) if base_url_name else ('', '')
if provider == 'anthropic':
    if not base_url:
        base_url, base_url_source = env_value_with_source('ANTHROPIC_BASE_URL')
    if llm_credential:
        auth_credential = ''
        auth_credential_source = ''
    elif auth_credential and not base_url:
        print(
            'LLM validation failed: ANTHROPIC_AUTH_TOKEN/LLM_AUTH_TOKEN requires '
            'ANTHROPIC_LLM_BASE_URL or ANTHROPIC_BASE_URL.',
            file=sys.stderr,
        )
        sys.exit(1)

if provider == 'noop':
    print("LLM validation skipped: no-LLM mode is enabled.")
    sys.exit(0)

if provider in {'ollama', 'vllm'} or not (llm_credential or auth_credential):
    sys.exit(0)

print("LLM validation sources:")
print("  LLM_PROVIDER: .env:LLM_PROVIDER")
print("  LLM_MODEL: .env:LLM_MODEL")
if llm_credential:
    print(f"  LLM_API_KEY: {llm_credential_source} (value hidden)")
elif auth_credential:
    print(f"  {auth_credential_source.rsplit(':', 1)[-1]}: {auth_credential_source} (value hidden)")
if base_url:
    print(f"  {base_url_source.rsplit(':', 1)[-1]}: {base_url_source} (value hidden)")
else:
    print("  *_LLM_BASE_URL: not set")

def anthropic_headers(llm_credential, auth_credential):
    headers = {
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    }
    if auth_credential:
        headers['authorization'] = f'Bearer {auth_credential}'
    else:
        headers['x-api-key'] = llm_credential
    return headers

CONFIGS = {
    'anthropic': {
        'url':     lambda b: f"{b or 'https://api.anthropic.com'}/v1/messages",
        'headers': lambda k, t: anthropic_headers(k, t),
        'body':    lambda m: {'model': m, 'max_tokens': 1,
                              'messages': [{'role': 'user', 'content': 'hi'}]},
    },
    'openai': {
        'url':     lambda b: f"{b or 'https://api.openai.com'}/v1/chat/completions",
        'headers': lambda k, t: {'authorization': f'Bearer {k}',
                                 'content-type': 'application/json'},
        'body':    lambda m: {'model': m, 'max_tokens': 1,
                              'messages': [{'role': 'user', 'content': 'hi'}]},
    },
    'deepseek': {
        'url':     lambda b: f"{b or 'https://api.deepseek.com'}/v1/chat/completions",
        'headers': lambda k, t: {'authorization': f'Bearer {k}',
                                 'content-type': 'application/json'},
        'body':    lambda m: {'model': m, 'max_tokens': 1,
                              'messages': [{'role': 'user', 'content': 'hi'}]},
    },
    'qwen': {
        'url':     lambda b: f"{b or 'https://dashscope.aliyuncs.com/compatible-mode'}/v1/chat/completions",
        'headers': lambda k, t: {'authorization': f'Bearer {k}',
                                 'content-type': 'application/json'},
        'body':    lambda m: {'model': m, 'max_tokens': 1,
                              'messages': [{'role': 'user', 'content': 'hi'}]},
    },
}

cfg = CONFIGS.get(provider)
if not cfg:
    print(f"No test template for provider={provider!r}, skipping LLM validation")
    sys.exit(0)

url     = cfg['url'](base_url)
headers = cfg['headers'](llm_credential, auth_credential)
body    = getattr(json, "dumps")(cfg['body'](model)).encode()

try:
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=15):
        print(f"LLM test OK (provider={provider}, model={model})")
        sys.exit(0)
except urllib.error.HTTPError as e:
    err = e.read().decode(errors='replace')
    print(f"LLM test failed (HTTP {e.code}): {err}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"LLM test error: {e}", file=sys.stderr)
    sys.exit(1)
PY
}

stop_unhealthy_managed_server() {
  pid=$(managed_pid 2>/dev/null || true)
  if [ -n "$pid" ]; then
    echo "Stopping unhealthy managed powermem-server PID $pid."
    kill "$pid" 2>/dev/null || true
    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
      echo "Managed server PID $pid is still running; sending SIGKILL."
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
  remove_managed_pid_files
}

announce_dashboard_url() {
  case "$1" in
    */) dashboard_url="${1}dashboard/" ;;
    *) dashboard_url="${1}/dashboard/" ;;
  esac
  echo "Memory dashboard: $dashboard_url"
}

start_backend_server() {
  POWERMEM_START_UV_BIN=$UV_BIN \
  POWERMEM_START_PYTHON=$BOOTSTRAP_PYTHON \
  POWERMEM_START_PACKAGE=$PACKAGE \
  POWERMEM_START_UV_INDEX_URL="${POWERMEM_UV_INDEX_URL:-}" \
  POWERMEM_START_UVX_WITH_ARGS="$UVX_WITH_ARGS" \
  POWERMEM_START_LOG_FILE="$LOG_FILE" \
  POWERMEM_START_PORT=$port \
  POWERMEM_ENV_FILE="$ENV_FILE" \
  "$BOOTSTRAP_PYTHON" - <<'PY'
import os
import shlex
import subprocess

args = [
    os.environ["POWERMEM_START_UV_BIN"],
    "tool",
    "run",
    "--python",
    os.environ["POWERMEM_START_PYTHON"],
]
index_url = os.environ.get("POWERMEM_START_UV_INDEX_URL", "")
if index_url:
    args.extend(["--default-index", index_url])
args.extend(["--from", os.environ["POWERMEM_START_PACKAGE"]])
extra = os.environ.get("POWERMEM_START_UVX_WITH_ARGS", "")
if extra:
    args.extend(shlex.split(extra))
args.extend([
    "powermem-server",
    "--host",
    "127." "0.0.1",
    "--port",
    os.environ["POWERMEM_START_PORT"],
])

env = os.environ.copy()
log = open(os.environ["POWERMEM_START_LOG_FILE"], "ab", buffering=0)
proc = subprocess.Popen(
    args,
    stdin=subprocess.DEVNULL,
    stdout=log,
    stderr=subprocess.STDOUT,
    env=env,
    start_new_session=True,
    close_fds=True,
)
print(proc.pid)
PY
}

if [ -n "${POWERMEM_IMPORT_ENV_FILE:-}" ]; then
  import_env_file "$POWERMEM_IMPORT_ENV_FILE"
  use_imported_server_port
elif truthy "${POWERMEM_INIT_FORCE_RECONFIGURE:-}" || truthy "${POWERMEM_INIT_NO_LLM:-}"; then
  backup_env_file
  echo "Regenerating plugin .env from environment variables and plugin defaults."
  create_env_file
elif [ ! -f "$ENV_FILE" ]; then
  echo "Creating plugin .env from environment variables and plugin defaults."
  create_env_file
else
  echo "Using existing plugin .env: $ENV_FILE"
  echo "Checking managed powermem-server recorded for this env: $(managed_pid_file)"
  if pid_alive; then
    echo "Managed powermem-server is recorded and matches $ENV_FILE: $(managed_pid)"
    managed_url=$(managed_base_url || true)
    if [ -n "$managed_url" ]; then
      base_url=$managed_url
      echo "Managed powermem-server URL: $base_url"
    fi
    if is_healthy "$base_url"; then
      write_runtime_base_url "$base_url"
      echo "Managed PowerMem backend is healthy: $base_url"
      announce_dashboard_url "$base_url"
      echo "Hook will use this backend through $RUNTIME_FILE."
      exit 0
    fi
    echo "Managed powermem-server exists, but health check failed at $base_url; init will stop it and continue."
    stop_unhealthy_managed_server
  else
    echo "No matching managed powermem-server is recorded for $ENV_FILE; init will start one if no healthy backend is found."
    remove_managed_pid_files
  fi
fi
if [ -n "${POWERMEM_INIT_PORT:-}" ]; then
  base_url="http://localhost:$POWERMEM_INIT_PORT"
fi

echo "Validating LLM config..."
if ! validate_llm_config; then
  if truthy "${POWERMEM_INIT_NO_LLM_ON_VALIDATION_FAILURE:-}"; then
    echo "LLM validation failed; falling back to no-LLM mode so the local backend can start." >&2
    echo "Fact extraction, profile extraction, query rewrite, compression, and graph extraction will be skipped until LLM config is repaired." >&2
    backup_env_file
    POWERMEM_INIT_NO_LLM=1
    export POWERMEM_INIT_NO_LLM
    create_env_file
    echo "Validating no-LLM config..."
    validate_llm_config || {
      echo "No-LLM fallback validation failed unexpectedly." >&2
      exit 1
    }
  else
    echo "LLM validation failed. Check the provider, model, API key, and base URL." >&2
    echo "To start a degraded local backend now, re-run with POWERMEM_INIT_NO_LLM_ON_VALIDATION_FAILURE=1." >&2
    echo "To intentionally reconfigure no-LLM mode, run with POWERMEM_INIT_NO_LLM=1 POWERMEM_INIT_FORCE_RECONFIGURE=1." >&2
    exit 1
  fi
fi

db_provider=$(grep '^DATABASE_PROVIDER=' "$ENV_FILE" 2>/dev/null \
  | cut -d= -f2 | tr -d '[:space:]')
db_provider="${db_provider:-sqlite}"
case "$db_provider" in
  oceanbase) PACKAGE="${POWERMEM_INIT_PACKAGE:-powermem[server,seekdb]}" ;;
  *)         PACKAGE="${POWERMEM_INIT_PACKAGE:-powermem[server,extras]}" ;;
esac

# For SQLite backend: probe FTS5/JSON1 support via the bootstrap Python and,
# if the bundled SQLite is too old (< 3.9.0), inject pysqlite3-binary into
# the uvx invocation so PowerMem gets a modern SQLite at runtime.
UVX_WITH_ARGS=""
if [ "$db_provider" != "oceanbase" ]; then
  _sqlite_ok=$("$BOOTSTRAP_PYTHON" -c \
    "import sqlite3; print(sqlite3.sqlite_version_info >= (3,9,0))" 2>/dev/null || echo False)
  if [ "$_sqlite_ok" != "True" ]; then
    _sys_ver=$("$BOOTSTRAP_PYTHON" -c 'import sqlite3; print(sqlite3.sqlite_version)' 2>/dev/null || echo unknown)
    echo "System SQLite $_sys_ver < 3.9.0; injecting pysqlite3-binary into uvx invocation."
    UVX_WITH_ARGS="--with pysqlite3-binary"
  fi
fi

if pid_alive; then
  echo "Managed PowerMem server process is running: $(managed_pid)"
  managed_url=$(managed_base_url || true)
  if [ -n "$managed_url" ]; then
    base_url=$managed_url
  fi
  if is_healthy "$base_url"; then
    write_runtime_base_url "$base_url"
    echo "Managed PowerMem backend is healthy: $base_url"
    announce_dashboard_url "$base_url"
    exit 0
  fi
  echo "Managed server PID exists but health check failed; stopping it before continuing."
  stop_unhealthy_managed_server
fi

if is_healthy "$base_url"; then
  write_runtime_base_url "$base_url"
  echo "External PowerMem backend is healthy: $base_url"
  announce_dashboard_url "$base_url"
  echo "Plugin config is ready. Not starting a managed server."
  exit 0
fi

ensure_uv
configure_uv_index
export_env_file_vars "$ENV_FILE"
echo "Backend package: $PACKAGE"
echo "Backend launcher: uvx --from '$PACKAGE' powermem-server"

if [ -n "${POWERMEM_INIT_PRELOAD_MODEL:-}" ]; then
  echo "POWERMEM_INIT_PRELOAD_MODEL is deprecated; the embedding model is now downloaded automatically by PowerMem at startup."
fi

if [ -n "${POWERMEM_INIT_PORT:-}" ]; then
  port=$POWERMEM_INIT_PORT
  if ! port_free "$port"; then
    describe_port "$port" >&2
    echo "Requested POWERMEM_INIT_PORT=$port is not available. Stop that process or choose another port." >&2
    exit 1
  fi
elif port_free 8848; then
  port=8848
else
  describe_port 8848 >&2
  echo "Port 8848 is occupied and not a healthy PowerMem backend; looking for a free port in 8849-8899." >&2
  port=$(find_free_port 8849 8899) || {
    echo "No free port found in 8849-8899." >&2
    describe_port 8848 >&2
    exit 1
  }
fi

echo "Starting PowerMem server on port $port with uvx"
pid=$(start_backend_server)
write_managed_pid "$pid"
echo "Recorded managed server PID $pid in $PID_FILE"

base_url="http://localhost:$port"

echo "Waiting for backend health: $base_url"
health_timeout=${POWERMEM_INIT_HEALTH_TIMEOUT_SECONDS:-300}
case "$health_timeout" in
  ""|*[!0-9]*) health_timeout=300 ;;
esac
max_checks=$((health_timeout / 2))
if [ "$max_checks" -lt 1 ]; then
  max_checks=1
fi
i=0
while [ "$i" -lt "$max_checks" ]; do
  if is_healthy "$base_url"; then
    write_runtime_base_url "$base_url"
    echo "PowerMem backend is healthy: $base_url"
    announce_dashboard_url "$base_url"
    echo "Hook will use this backend through $RUNTIME_FILE."
    echo "Log: $LOG_FILE"
    exit 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "PowerMem server process exited before it became healthy." >&2
    echo "Check log: $LOG_FILE" >&2
    tail -n 80 "$LOG_FILE" >&2 2>/dev/null || true
    remove_managed_pid_files
    describe_port "$port" >&2
    exit 1
  fi
  i=$((i + 1))
  sleep 2
done

echo "PowerMem server did not become healthy within $((max_checks * 2)) seconds." >&2
echo "Check log: $LOG_FILE" >&2
stop_unhealthy_managed_server
describe_port "$port" >&2
exit 1
