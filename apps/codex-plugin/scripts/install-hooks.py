#!/usr/bin/env python3
"""Install PowerMem Codex fallback hooks into a user-scope hooks.json file."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

MARKER = "__powermem_codex_hook__"


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (
        Exception
    ) as exc:  # pragma: no cover - exact parser message is versioned
        raise SystemExit(
            f"Refusing to overwrite invalid Codex hooks file {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise SystemExit(
            f"Refusing to overwrite non-object Codex hooks file {path}"
        )
    return payload


def resolve_command(command: str, plugin_root: str) -> str:
    for token in (
        "${CLAUDE_PLUGIN_ROOT}",
        "${PLUGIN_ROOT}",
        "${CODEX_PLUGIN_ROOT}",
    ):
        command = command.replace(token, plugin_root)
    return command


def is_powermem_entry(entry: Any, plugin_root: str) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get(MARKER) is True:
        return True

    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False

    normalized_root = plugin_root.replace("\\", "/")
    for handler in hooks:
        if not isinstance(handler, dict):
            continue
        command = str(handler.get("command", "")).replace("\\", "/")
        if normalized_root in command and "/hooks/" in command:
            return True
    return False


def build_hooks_payload(
    existing: dict[str, Any],
    manifest: dict[str, Any],
    plugin_root: str,
) -> dict[str, Any]:
    payload = dict(existing)
    hooks = payload.get("hooks")
    if hooks is None:
        hooks = {}
    elif not isinstance(hooks, dict):
        raise SystemExit(
            "Refusing to overwrite Codex hooks file with non-object hooks"
        )
    payload["hooks"] = hooks

    source_hooks = manifest.get("hooks")
    if not isinstance(source_hooks, dict):
        raise SystemExit("Invalid hook manifest: missing hooks object")

    for event, entries in source_hooks.items():
        if not isinstance(entries, list):
            continue

        existing_entries = hooks.get(event)
        if existing_entries is None:
            kept: list[Any] = []
        elif isinstance(existing_entries, list):
            kept = [
                entry
                for entry in existing_entries
                if not is_powermem_entry(entry, plugin_root)
            ]
        else:
            raise SystemExit(
                "Refusing to overwrite Codex hooks event with non-list "
                f"value: {event}"
            )

        resolved = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            next_entry = {
                key: value for key, value in entry.items() if key != "hooks"
            }
            next_entry[MARKER] = True
            next_hooks = []
            for handler in entry.get("hooks", []):
                if not isinstance(handler, dict):
                    continue
                next_handler = dict(handler)
                command = str(next_handler.get("command", ""))
                next_handler["command"] = resolve_command(command, plugin_root)
                next_hooks.append(next_handler)
            if next_hooks:
                next_entry["hooks"] = next_hooks
                resolved.append(next_entry)

        if kept or resolved:
            hooks[event] = [*kept, *resolved]
        else:
            hooks.pop(event, None)

    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if path.exists():
        stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        backup = path.with_name(f"{path.name}.powermem-bak-{stamp}")
        shutil.copy2(path, backup)

    tmp = path.with_name(f"{path.name}.tmp-{id(payload)}")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return backup


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "Usage: install-hooks.py <codex-hooks-file> "
            "<hook-manifest> <plugin-root>",
            file=sys.stderr,
        )
        return 2

    hooks_path = Path(argv[1]).expanduser()
    manifest_path = Path(argv[2])
    plugin_root = str(Path(argv[3]).resolve())

    existing = load_json_object(hooks_path)
    manifest = load_json_object(manifest_path)
    payload = build_hooks_payload(existing, manifest, plugin_root)
    backup = write_json_atomic(hooks_path, payload)

    if backup:
        print(f"Backup: {backup}")
    print(f"Wrote Codex fallback hook config: {hooks_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
