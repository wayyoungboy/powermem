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

The init skill locates the installed plugin root and runs:

```bash
sh "$PLUGIN_ROOT/scripts/init.sh"
```

It also mirrors the bundled hooks into `~/.codex/hooks.json` by default. This is
a user-scope fallback for Codex hosts that do not dispatch plugin-local hooks
yet. To skip the fallback:

```bash
POWERMEM_INIT_ENABLE_HOOKS=0 sh "$PLUGIN_ROOT/scripts/init.sh"
```

## Backend Package

By default, init installs the backend with:

```bash
pip install powermem "fastmcp>=1.0"
```

To test unpublished backend code:

```bash
POWERMEM_INIT_PACKAGE='powermem @ git+https://github.com/oceanbase/powermem.git@<branch-or-sha>' \
  sh "$PLUGIN_ROOT/scripts/init.sh"
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
does not need to write `~/.codex/context.json`. It also adds PowerMem-owned
fallback entries to `~/.codex/hooks.json` by default and preserves unrelated
hooks.

The Codex marketplace is exposed through `.agents/plugins/marketplace.json`,
which points at this bundled plugin. The repository also keeps
`.codex-plugin/marketplace.json` for Codex builds that probe that compatible
location. The explicit `.agents` catalog is intentional because this repository
also has a separate Claude Code marketplace under `.claude-plugin/`. The plugin
manifest lives at `apps/codex-plugin/.codex-plugin/plugin.json`.
