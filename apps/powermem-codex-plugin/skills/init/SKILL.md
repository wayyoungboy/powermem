---
name: init
description: Initialize the PowerMem Codex hook plugin by connecting to an existing PowerMem backend or starting a local backend.
---

# PowerMem Codex Init

Use when the user wants to initialize, repair, or connect the PowerMem Codex hook plugin.

1. Read `apps/powermem-codex-plugin/SETUP.md`, especially "Installed Plugin Initialization".
2. Resolve `PLUGIN_ROOT` from `PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, or the installed plugin path under `~/.codex/plugins`.
3. Export `NO_PROXY` and `no_proxy` so localhost and loopback traffic does not go through a proxy before local health checks.
4. Run `sh "$PLUGIN_ROOT/scripts/status.sh"` first.
5. Use a guided multi-turn flow in the user's language. Ask only the next missing decision or value, wait for the user's answer, then continue. Do not ask for all configuration values in one message, and do not re-ask for values the user already provided.
6. First ask the user to choose the backend mode unless they already made it clear:
   - existing PowerMem backend/cluster/service
   - local PowerMem backend on this machine
   - repair/check the current setup
7. If the user chooses an existing/remote PowerMem backend, cluster, service, or gives an HTTP(S) base URL, do not start a local backend. Guide the user through these short follow-up turns:
   - Ask for the PowerMem base URL, for example `https://powermem.example.com`.
   - Ask whether the backend requires an API key for `X-API-Key`. If yes, ask them to provide it or confirm it is already available as `POWERMEM_API_KEY`; never print the key back.
   - Summarize the non-secret choices and ask for confirmation before running the command.
8. Before running any connect or local init command, ask whether the user wants to configure memory identity/scope:
   - skip identity config: let the hook use the OS username as the default user id and leave agent id unset
   - configure `POWERMEM_USER_ID` only
   - configure both `POWERMEM_USER_ID` and `POWERMEM_AGENT_ID`

   Ask only for the values needed by that choice. Recommend the OS username or company account id for `POWERMEM_USER_ID` when unsure. Recommend `codex` for `POWERMEM_AGENT_ID` when the user wants Codex-specific memory scope. Include selected identity values in the non-secret summary before running the command.
9. To connect an existing backend, run:

   ```bash
   POWERMEM_CONNECT_BASE_URL="<base-url>" \
   POWERMEM_API_KEY="<api-key-if-needed>" \
   POWERMEM_USER_ID="<user-id-if-configured>" \
   POWERMEM_AGENT_ID="<agent-id-if-configured>" \
   sh "$PLUGIN_ROOT/scripts/init.sh"
   ```

   Omit empty optional variables rather than printing placeholders. The script must verify `/api/v1/system/health`, write `~/.powermem/runtime.env`, and not start a managed local `powermem-server`.
10. If status is already healthy and the base URL is the intended backend, still ask whether the user wants to configure or update `POWERMEM_USER_ID` / `POWERMEM_AGENT_ID` unless those values are already configured and acceptable. If no identity update is needed, report the base URL and stop.
11. If the user chooses a local backend, ask one follow-up choice before running local init:
    - zero-config quick start
    - import an existing PowerMem `.env`
    - manually configure providers and credentials
12. For zero-config local quick start, explain that Codex will start a local SQLite backend with local embeddings and `LLM_PROVIDER=noop`. Basic memory add/search/update/delete works, while fact extraction, profile extraction, query rewrite, compression, and graph extraction are skipped until LLM config is repaired. Include selected `POWERMEM_USER_ID` / `POWERMEM_AGENT_ID` variables when configured. If no plugin `.env` exists, run:

    ```bash
    POWERMEM_USER_ID="<user-id-if-configured>" \
    POWERMEM_AGENT_ID="<agent-id-if-configured>" \
    POWERMEM_INIT_NO_LLM=1 sh "$PLUGIN_ROOT/scripts/init.sh"
    ```

    If an existing plugin `.env` is present and the user confirms replacing it, run:

    ```bash
    POWERMEM_USER_ID="<user-id-if-configured>" \
    POWERMEM_AGENT_ID="<agent-id-if-configured>" \
    POWERMEM_INIT_NO_LLM=1 POWERMEM_INIT_FORCE_RECONFIGURE=1 sh "$PLUGIN_ROOT/scripts/init.sh"
    ```

13. For importing an existing local config, ask for the source `.env` path. Confirm the source path and destination `~/.powermem/.env` before running the command. Do not print or summarize secret values from the file. Include selected `POWERMEM_USER_ID` / `POWERMEM_AGENT_ID` variables when configured. Run:

    ```bash
    POWERMEM_USER_ID="<user-id-if-configured>" \
    POWERMEM_AGENT_ID="<agent-id-if-configured>" \
    POWERMEM_IMPORT_ENV_FILE="<path-to-existing-env>" sh "$PLUGIN_ROOT/scripts/init.sh"
    ```

    The script must back up any existing plugin `.env`, copy the imported file to `~/.powermem/.env`, validate it, and start or reuse the local backend.
14. For manual local configuration, ask only the next missing value, one turn at a time:
    - database provider: recommend `sqlite` for local Codex usage; mention `oceanbase` only for users who want the embedded seekdb/OceanBase path
    - LLM mode/provider: `anthropic`, `openai`, `qwen`, `deepseek`, `ollama`, `vllm`, or no-LLM
    - model name
    - API key or auth token if the selected provider requires one; never print it back
    - base URL only when the provider needs a custom endpoint or bearer-token gateway
    - embedding provider only if they do not want the default local HuggingFace embedding
    - optional local port only if they do not want `8848`

    Summarize non-secret choices and ask for confirmation before running `sh "$PLUGIN_ROOT/scripts/init.sh"` with the corresponding `POWERMEM_INIT_*` environment variables. Use `POWERMEM_INIT_NO_LLM=1` when the user explicitly picks no-LLM.
15. If the user wants a local backend and it is missing or unhealthy, run the local init command for their selected local setup path.
16. If local init fails because LLM validation fails and the user has not provided replacement credentials, ask whether to retry in no-LLM degraded mode. If they agree, run `POWERMEM_INIT_NO_LLM_ON_VALIDATION_FAILURE=1 sh "$PLUGIN_ROOT/scripts/init.sh"` and explain that fact extraction, profile extraction, query rewrite, compression, and graph extraction are disabled until LLM config is repaired.
17. If the user chooses repair/check, report the current status first, then ask whether to reconnect an existing backend, reinitialize local backend, import an existing `.env`, switch to zero-config local mode, update memory identity/scope, or leave the current configuration unchanged.
18. After init/connect, run `sh "$PLUGIN_ROOT/scripts/status.sh"` again and verify health with `curl --noproxy '*' -fsS "${POWERMEM_BASE_URL%/}/api/v1/system/health"` after sourcing `~/.powermem/runtime.env` when present. If an API key is configured, include `-H "X-API-Key: $POWERMEM_API_KEY"` but never print the key. Report whether `POWERMEM_USER_ID` and `POWERMEM_AGENT_ID` are configured; if skipped, explain that user id falls back to the OS username and agent id is unset.
19. Do not configure or add a Codex MCP server. This plugin uses Codex hooks and the PowerMem HTTP API.
20. Never print secrets. Mask API keys and auth tokens in any status summary.
