# PowerMem Plugin for Codex

This plugin helps Codex connect to PowerMem through bundled MCP, lifecycle
hooks, and user-invocable skills. The plugin installs the Python backend into a
plugin-local virtualenv; the installed plugin itself provides `.mcp.json`,
`hooks/hooks.codex.json`, and memory skills.

## Install

When this repository marketplace is available to Codex:

```text
codex plugin marketplace add oceanbase/powermem
codex plugin add memory-powermem@powermem
```

During local development, install from this repository path or marketplace as
supported by your Codex build, then ask Codex:

```text
Use memory-powermem to initialize PowerMem for Codex.
```

The init skill runs:

```bash
sh "$CODEX_PLUGIN_ROOT/scripts/init.sh"
```

To also mirror the bundled hooks into user-scope Codex hooks as a fallback:

```bash
POWERMEM_INIT_ENABLE_HOOKS=1 sh "$CODEX_PLUGIN_ROOT/scripts/init.sh"
```

## Backend Package

By default, init installs the backend with:

```bash
pip install powermem "fastmcp>=1.0"
```

To test unpublished backend code:

```bash
POWERMEM_INIT_PACKAGE='powermem @ git+https://github.com/oceanbase/powermem.git@<branch-or-sha>' \
  sh "$CODEX_PLUGIN_ROOT/scripts/init.sh"
```

## Commands

Ask Codex to use these plugin skills:

- Initialize PowerMem memory for Codex.
- Check PowerMem status.
- Stop PowerMem plugin processes.
- Reset PowerMem plugin data.
- Recall relevant PowerMem memories.
- Remember this context in PowerMem.

The plugin also bundles these Codex lifecycle hooks:

- `SessionStart`: records a session start marker.
- `UserPromptSubmit`: recalls relevant memories and captures the prompt.
- `PreToolUse` / `PostToolUse`: captures selected tool activity.
- `PreCompact`: preserves compacted context.
- `Stop`: saves session-end context.

## Data

Plugin-local files live under:

```text
${CODEX_PLUGIN_DATA:-$HOME/.codex/plugins/data/memory-powermem}/
```

The plugin manifest points Codex at bundled MCP and hook config. The init script
does not need to write `~/.codex/context.json`. When fallback hooks are enabled,
it adds PowerMem-owned entries to `~/.codex/hooks.json` and preserves unrelated
hooks.

The repository marketplace manifests live at `.agents/plugins/marketplace.json`
and `.codex-plugin/marketplace.json`. The plugin manifest lives at
`apps/codex-plugin/.codex-plugin/plugin.json`.
