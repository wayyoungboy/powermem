# PowerMem Plugin for OpenCode

This plugin connects OpenCode to PowerMem through MCP plus event capture.

## Install MCP

Add this to `~/.config/opencode/opencode.json` or `.opencode/opencode.json`:

```json
{
  "mcp": {
    "powermem": {
      "type": "local",
      "command": ["sh", "-c", "exec uvx powermem-mcp"],
      "enabled": true
    }
  }
}
```

Set `POWERMEM_ENV_FILE` before starting OpenCode when you do not use the default
PowerMem config path.

## Install Capture Plugin

```bash
mkdir -p ~/.config/opencode/plugins ~/.config/opencode/commands
cp apps/opencode-plugin/powermem-capture.ts ~/.config/opencode/plugins/
cp apps/opencode-plugin/commands/recall.md ~/.config/opencode/commands/
cp apps/opencode-plugin/commands/remember.md ~/.config/opencode/commands/
```

Then add the plugin path to `~/.config/opencode/opencode.json`:

```json
{
  "plugin": ["~/.config/opencode/plugins/powermem-capture.ts"]
}
```

`pmem connect opencode --with-hooks` performs the MCP config update and copies
the capture plugin when OpenCode is installed.

## Captured Events

- session lifecycle: created, idle/status, compacted, updated, diff, deleted,
  error
- prompts and messages: chat.message, message.updated, message.removed
- tool lifecycle and file activity: tool.execute.before, tool parts,
  file.edited
- permissions, tasks, command execution, model/config metadata

Captured content is sent to the local PowerMem CLI using the configured
`POWERMEM_ENV_FILE`. Failures are logged only when
`OPENCODE_POWERMEM_DEBUG=1`.
