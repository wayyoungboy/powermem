---
description: Initialize PowerMem for Claude Code after the plugin is installed. Use when the user asks to set up, initialize, or repair PowerMem.
---

Initialize PowerMem for Claude Code.

Read `apps/claude-code-plugin/SETUP.md`, section "Installed plugin initialization",
and follow only that section.

Do not run the source/developer setup flow from `SETUP.md`: do not build hook
binaries, do not stage the plugin, do not run `claude plugin marketplace add`, do
not run `claude plugin install`, and do not build the dashboard.

Use the plugin scripts as directed by that section:

- `scripts/status.sh`
- `scripts/init.sh`

If the user already has a reachable PowerMem server, configure remote mode
instead of starting a local backend:

```bash
POWERMEM_INIT_REMOTE_BASE_URL=https://powermem.example.com \
POWERMEM_INIT_CONNECTION_MODE=hook \
sh "$CLAUDE_PLUGIN_ROOT/scripts/init.sh"
```

Use `POWERMEM_INIT_CONNECTION_MODE=mcp` for in-chat MCP tools only, or `both`
for both hooks and MCP tools. If the server requires PowerMem API auth, pass
`POWERMEM_INIT_REMOTE_API_KEY`; never print the value.

Remember that `scripts/init.sh` ensures uv and starts the backend with the
uvx-style launcher. Package depends on the storage backend: SQLite (default)
uses `uvx --from 'powermem[server,extras]' powermem-server` (pulls
`sentence-transformers` for the local huggingface embedder); OceanBase uses
`uvx --from 'powermem[server,seekdb]' powermem-server`. If the user is testing
unpublished backend changes, run the script with
`POWERMEM_INIT_PACKAGE='powermem[server,extras] @ git+https://github.com/oceanbase/powermem.git@<branch-or-sha>'`
(SQLite) or the matching `[server,seekdb]` spec (OceanBase) so that value is
passed to `uvx --from` instead of using the default PyPI package.

If values are missing, ask only for the missing values and pass them through
`POWERMEM_INIT_*` environment variables. Never print API keys; mask secrets in
summaries.

The default local embedding model (`all-MiniLM-L6-v2`) is downloaded
automatically by PowerMem at startup — no `init.sh` flag is needed. CN networks
download through ModelScope and bridge into the HuggingFace cache; other networks
download from HuggingFace directly. `POWERMEM_INIT_PRELOAD_MODEL` is deprecated
and now a no-op; do not recommend it.
