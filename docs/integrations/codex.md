# Codex

Connect Codex CLI or the Codex app to PowerMem with the native
`memory-powermem` plugin, bundled lifecycle hooks, and an explicit MCP server
entry for tools.

The Codex plugin installs PowerMem skills and reuses the same backend bootstrap
as the Claude Code plugin. It also bundles Codex hooks from
`apps/agent-plugin/hooks/codex-hooks.json` so new threads can retrieve relevant
memories and save concise turn summaries. MCP is still wired explicitly after
init writes `~/.powermem/runtime.env`.

## Recommended Setup

Install the PowerMem marketplace and plugin:

```bash
codex plugin marketplace add oceanbase/powermem
codex plugin add memory-powermem@powermem
```

For branch testing from a fork:

```bash
codex plugin remove memory-powermem 2>/dev/null || true
codex plugin marketplace remove powermem 2>/dev/null || true
codex plugin marketplace add https://github.com/<owner>/powermem.git --ref <branch>
codex plugin add memory-powermem@powermem
```

Start a new Codex thread after installing or updating the plugin so Codex loads
the new skills and hooks. Review and trust the plugin hooks when Codex asks, or
open `/hooks` and trust the PowerMem hook definitions there. Then ask Codex:

```text
Use the memory-powermem init skill to initialize PowerMem.
```

The init skill prepares shared local state under `~/.powermem/`:

```text
~/.powermem/.env
~/.powermem/runtime.env
~/.powermem/powermem.pid
server log under the local state directory
~/.powermem/venv/
```

After init succeeds, wire Codex MCP to the managed server:

```bash
. "$HOME/.powermem/runtime.env"
codex mcp remove powermem 2>/dev/null || true
codex mcp add powermem --url "${POWERMEM_BASE_URL%/}/mcp"
```

## Bundled Hooks

The plugin manifest points Codex at `hooks/codex-hooks.json`. The hook commands
run `hooks/run-hook.sh`, which executes the packaged `powermem-hook` binary and
reads the runtime endpoint from `~/.powermem/runtime.env`.

Default behavior:

- `SessionStart` searches PowerMem for project/session context and injects it as
  Codex `additionalContext`.
- `UserPromptSubmit` searches PowerMem for memories relevant to the current
  prompt and injects them as `additionalContext`.
- `Stop` saves the latest assistant turn summary to PowerMem.
- `PostToolUse` is registered but does not save tool inputs or outputs unless
  explicitly enabled with `POWERMEM_CODEX_POST_TOOL_SAVE=1`.

Hook environment controls:

```bash
# Disable prompt-time recall.
export POWERMEM_PROMPT_SEARCH=0

# Disable SessionStart recall.
export POWERMEM_CODEX_SESSION_SEARCH=0

# Disable Stop summary writes.
export POWERMEM_CODEX_STOP_SAVE=0

# Opt in to saving selected PostToolUse summaries.
export POWERMEM_CODEX_POST_TOOL_SAVE=1
```

Codex requires non-managed command hooks to be reviewed and trusted. If a hook
definition changes after an update, open `/hooks` again and trust the new
PowerMem hook hash.

## Prerequisites

- Codex CLI or Codex app with plugin support. CLI setup uses the
  `codex plugin` and `codex mcp` commands.
- A supported Python runtime for the PowerMem backend. The init script creates
  `~/.powermem/venv` and installs `powermem` there.
- Anthropic credentials available from the environment or `~/.claude/settings.json`.
  `ANTHROPIC_API_KEY` works by itself. `ANTHROPIC_AUTH_TOKEN` must be paired with
  `ANTHROPIC_BASE_URL`.

## Manual MCP Only

If you do not want the Codex plugin skills, you can still connect Codex as a
plain MCP client:

```bash
codex mcp add powermem --url http://localhost:8848/mcp
```

Use this only when a PowerMem HTTP server is already running. The native plugin
path is preferred because the `init`, `status`, `stop`, and `reset` skills manage
the local server lifecycle for you.

## Verify

1. Confirm the managed server is healthy:

   ```bash
   . "$HOME/.powermem/runtime.env"
   curl -fsS "${POWERMEM_BASE_URL%/}/api/v1/system/health"
   ```

2. Confirm Codex has the MCP entry:

   ```bash
   codex mcp list
   ```

3. Open `/hooks` and confirm the PowerMem hooks are trusted.

4. In Codex, ask it to remember a probe such as
   `PowerMem Codex probe: dragonfruit-zx9`, then search for `dragonfruit-zx9`.

## Troubleshooting

- If the plugin skills do not appear, start a new Codex thread after
  `codex plugin add`.
- If the hooks do not run, open `/hooks`, trust the PowerMem hook definitions,
  and start a new thread.
- If MCP uses the wrong port, reload `~/.powermem/runtime.env` and re-run
  `codex mcp remove powermem` followed by `codex mcp add`.
- If the server fails to start, read the server log under the local state directory.
- If package installation is slow in CN networks, init detects the current
  machine region and adds the Tsinghua PyPI mirror for `pip install`.

## Uninstall

Remove the MCP entry and plugin:

```bash
codex mcp remove powermem
codex plugin remove memory-powermem 2>/dev/null || true
```

If your Codex CLI does not expose `plugin remove`, use `codex plugin list` to
inspect the installed plugin and remove it through the CLI version's supported
plugin management command.
