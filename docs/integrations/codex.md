# Codex

Connect Codex to PowerMem with the first-party Codex hook plugin. This path uses Codex lifecycle hooks and the PowerMem HTTP API directly. It does not add an MCP server.

## Recommended setup

First download the code and enter the directory:

```bash
git clone https://github.com/oceanbase/powermem
cd powermem
```

Then install the local Codex plugin:

```bash
codex plugin marketplace add "$(pwd)"
codex plugin add powermem-codex-plugin@powermem-local
```

Start a new Codex thread, open `/hooks`, review the PowerMem hook definitions, and trust them. Then ask Codex:

```text
Use the powermem-codex-plugin init skill to initialize PowerMem.
```

The init skill walks through setup as a short dialog. It first asks whether Codex should use an existing PowerMem backend/cluster, start a local backend, or repair the current setup. Local startup then asks whether to use zero-config no-LLM mode, import an existing PowerMem `.env`, or manually configure providers and credentials. Before running init it also asks whether to configure `POWERMEM_USER_ID` and `POWERMEM_AGENT_ID`. It asks only for the values required by that choice.

The installed plugin follows [`apps/powermem-codex-plugin/SETUP.md`](https://github.com/oceanbase/powermem/blob/main/apps/powermem-codex-plugin/SETUP.md), connects to an existing PowerMem HTTP backend or starts/reuses a local one, and writes runtime state under `~/.powermem/`.

## Existing PowerMem backend

If you already run PowerMem as a shared service or cluster, ask Codex:

```text
Use the powermem-codex-plugin init skill.
I want to connect an existing PowerMem backend.
```

The skill will ask for the base URL, whether an API key is required, and whether to configure `POWERMEM_USER_ID` / `POWERMEM_AGENT_ID`. It writes `~/.powermem/runtime.env`, verifies `GET /api/v1/system/health`, and the hooks then call that backend directly.

## Local PowerMem backend

If you want Codex to manage a local backend, ask Codex:

```text
Use the powermem-codex-plugin init skill.
I want to start a local PowerMem backend.
```

The skill will then guide one of three paths:

1. Zero-config quick start: local SQLite, local embeddings, and no LLM.
2. Import an existing PowerMem `.env` into `~/.powermem/.env`.
3. Manually configure database, LLM, embedding, and port settings.

## How it works

- `UserPromptSubmit` posts to `POST /api/v1/memories/search` and injects relevant results as Codex `additionalContext`.
- `Stop` posts the latest assistant turn summary to `POST /api/v1/memories`.
- `POWERMEM_BASE_URL` defaults to `http://localhost:8848`.
- `POWERMEM_API_KEY`, when set, is sent as `X-API-Key`.
- `POWERMEM_USER_ID` and `POWERMEM_AGENT_ID` scope memory reads/writes. If `POWERMEM_USER_ID` is not configured, the hook falls back to the OS username; `POWERMEM_AGENT_ID` is unset unless configured.

No `codex mcp add` command is needed for this plugin.

## Verify

1. Confirm the backend is healthy:

   ```bash
   . "$HOME/.powermem/runtime.env"
   curl -fsS "${POWERMEM_BASE_URL%/}/api/v1/system/health"
   ```

2. In a new Codex thread, ask something that should match existing memories. When results are found, the `UserPromptSubmit` hook injects a `PowerMem` context block.

3. Finish a turn and confirm a `codex-stop-summary` memory appears in PowerMem.

## Controls

- `POWERMEM_PROMPT_SEARCH=0` disables prompt-time recall.
- `POWERMEM_CODEX_STOP_SAVE=0` disables turn summary writes.
- `POWERMEM_INFER_CODEX_STOP=0` stores Stop summaries without inference.
- `POWERMEM_PROMPT_SEARCH_LIMIT` controls prompt recall result count. Default: `8`.
- `POWERMEM_PROMPT_SEARCH_MAX_CHARS` limits injected context. Default: `24000`.
- `POWERMEM_CODEX_SAVE_MAX_CHARS` limits saved Stop content. Default: `16000`.

## Troubleshooting

- If hooks do not run, start a new Codex thread and review `/hooks`; plugin-bundled hooks must be trusted.
- If no memories are injected, confirm `POWERMEM_BASE_URL` points at a healthy backend and `POWERMEM_PROMPT_SEARCH` is not `0`.
- If writes are missing, confirm `POWERMEM_CODEX_STOP_SAVE` is not `0` and check the local PowerMem server log file.

## Uninstall

For guided cleanup, ask Codex:

```text
Use the powermem-codex-plugin uninstall skill.
```

The uninstall skill first checks status, then walks three progressive layers. It asks one layer at a time and stops when the user does not want to continue deeper.

```text
1. Delete Codex hooks/plugin
2. Delete the local marketplace
3. Delete local PowerMem service configuration
```

Layer 1 keeps the shared backend, marketplace, runtime, config, data, and Claude Code memory access:

```bash
codex plugin remove powermem-codex-plugin 2>/dev/null || true
```

Layer 2 removes the local marketplace only when it was added for this plugin:

```bash
codex plugin marketplace remove powermem-local 2>/dev/null || true
```

Layer 3 touches `~/.powermem` and may affect Claude Code or other clients. Ask whether the backend is shared before stopping service or removing runtime/config/data.

Stop the local service:

```bash
POWERMEM_UNINSTALL_STOP_SERVER=1 sh "$PLUGIN_ROOT/scripts/uninstall.sh"
```

Remove runtime or config:

```bash
POWERMEM_UNINSTALL_REMOVE_RUNTIME=1 sh "$PLUGIN_ROOT/scripts/uninstall.sh"
POWERMEM_UNINSTALL_REMOVE_CONFIG=1 sh "$PLUGIN_ROOT/scripts/uninstall.sh"
```

Delete all local PowerMem data only after explicit confirmation:

```bash
POWERMEM_UNINSTALL_DELETE_DATA=1 \
POWERMEM_UNINSTALL_CONFIRM=delete-powermem-data \
sh "$PLUGIN_ROOT/scripts/uninstall.sh"
```
