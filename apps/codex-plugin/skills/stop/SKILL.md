---
name: stop
description: Stop PowerMem processes managed by the Codex plugin.
user-invocable: true
---

Locate the installed plugin root using `PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`,
`CODEX_PLUGIN_ROOT`, or the Codex plugin cache, then run
`sh "$root/scripts/stop.sh"`.

This only stops a PID tracked by the plugin data directory. Do not kill unrelated
PowerMem processes unless the user explicitly asks.
