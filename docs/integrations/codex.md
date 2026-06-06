# Codex

Connect Codex to PowerMem through bundled MCP, lifecycle hooks, and skills. The
Codex plugin path installs a plugin-local backend while the plugin bundle
provides `.mcp.json`, hook configuration, and memory skills. The generic
[PowerMem MCP client setup](https://github.com/oceanbase/powermem/blob/main/apps/mcp-client/SETUP.md)
remains available when you want to wire Codex manually or share one MCP server
with multiple clients.

## Plugin setup

When the PowerMem marketplace is available to Codex:

```text
codex plugin marketplace add oceanbase/powermem
codex plugin add memory-powermem@powermem
```

The repository includes both Codex marketplace manifest locations used in the
ecosystem: `.agents/plugins/marketplace.json` per the current Codex docs and
`.codex-plugin/marketplace.json` for compatibility with agentmemory-style
repositories.

Then ask Codex:

```text
Use memory-powermem to initialize PowerMem for Codex.
```

The plugin init flow:

1. Creates a plugin-local venv under `~/.codex/plugins/data/memory-powermem/`.
2. Installs the Python backend and MCP runtime dependencies with
   `pip install powermem "fastmcp>=1.0"` by default.
3. Creates a plugin-local `.env`.
4. Lets Codex load the plugin's bundled `.mcp.json` and `hooks/hooks.codex.json`.

The plugin bundles these lifecycle hooks:

- `SessionStart`
- `UserPromptSubmit`
- `PreToolUse`
- `PostToolUse`
- `PreCompact`
- `Stop`

To also mirror those hooks into `~/.codex/hooks.json` as a user-scope fallback:

```bash
POWERMEM_INIT_ENABLE_HOOKS=1 sh "$CODEX_PLUGIN_ROOT/scripts/init.sh"
```

Use the fallback for Codex builds that do not dispatch plugin-local hooks. The
fallback preserves unrelated hooks and replaces only prior PowerMem-owned hook
entries.

If you are testing backend code that has not been published to PyPI, run init
with:

```bash
POWERMEM_INIT_PACKAGE='powermem @ git+https://github.com/oceanbase/powermem.git@<branch-or-sha>' \
  sh "$CODEX_PLUGIN_ROOT/scripts/init.sh"
```

Restart Codex after init so it reloads the installed plugin's MCP and hooks.

## Recommended setup — let your MCP client agent set it up

Use this path if you are not using the Codex plugin.

First download the code and enter the directory:

```bash
git clone https://github.com/oceanbase/powermem
cd powermem
```

Then open the AI agent window where you run Codex and paste this one line:

```text
Read and follow apps/mcp-client/SETUP.md to setup PowerMem
```

The agent follows [`apps/mcp-client/SETUP.md`](https://github.com/oceanbase/powermem/blob/main/apps/mcp-client/SETUP.md), runs `powermem-mcp` directly, and updates only the Codex MCP configuration.

## Manual setup prerequisites

- Codex installed and able to read `~/.codex/context.json`.
- A running PowerMem MCP endpoint or local `powermem-mcp` command.
- PowerMem configured with your LLM provider, API key, and model.

## Manual setup

Use this section only when you want to wire Codex by hand.

### Configure

Add PowerMem to `~/.codex/context.json`:

```json
{
  "mcpServers": {
    "powermem": {
      "url": "http://localhost:8848/mcp"
    }
  }
}
```

If the PowerMem MCP endpoint requires auth, add the matching header or pass
`POWERMEM_API_KEY` to a stdio MCP command.

## Verify

1. Restart Codex so it reloads the installed plugin.
2. Confirm the `powermem` MCP server is listed.
3. Add a probe memory with content `PowerMem Codex probe: dragonfruit-zx9`.
4. Search for `dragonfruit-zx9` and confirm Codex receives the result.

## Troubleshooting

- If bundled hooks do not fire, run init with `POWERMEM_INIT_ENABLE_HOOKS=1`
  and restart Codex.
- If MCP fails, confirm `http://localhost:8848/mcp` is reachable or switch to stdio MCP.

## Uninstall

Run `codex plugin remove memory-powermem@powermem` or remove it from the Codex
plugin browser. If fallback hooks were enabled, remove the PowerMem-owned
entries from `~/.codex/hooks.json`. For agent-guided cleanup, follow
[`apps/mcp-client/UNINSTALL.md`](https://github.com/oceanbase/powermem/blob/main/apps/mcp-client/UNINSTALL.md).
