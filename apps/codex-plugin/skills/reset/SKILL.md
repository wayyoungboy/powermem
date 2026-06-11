---
name: reset
description: Reset PowerMem Codex plugin-local data after explicit confirmation.
user-invocable: true
---

Reset is destructive. First tell the user it will stop plugin-managed processes
and delete the plugin data directory containing `.env`, runtime state, logs, and
venv. Only after explicit confirmation, run:

```bash
POWERMEM_RESET_CONFIRM=delete sh "$PLUGIN_ROOT/scripts/reset.sh"
```

Do not delete project files, Codex config, or unrelated PowerMem data.
