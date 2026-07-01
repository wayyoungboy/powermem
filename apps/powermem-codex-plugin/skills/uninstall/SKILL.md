---
name: uninstall
description: "Uninstall the PowerMem Codex hook plugin through three progressive layers: delete Codex hooks, optionally delete the local marketplace, then optionally delete local PowerMem service configuration after guided confirmation."
---

# PowerMem Codex Uninstall

Use when the user wants to remove, uninstall, disconnect, or clean up the PowerMem Codex hook plugin.

1. Read `apps/powermem-codex-plugin/UNINSTALL.md`.
2. Resolve `PLUGIN_ROOT` from `PLUGIN_ROOT`, `CODEX_PLUGIN_ROOT`, or the installed plugin path under `~/.codex/plugins`.
3. Run `sh "$PLUGIN_ROOT/scripts/status.sh"` first and report the current backend mode, base URL, managed server status, and data directory.
4. Use three progressive layers in the user's language. Ask one layer at a time and stop as soon as the user does not want to continue deeper:
   - Layer 1: delete Codex hooks/plugin
   - Layer 2: delete local marketplace
   - Layer 3: delete local PowerMem service configuration
5. Layer 1 is the default uninstall. Remove only the Codex plugin/hooks and keep marketplace, local service, runtime, config, memories, logs, data, and Claude Code memory access:

   ```bash
   codex plugin remove powermem-codex-plugin 2>/dev/null || true
   ```

   After it succeeds, ask whether to continue to Layer 2.
6. Layer 2 removes the local development marketplace registration. Do this only after Layer 1 and only when the user confirms `powermem-local` was added for this plugin and is not needed by other local plugins:

   ```bash
   codex plugin marketplace remove powermem-local 2>/dev/null || true
   ```

   After it succeeds, ask whether to continue to Layer 3.
7. Layer 3 touches local PowerMem resources under `~/.powermem`. Before doing anything in this layer, ask whether the local backend is shared with Claude Code or another client. If the user says yes or is not sure, recommend stopping here.
8. If the user explicitly continues to Layer 3, ask the local service/config cleanup questions one at a time:
   - stop the local managed `powermem-server`
   - remove hook runtime state: `~/.powermem/runtime.env`
   - remove local backend config: `~/.powermem/.env`
   - delete all local PowerMem data under `~/.powermem`
9. Warn before stopping the service that Claude Code memory access may be unavailable until PowerMem is restarted if Claude uses the same backend. Use `POWERMEM_UNINSTALL_STOP_SERVER=1` when selected.
10. Warn before removing `~/.powermem/runtime.env` or `~/.powermem/.env` that these files are shared by the Codex and Claude Code plugins by default. Use `POWERMEM_UNINSTALL_REMOVE_RUNTIME=1` and, when selected, `POWERMEM_UNINSTALL_REMOVE_CONFIG=1`.
11. Before deleting `~/.powermem`, show the exact data directory from status, explain that memories, config, runtime, logs, pid files, and local database files will be deleted, and warn that local Claude Code will lose those local memories/config if it shares that directory. Require the exact confirmation phrase `delete-powermem-data`. Never delete data without that phrase.
12. Build one Layer 3 cleanup command from the selected non-data-delete options, omitting unselected variables:

    ```bash
    POWERMEM_UNINSTALL_STOP_SERVER=1 \
    POWERMEM_UNINSTALL_REMOVE_RUNTIME=1 \
    POWERMEM_UNINSTALL_REMOVE_CONFIG=1 \
    sh "$PLUGIN_ROOT/scripts/uninstall.sh"
    ```

13. If the user selected full data deletion, use this command instead of separate runtime/config cleanup:

    ```bash
    POWERMEM_UNINSTALL_DELETE_DATA=1 \
    POWERMEM_UNINSTALL_CONFIRM=delete-powermem-data \
    sh "$PLUGIN_ROOT/scripts/uninstall.sh"
    ```

14. Never remove or modify `apps/claude-code-plugin`.
15. Never delete `~/.powermem`, remove `~/.powermem/runtime.env`, remove `~/.powermem/.env`, or stop a shared local backend without warning that Claude may be affected.
16. After uninstall commands, report what was removed and what was kept. If the plugin was removed, tell the user to start a new Codex thread so hooks and skills are no longer loaded from the removed plugin.
