# Agent Integrations

PowerMem can be wired into multiple coding agents through a shared MCP entry and
host-specific plugins where the host supports lifecycle hooks.

## Quick Connect

```bash
pmem connect cursor
pmem connect claude-code --with-hooks
pmem connect codex
pmem connect opencode --with-hooks
pmem connect copilot-cli
pmem connect continue
pmem connect gemini-cli
pmem connect qwen
pmem connect kiro
pmem connect hermes
pmem connect pi
pmem connect openhuman
pmem connect goose
pmem connect qoder
pmem connect openclaw
pmem connect warp
pmem connect zed
pmem connect droid
pmem connect antigravity
pmem connect --all
```

By default, connector entries launch:

```bash
uvx powermem-mcp
```

Set `POWERMEM_ENV_FILE` before starting the agent, or pass `--env-file` when
running `pmem connect`, if your PowerMem config is not in the default location.

## Supported Hosts

| Host | Command | What gets configured |
|------|---------|----------------------|
| Claude Code | `pmem connect claude-code --with-hooks` | `~/.claude.json` MCP entry and optional user-scope hooks fallback |
| Codex | `pmem connect codex` | `codex mcp add powermem -- uvx powermem-mcp`; use the Codex plugin for hooks and skills |
| GitHub Copilot CLI | `pmem connect copilot-cli` | MCP config under `COPILOT_HOME` or `~/.copilot` |
| Continue | `pmem connect continue` | `~/.continue/config.yaml` |
| Cursor | `pmem connect cursor` | `~/.cursor/mcp.json` |
| OpenCode | `pmem connect opencode --with-hooks` | `~/.config/opencode/opencode.json`, optional capture plugin copy |
| OpenClaw | `pmem connect openclaw` | `~/.openclaw/openclaw.json` |
| Cline | `pmem connect cline` | `~/.cline/mcp.json` |
| Windsurf | `pmem connect windsurf` | `~/.codeium/windsurf/mcp_config.json` |
| Gemini CLI | `pmem connect gemini-cli` | `~/.gemini/settings.json` |
| Qwen Code | `pmem connect qwen` | `~/.qwen/settings.json` |
| Kiro | `pmem connect kiro` | `~/.kiro/settings/mcp.json` |
| Hermes | `pmem connect hermes` | `~/.hermes/config.yaml` |
| Pi | `pmem connect pi` | Detects the host and reports the required native extension setup |
| OpenHuman | `pmem connect openhuman` | Detects the host and reports the required memory-trait setup |
| Goose | `pmem connect goose` | `~/.config/goose/config.yaml` |
| Qoder | `pmem connect qoder` | `~/.qoder/settings.json` |
| Warp | `pmem connect warp` | `~/.warp/.mcp.json` |
| Zed | `pmem connect zed` | `~/.config/zed/settings.json` under `context_servers` |
| Droid | `pmem connect droid` | `~/.factory/mcp.json` |
| Antigravity | `pmem connect antigravity` | platform app config `mcp_config.json` |

The connector backs up existing config files under `~/.powermem/backups/` before
writing. Existing MCP servers are preserved.

## Plugin Paths

- Claude Code: `apps/claude-code-plugin/`
- Codex: `apps/codex-plugin/`
- OpenCode: `apps/opencode-plugin/`
- Generic MCP clients: `apps/mcp-client/`
