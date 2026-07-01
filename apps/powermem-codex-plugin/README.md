# PowerMem for Codex

PowerMem for Codex is a native Codex plugin that uses lifecycle hooks instead of MCP.

- `UserPromptSubmit` calls the PowerMem HTTP API (`POST /api/v1/memories/search`) and injects relevant memories as Codex `additionalContext`.
- `UserPromptSubmit` can also save narrow user-stated facts such as durable preferences, so no-LLM mode can still remember simple statements like "I like beef."
- `Stop` saves the latest assistant turn summary through `POST /api/v1/memories` by default. Raw `Codex turn summary` records are filtered from prompt recall unless explicitly enabled.
- The backend is managed by `scripts/init.sh`, `status.sh`, and `stop.sh` and stores runtime state under `~/.powermem/`.

## Local Install

From the PowerMem repository root:

```bash
codex plugin marketplace add "$(pwd)"
codex plugin add powermem-codex-plugin@powermem-local
```

Start a new Codex thread after installing. Open `/hooks`, review the PowerMem hook definitions, and trust them. Then ask Codex:

```text
Use the powermem-codex-plugin init skill to initialize PowerMem.
```

This plugin does not add `mcpServers` and does not require `codex mcp add`.

## Existing PowerMem Backend

To connect Codex hooks to an existing PowerMem HTTP backend or cluster, run the init skill with connection settings instead of starting a local backend:

```bash
POWERMEM_CONNECT_BASE_URL="https://powermem.example.com" \
POWERMEM_API_KEY="..." \
POWERMEM_USER_ID="your-user-id" \
POWERMEM_AGENT_ID="codex" \
sh "$PLUGIN_ROOT/scripts/init.sh"
```

The script verifies `/api/v1/system/health`, writes `~/.powermem/runtime.env`, and leaves local `powermem-server` management alone.

## Memory Identity

During init, the skill asks whether to configure memory identity/scope:

1. Skip identity config: use the OS username as the default user id and leave agent id unset.
2. Configure `POWERMEM_USER_ID` only.
3. Configure both `POWERMEM_USER_ID` and `POWERMEM_AGENT_ID`.

Use `POWERMEM_AGENT_ID=codex` when Codex memories should be separated from other agents.

## Local PowerMem Backend

For a backend managed on this machine, the init skill asks how to configure it:

1. Zero-config quick start: local SQLite, local embeddings, and `LLM_PROVIDER=noop`.
2. Import an existing PowerMem `.env` into `~/.powermem/.env`.
3. Manually configure database, LLM, embedding, and port settings through `POWERMEM_INIT_*` variables.

Direct commands:

```bash
# Zero-config local backend.
POWERMEM_INIT_NO_LLM=1 sh "$PLUGIN_ROOT/scripts/init.sh"

# Import an existing PowerMem .env.
POWERMEM_IMPORT_ENV_FILE="/path/to/existing/.env" sh "$PLUGIN_ROOT/scripts/init.sh"

# Manual/default local init from env vars and plugin defaults.
sh "$PLUGIN_ROOT/scripts/init.sh"
```

## Uninstall

Ask Codex to use the uninstall skill for guided cleanup:

```text
Use the powermem-codex-plugin uninstall skill.
```

The uninstall flow has three progressive layers: delete Codex hooks/plugin, optionally delete the local marketplace, then optionally delete local PowerMem service configuration under `~/.powermem`.

## Runtime Controls

```bash
# Disable prompt-time recall.
export POWERMEM_PROMPT_SEARCH=0

# Disable Stop summary writes.
export POWERMEM_CODEX_STOP_SAVE=0

# Disable narrow user-statement writes from UserPromptSubmit.
export POWERMEM_USER_FACT_SAVE=0

# Store Stop summaries as raw content instead of inferred memories.
export POWERMEM_INFER_CODEX_STOP=0

# Allow raw Stop summaries to be injected during prompt recall.
export POWERMEM_INCLUDE_RAW_CODEX_STOP_SUMMARIES=1

# Connect hooks to an existing backend during init.
export POWERMEM_CONNECT_BASE_URL=https://powermem.example.com

# Scope memories to a user or agent during init/runtime.
export POWERMEM_USER_ID=your-user-id
export POWERMEM_AGENT_ID=codex

# Import an existing .env before starting the local backend.
export POWERMEM_IMPORT_ENV_FILE=/path/to/existing/.env

# Remove hook runtime state during uninstall while keeping memories/config.
export POWERMEM_UNINSTALL_REMOVE_RUNTIME=1

# Remove local backend config during uninstall while keeping memories/data.
export POWERMEM_UNINSTALL_REMOVE_CONFIG=1
```

## Files

- `.codex-plugin/plugin.json` - Codex plugin manifest.
- `hooks/hooks.json` - bundled Codex hook configuration.
- `hooks/run-hook.sh` / `hooks/run-hook.ps1` - platform launchers for the native hook binary.
- `hooks/bin/` - prebuilt hook binaries.
- `skills/` - setup, status, and stop workflows for Codex.
