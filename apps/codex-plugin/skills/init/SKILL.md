---
name: init
description: Initialize PowerMem for Codex after the plugin is installed.
user-invocable: true
---

Initialize PowerMem for Codex.

First locate the installed plugin root. Prefer `PLUGIN_ROOT`, then
`CLAUDE_PLUGIN_ROOT`, then `CODEX_PLUGIN_ROOT`; if none are set, search under
`${CODEX_HOME:-$HOME/.codex}/plugins/cache/powermem/memory-powermem/*`.

Run `scripts/status.sh` from that plugin root first. If config or
`powermem-mcp` is missing, run `scripts/init.sh` from the same root.

```bash
for root in "${PLUGIN_ROOT:-}" "${CLAUDE_PLUGIN_ROOT:-}" "${CODEX_PLUGIN_ROOT:-}" "${CODEX_HOME:-$HOME/.codex}/plugins/cache/powermem/memory-powermem"/* "$HOME/.codex/plugins/cache/powermem/memory-powermem"/*; do
  if [ -f "$root/scripts/init.sh" ]; then
    sh "$root/scripts/init.sh"
    exit $?
  fi
done
echo "PowerMem Codex plugin root not found. Reinstall memory-powermem@powermem." >&2
exit 1
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
- `POWERMEM_INIT_ENABLE_HOOKS=0` to skip mirroring bundled plugin hooks into
  `~/.codex/hooks.json`

Remember that init installs `powermem` from PyPI by default. For unpublished
backend changes, run the script with:

```bash
POWERMEM_INIT_PACKAGE='powermem @ git+https://github.com/oceanbase/powermem.git@<branch-or-sha>' \
  sh "$PLUGIN_ROOT/scripts/init.sh"
```

After init succeeds, tell the user to restart Codex so it reloads the installed
plugin's bundled `.mcp.json`. Explain that init also installs user-scope
fallback hooks by default for Codex hosts that do not dispatch plugin-local
hooks yet.
