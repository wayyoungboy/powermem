# PowerMem for Codex Setup

This guide is for Codex app and Codex CLI. It sets up PowerMem through Codex lifecycle hooks, not MCP.

## Installed Plugin Initialization

Use this section after `powermem-codex-plugin` is installed in Codex.

1. Start a new Codex thread so the plugin skills and hooks are loaded.
2. Open `/hooks`, review the PowerMem `UserPromptSubmit` and `Stop` hooks, and trust them.
3. Resolve the installed plugin root:

   ```bash
   if [ -z "${PLUGIN_ROOT:-}" ]; then
     PLUGIN_ROOT="${CODEX_PLUGIN_ROOT:-}"
   fi

   if [ -z "${PLUGIN_ROOT:-}" ]; then
     PLUGIN_ROOT=$(
       find "$HOME/.codex/plugins" "$HOME/.codex/plugins/cache" \
         -maxdepth 8 -type d -name scripts 2>/dev/null |
       while IFS= read -r scripts_dir; do
         case "$scripts_dir" in
           *powermem-codex-plugin*) dirname "$scripts_dir"; break ;;
         esac
       done
     )
   fi
   ```

4. Check status:

   ```bash
   sh "$PLUGIN_ROOT/scripts/status.sh"
   ```

5. The init skill should guide setup through short choices instead of asking for every value at once:

   ```text
   Which backend should Codex use?
   1. Existing PowerMem backend or cluster
   2. Local PowerMem backend on this machine
   3. Repair or check the current setup
   ```

   For an existing backend, the skill asks follow-up questions for the base URL and whether an API key is required. For a local backend, it asks one more choice:

   ```text
   How should the local backend be configured?
   1. Zero-config quick start
   2. Import an existing PowerMem .env
   3. Manually configure providers and credentials
   ```

   Before running any connect or local init command, the skill asks whether to configure memory identity/scope:

   ```text
   Configure memory identity?
   1. Skip: use OS username as user id, leave agent id unset
   2. Configure POWERMEM_USER_ID only
   3. Configure POWERMEM_USER_ID and POWERMEM_AGENT_ID
   ```

   Use `POWERMEM_USER_ID` to scope memories to a person/account. Use `POWERMEM_AGENT_ID`, commonly `codex`, when Codex memories should be separated from other agents.

6. To connect an existing PowerMem HTTP backend or cluster, provide its base URL and optional auth/identity settings:

   ```bash
   POWERMEM_CONNECT_BASE_URL="https://powermem.example.com" \
   POWERMEM_API_KEY="..." \
   POWERMEM_USER_ID="your-user-id" \
   POWERMEM_AGENT_ID="codex" \
   sh "$PLUGIN_ROOT/scripts/init.sh"
   ```

   Omit `POWERMEM_API_KEY`, `POWERMEM_USER_ID`, or `POWERMEM_AGENT_ID` when not configured. This mode writes `~/.powermem/runtime.env`, verifies `/api/v1/system/health`, and does not start a managed local `powermem-server`.

7. If you want a local backend and it is missing or unhealthy, choose one local setup path.

   Zero-config quick start creates a local SQLite backend with local HuggingFace embeddings and `LLM_PROVIDER=noop`:

   ```bash
   POWERMEM_USER_ID="your-user-id" \
   POWERMEM_AGENT_ID="codex" \
   POWERMEM_INIT_NO_LLM=1 sh "$PLUGIN_ROOT/scripts/init.sh"
   ```

   Omit `POWERMEM_USER_ID` and `POWERMEM_AGENT_ID` when you choose the default identity behavior. In no-LLM mode, basic memory add/search/update/delete works while fact extraction, profile extraction, query rewrite, compression, and graph extraction are skipped until you repair the LLM configuration. If you intentionally want to replace an existing `~/.powermem/.env` with zero-config settings, add `POWERMEM_INIT_FORCE_RECONFIGURE=1`.

   To import an existing PowerMem `.env`, pass its path:

   ```bash
   POWERMEM_USER_ID="your-user-id" \
   POWERMEM_AGENT_ID="codex" \
   POWERMEM_IMPORT_ENV_FILE="/path/to/existing/.env" sh "$PLUGIN_ROOT/scripts/init.sh"
   ```

   Omit identity variables when you choose the default identity behavior. This backs up any existing `~/.powermem/.env`, copies the imported config into place, validates it, and starts or reuses the local backend. Do not print API keys or tokens from the imported file.

   To configure manually, provide the relevant `POWERMEM_INIT_*` variables before running init. For example:

   ```bash
   POWERMEM_INIT_DATABASE_PROVIDER=sqlite \
   POWERMEM_INIT_LLM_PROVIDER=anthropic \
   POWERMEM_INIT_LLM_MODEL=claude-sonnet-4-5 \
   POWERMEM_INIT_LLM_API_KEY="..." \
   POWERMEM_USER_ID="your-user-id" \
   POWERMEM_AGENT_ID="codex" \
   sh "$PLUGIN_ROOT/scripts/init.sh"
   ```

   For default local initialization from available environment variables and plugin defaults:

   ```bash
   sh "$PLUGIN_ROOT/scripts/init.sh"
   ```

   If LLM validation fails and you want the local HTTP backend available immediately, start in no-LLM degraded mode:

   ```bash
   POWERMEM_INIT_NO_LLM_ON_VALIDATION_FAILURE=1 sh "$PLUGIN_ROOT/scripts/init.sh"
   ```

   In no-LLM mode, basic memory add/search/update/delete works while fact extraction, profile extraction, query rewrite, compression, and graph extraction are skipped until you repair the LLM configuration.

For a managed local backend, the init script creates or reuses:

```text
~/.powermem/.env
~/.powermem/runtime.env
~/.powermem/powermem.pid
local PowerMem server log file
~/.powermem/seekdb_data/
```

Do not run `codex mcp add` for this plugin. The hooks call `POWERMEM_BASE_URL` directly.

## Local Repository Install

From the PowerMem repository root:

```bash
codex plugin marketplace add "$(pwd)"
codex plugin add powermem-codex-plugin@powermem-local
```

Then start a new Codex thread and run the installed plugin initialization above.

## Verify

1. Confirm the backend is healthy:

   ```bash
   . "$HOME/.powermem/runtime.env"
   curl -fsS "${POWERMEM_BASE_URL%/}/api/v1/system/health"
   ```

2. In a new Codex thread, ask something that should match existing memories. The `UserPromptSubmit` hook should inject a `PowerMem` context block when results are found.

3. Finish a turn and confirm a `codex-stop-summary` memory appears in PowerMem. In no-LLM mode, raw Stop summaries are still stored, but they are filtered from prompt-time recall by default.

## Controls

- `POWERMEM_PROMPT_SEARCH=0` disables prompt-time recall.
- `POWERMEM_CODEX_STOP_SAVE=0` disables turn summary writes.
- `POWERMEM_INFER_CODEX_STOP=0` stores Stop summaries without inference.
- `POWERMEM_USER_FACT_SAVE=0` disables narrow user-statement writes from `UserPromptSubmit`.
- `POWERMEM_INCLUDE_RAW_CODEX_STOP_SUMMARIES=1` allows raw `Codex turn summary` records to be injected during prompt recall.
- `POWERMEM_BASE_URL` overrides the backend URL. Default: `http://localhost:8848`.
- `POWERMEM_CONNECT_BASE_URL` tells `init.sh` to connect an existing backend and skip local server startup.
- `POWERMEM_API_KEY` sends `X-API-Key` to the PowerMem HTTP API.
- `POWERMEM_USER_ID` scopes memories for a user.
- `POWERMEM_AGENT_ID` scopes memories for an agent, usually `codex`.
- `POWERMEM_IMPORT_ENV_FILE` imports an existing PowerMem `.env` into `~/.powermem/.env` before starting the local backend.
- `POWERMEM_INIT_NO_LLM=1` intentionally creates a zero-config local no-LLM backend.
- `POWERMEM_INIT_NO_LLM_ON_VALIDATION_FAILURE=1` falls back to a degraded no-LLM local backend when LLM validation fails.
- `POWERMEM_INIT_FORCE_RECONFIGURE=1` regenerates `~/.powermem/.env` after backing up the old file.
