---
name: status
description: Check the local PowerMem backend and hook runtime status for Codex.
---

# PowerMem Codex Status

Resolve `PLUGIN_ROOT` from `PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, or the installed plugin path under `~/.codex/plugins`, then run:

```bash
sh "$PLUGIN_ROOT/scripts/status.sh"
```

Summarize the backend health, runtime base URL, PID state, and whether a Codex restart or hook trust review is still needed. Mask secrets.
