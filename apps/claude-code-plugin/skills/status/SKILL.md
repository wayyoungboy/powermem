---
description: Check whether PowerMem is configured, running, and reachable from Claude Code.
---

Run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/status.sh"` when available. Report the data directory, base URL, connection mode, MCP config state, managed server PID if any, and health state. In remote mode, a missing managed PID is expected. Do not print `.env` or API key contents.
