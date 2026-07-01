# PowerMem for Codex Uninstall

The installed `uninstall` skill should guide cleanup as three progressive layers. Ask one layer at a time, and stop as soon as the user does not want to continue deeper.

## Layer 1: Delete Codex Hooks

This removes the Codex plugin, including its bundled hook configuration, from future Codex threads. It keeps the local marketplace entry, local PowerMem service, runtime, config, memories, logs, and data.

Use this when the user only wants Codex to stop loading PowerMem hooks.

```bash
codex plugin remove powermem-codex-plugin 2>/dev/null || true
```

Start a new Codex thread after removal so Codex stops loading plugin hooks and skills from the removed plugin.

After this layer, ask whether to continue to Layer 2.

## Layer 2: Delete Local Marketplace

This removes the local development marketplace registration, usually `powermem-local`. It should happen only after the Codex plugin/hooks are removed and only when that marketplace was added for this plugin.

Use this when the user no longer wants this local plugin source to appear in Codex.

```bash
codex plugin marketplace remove powermem-local 2>/dev/null || true
```

Do not remove the marketplace if other local PowerMem plugins depend on it.

After this layer, ask whether to continue to Layer 3.

## Layer 3: Delete Local Service Configuration

This layer touches local PowerMem resources under `~/.powermem`. It can affect Claude Code or other clients if they share the same local PowerMem backend. Before doing anything in this layer, ask whether the local backend is shared with Claude Code or another client. If the user says yes or is not sure, recommend stopping here.

If the user confirms they want to continue, ask the local service/config questions one at a time:

```text
1. Stop the local managed powermem-server?
2. Remove hook runtime state: ~/.powermem/runtime.env?
3. Remove local backend config: ~/.powermem/.env?
4. Delete all local PowerMem data under ~/.powermem?
```

### Stop Local Service

Stopping the service keeps files under `~/.powermem`, but Claude Code memory access will be unavailable until PowerMem is restarted if Claude uses the same backend.

```bash
POWERMEM_UNINSTALL_STOP_SERVER=1 sh "$PLUGIN_ROOT/scripts/uninstall.sh"
```

### Remove Runtime Or Config

Remove only the hook runtime file:

```bash
POWERMEM_UNINSTALL_REMOVE_RUNTIME=1 sh "$PLUGIN_ROOT/scripts/uninstall.sh"
```

Remove runtime and backend config:

```bash
POWERMEM_UNINSTALL_REMOVE_RUNTIME=1 \
POWERMEM_UNINSTALL_REMOVE_CONFIG=1 \
sh "$PLUGIN_ROOT/scripts/uninstall.sh"
```

`~/.powermem/runtime.env` and `~/.powermem/.env` are shared by the Codex and Claude Code plugins by default. Warn the user before removing either file.

### Delete All Local PowerMem Data

Deleting data stops the local managed backend and deletes `~/.powermem/`, including memories, config, runtime, logs, pid files, and local database files. If Claude Code uses the same local data directory, this also removes Claude's local PowerMem memory/config.

Required confirmation phrase:

```text
delete-powermem-data
```

Command:

```bash
POWERMEM_UNINSTALL_DELETE_DATA=1 \
POWERMEM_UNINSTALL_CONFIRM=delete-powermem-data \
sh "$PLUGIN_ROOT/scripts/uninstall.sh"
```

The uninstall script refuses to delete data unless `POWERMEM_UNINSTALL_CONFIRM=delete-powermem-data` is present.

## Command Composition For Layer 3

For local service/config cleanup without deleting all data, combine the chosen variables in one command and omit unselected variables:

```bash
POWERMEM_UNINSTALL_STOP_SERVER=1 \
POWERMEM_UNINSTALL_REMOVE_RUNTIME=1 \
POWERMEM_UNINSTALL_REMOVE_CONFIG=1 \
sh "$PLUGIN_ROOT/scripts/uninstall.sh"
```

If the user selects data deletion, use the data deletion command instead of separate runtime/config cleanup because deleting `~/.powermem` includes those files.
