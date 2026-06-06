---
name: status
description: Check whether the PowerMem Codex plugin is configured.
user-invocable: true
---

Run `sh "${CODEX_PLUGIN_ROOT}/scripts/status.sh"` when available.

Report the data directory, env file state, venv Python, `powermem-mcp` path,
whether bundled `.mcp.json` and `hooks.codex.json` are present, and whether
PowerMem fallback hooks are present in `~/.codex/hooks.json`. Do not print
`.env` contents.
