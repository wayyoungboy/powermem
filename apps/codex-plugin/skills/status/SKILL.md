---
name: status
description: Check whether the PowerMem Codex plugin is configured.
user-invocable: true
---

Locate the installed plugin root using `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`,
`CODEX_PLUGIN_ROOT`, or the Codex plugin cache, then run
`sh "$root/scripts/status.sh"`.

Report the data directory, env file state, venv Python, `powermem-mcp` path,
whether bundled `.mcp.json` and `hooks.codex.json` are present, and whether
PowerMem fallback hooks are present in `~/.codex/hooks.json`. Do not print
`.env` contents.
