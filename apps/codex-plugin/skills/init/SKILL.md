---
name: init
description: Initialize PowerMem for Codex after the plugin is installed.
user-invocable: true
---

Initialize PowerMem for Codex.

Run `sh "${CODEX_PLUGIN_ROOT}/scripts/status.sh"` first when available. If
`CODEX_PLUGIN_ROOT` is unavailable but `CLAUDE_PLUGIN_ROOT` is set, use that
plugin root instead. If config or `powermem-mcp` is missing, run:

```bash
sh "${CODEX_PLUGIN_ROOT}/scripts/init.sh"
```

If init reports missing values, ask only for those missing values and pass them
through `POWERMEM_INIT_*` environment variables. Never invent credentials and
never print API keys.

Use these variables when needed:

- `POWERMEM_INIT_LLM_PROVIDER`
- `POWERMEM_INIT_LLM_MODEL`
- `POWERMEM_INIT_LLM_API_KEY`
- `POWERMEM_INIT_LLM_BASE_URL`
- `POWERMEM_INIT_PACKAGE`
- `POWERMEM_INIT_PYTHON`
- `POWERMEM_INIT_ENABLE_HOOKS=1` to mirror the bundled plugin hooks into
  `~/.codex/hooks.json` as a user-scope fallback

Remember that init installs `powermem` from PyPI by default. For unpublished
backend changes, run the script with:

```bash
POWERMEM_INIT_PACKAGE='powermem @ git+https://github.com/oceanbase/powermem.git@<branch-or-sha>' \
  sh "${CODEX_PLUGIN_ROOT}/scripts/init.sh"
```

After init succeeds, tell the user to restart Codex so it reloads the installed
plugin's bundled `.mcp.json` and hooks.

If the user asks for hook-based memory, re-run init with
`POWERMEM_INIT_ENABLE_HOOKS=1`. Explain that the plugin already bundles hooks,
and this option installs a user-scope fallback for Codex builds that do not
dispatch plugin-local hooks.
