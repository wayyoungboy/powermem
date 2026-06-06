---
name: stop
description: Stop PowerMem processes managed by the Codex plugin.
user-invocable: true
---

Run `sh "${CODEX_PLUGIN_ROOT}/scripts/stop.sh"` when available.

This only stops a PID tracked by the plugin data directory. Do not kill unrelated
PowerMem processes unless the user explicitly asks.
