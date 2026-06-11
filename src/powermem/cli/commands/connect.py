"""
PowerMem connector commands for Claude Code and Codex.

This command wires PowerMem's MCP server into supported coding-agent configs
without replacing unrelated user settings.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import click

from ..utils.output import (
    print_error,
    print_info,
    print_success,
    print_warning,
)

JsonObject = Dict[str, Any]


def _home() -> Path:
    return Path.home()


def _default_env_file() -> str:
    return os.environ.get(
        "POWERMEM_ENV_FILE", str(_home() / ".powermem" / ".env")
    )


def _mcp_block(env_file: str) -> JsonObject:
    return {
        "command": "uvx",
        "args": ["powermem-mcp"],
        "env": {
            "POWERMEM_ENV_FILE": env_file,
        },
    }


def _backup_path(path: Path, label: str) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    backup_dir = _home() / ".powermem" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lstrip(".") or "bak"
    return backup_dir / f"{label}-{stamp}.{suffix}"


def _read_json(path: Path) -> Optional[JsonObject]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"invalid-json:{path}:{exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"json-root-not-object:{path}")
    return data


def _write_json_atomic(path: Path, data: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def _same_uvx_powermem(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("command") != "uvx":
        return False
    args = entry.get("args")
    return isinstance(args, list) and "powermem-mcp" in args


@dataclass(frozen=True)
class ConnectResult:
    kind: str
    path: Optional[Path] = None
    reason: Optional[str] = None


@dataclass(frozen=True)
class Adapter:
    name: str
    display_name: str
    detect: Callable[[], bool]
    install: Callable[[str, bool, bool, bool], ConnectResult]
    note: str


def _install_json_mcp(
    *,
    label: str,
    config_path: Path,
    wrapper_key: str,
    env_file: str,
    force: bool,
    dry_run: bool,
) -> ConnectResult:
    try:
        existing = _read_json(config_path)
    except ValueError as exc:
        return ConnectResult("skipped", config_path, str(exc))

    data: JsonObject = dict(existing or {})
    servers = data.get(wrapper_key)
    if servers is None:
        servers = {}
    elif not isinstance(servers, dict):
        return ConnectResult(
            "skipped", config_path, f"{wrapper_key}-root-not-object"
        )

    current = servers.get("powermem")
    if current is not None and not force:
        if _same_uvx_powermem(current):
            return ConnectResult("already-wired", config_path)
        return ConnectResult(
            "skipped",
            config_path,
            "powermem-entry-exists-use-force",
        )

    servers["powermem"] = _mcp_block(env_file)
    data[wrapper_key] = servers

    if dry_run:
        print_info(
            f"[dry-run] Would write {wrapper_key}.powermem in {config_path}"
        )
        return ConnectResult("installed", config_path)

    if config_path.exists():
        backup = _backup_path(config_path, label)
        shutil.copy2(config_path, backup)
        print_info(f"Backup: {backup}")

    _write_json_atomic(config_path, data)
    try:
        verify = _read_json(config_path)
    except ValueError as exc:
        return ConnectResult("skipped", config_path, str(exc))

    verify_servers = verify.get(wrapper_key) if verify else None
    if not isinstance(verify_servers, dict) or not _same_uvx_powermem(
        verify_servers.get("powermem")
    ):
        return ConnectResult("skipped", config_path, "verification-failed")
    return ConnectResult("installed", config_path)


def _install_claude_hooks(force: bool, dry_run: bool) -> ConnectResult:
    settings_path = _home() / ".claude" / "settings.json"
    plugin_root_env = os.environ.get("POWERMEM_CLAUDE_PLUGIN_ROOT", "").strip()
    plugin_root = (
        Path(plugin_root_env).expanduser()
        if plugin_root_env
        else Path(__file__).resolve().parents[4]
        / "apps"
        / "claude-code-plugin"
    )
    hook_script = plugin_root / "hooks" / "run-hook.sh"
    if not hook_script.is_file():
        return ConnectResult(
            "skipped", settings_path, f"hook-script-not-found:{hook_script}"
        )

    hook_manifest_path = plugin_root / "hooks" / "hooks.json"
    try:
        manifest = _read_json(hook_manifest_path)
    except ValueError as exc:
        return ConnectResult("skipped", settings_path, str(exc))

    manifest_hooks = manifest.get("hooks") if manifest else None
    if not isinstance(manifest_hooks, dict):
        return ConnectResult(
            "skipped",
            settings_path,
            f"hook-manifest-not-found:{hook_manifest_path}",
        )

    try:
        existing = _read_json(settings_path)
    except ValueError as exc:
        return ConnectResult("skipped", settings_path, str(exc))

    data: JsonObject = dict(existing or {})
    hooks = data.get("hooks")
    if hooks is None:
        hooks = {}
    elif not isinstance(hooks, dict):
        return ConnectResult("skipped", settings_path, "hooks-root-not-object")

    plugin_root_str = str(plugin_root)
    hook_script_str = str(hook_script)
    for event, manifest_entries in manifest_hooks.items():
        if not isinstance(manifest_entries, list):
            continue
        entries = hooks.get(event)
        if entries is None:
            entries = []
        elif not isinstance(entries, list):
            return ConnectResult(
                "skipped", settings_path, f"hooks-event-not-list:{event}"
            )

        kept = [
            item
            for item in entries
            if not _is_powermem_hook_entry(
                item, plugin_root_str, hook_script_str
            )
        ]
        resolved = []
        for item in manifest_entries:
            if not isinstance(item, dict):
                continue
            hook_handlers = item.get("hooks")
            if not isinstance(hook_handlers, list):
                continue
            next_item: JsonObject = {
                "__powermem_connect_hook__": True,
                "hooks": [],
            }
            if isinstance(item.get("matcher"), str):
                next_item["matcher"] = item["matcher"]
            for handler in hook_handlers:
                if not isinstance(handler, dict):
                    continue
                command = str(handler.get("command", "")).replace(
                    "${CLAUDE_PLUGIN_ROOT}", plugin_root_str
                )
                next_handler: JsonObject = {
                    "type": handler.get("type", "command"),
                    "command": command,
                }
                if isinstance(handler.get("timeout"), int):
                    next_handler["timeout"] = handler["timeout"]
                next_item["hooks"].append(next_handler)
            if next_item["hooks"]:
                resolved.append(next_item)
        hooks[event] = [*kept, *resolved]
    data["hooks"] = hooks

    if dry_run:
        print_info(
            f"[dry-run] Would merge PowerMem hooks into {settings_path}"
        )
        return ConnectResult("installed", settings_path)

    if settings_path.exists():
        backup = _backup_path(settings_path, "claude-settings")
        shutil.copy2(settings_path, backup)
        print_info(f"Backup: {backup}")

    _write_json_atomic(settings_path, data)
    return ConnectResult("installed", settings_path)


def _is_powermem_hook_entry(
    entry: Any, plugin_root: str, hook_script: str
) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("__powermem_connect_hook__") is True:
        return True
    handlers = entry.get("hooks")
    if not isinstance(handlers, list):
        return False
    normalized_root = plugin_root.replace("\\", "/")
    normalized_hook_script = hook_script.replace("\\", "/")
    for handler in handlers:
        if not isinstance(handler, dict):
            continue
        command = str(handler.get("command", "")).replace("\\", "/")
        if normalized_hook_script in command or (
            normalized_root in command and "run-hook.sh" in command
        ):
            return True
    return False


def _install_claude_code(
    env_file: str, force: bool, dry_run: bool, with_hooks: bool
) -> ConnectResult:
    result = _install_json_mcp(
        label="claude-code",
        config_path=_home() / ".claude.json",
        wrapper_key="mcpServers",
        env_file=env_file,
        force=force,
        dry_run=dry_run,
    )
    if with_hooks:
        hook_result = _install_claude_hooks(force, dry_run)
        if hook_result.kind == "skipped":
            print_warning(f"Claude Code hooks skipped: {hook_result.reason}")
    return result


def _install_codex(
    env_file: str, force: bool, dry_run: bool, with_hooks: bool
) -> ConnectResult:
    if not shutil.which("codex"):
        return ConnectResult("skipped", None, "codex-command-not-found")

    cmd = [
        "codex",
        "mcp",
        "add",
        "powermem",
        "--env",
        f"POWERMEM_ENV_FILE={env_file}",
        "--",
        "uvx",
        "powermem-mcp",
    ]
    if dry_run:
        print_info("[dry-run] Would run: " + " ".join(cmd))
        if with_hooks:
            print_info(
                "[dry-run] Codex hooks are installed by the Codex plugin "
                "init flow."
            )
        return ConnectResult("installed", None)

    env = os.environ.copy()
    env.setdefault("POWERMEM_ENV_FILE", env_file)
    proc = subprocess.run(
        cmd, text=True, capture_output=True, env=env, check=False
    )
    if proc.returncode != 0:
        return ConnectResult(
            "skipped", None, proc.stderr.strip() or "codex-mcp-add-failed"
        )
    if with_hooks:
        print_info("Codex hooks are installed by the Codex plugin init flow.")
    return ConnectResult("installed", _home() / ".codex" / "config.toml")


def _detect_dir(path: Path) -> Callable[[], bool]:
    return lambda: path.exists()


def _adapters() -> Dict[str, Adapter]:
    home = _home()
    return {
        "claude-code": Adapter(
            "claude-code",
            "Claude Code",
            _detect_dir(home / ".claude"),
            _install_claude_code,
            "MCP via ~/.claude.json; optional hooks fallback via "
            "~/.claude/settings.json.",
        ),
        "codex": Adapter(
            "codex",
            "Codex",
            lambda: shutil.which("codex") is not None
            or (home / ".codex").exists(),
            _install_codex,
            "MCP via `codex mcp add`; full hooks/skills through the "
            "Codex plugin.",
        ),
    }


@click.command(name="connect")
@click.argument("agent", required=False)
@click.option(
    "--all",
    "all_agents",
    is_flag=True,
    help="Connect every detected supported agent.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print planned changes without writing files.",
)
@click.option(
    "--force", is_flag=True, help="Overwrite an existing PowerMem MCP entry."
)
@click.option(
    "--with-hooks",
    is_flag=True,
    help="Also install host-specific hooks when supported.",
)
@click.option(
    "--env-file",
    type=click.Path(),
    default=None,
    help="PowerMem .env file used by uvx powermem-mcp.",
)
def connect_group(agent, all_agents, dry_run, force, with_hooks, env_file):
    """Wire PowerMem into Claude Code or Codex."""
    adapters = _adapters()
    resolved_env = env_file or _default_env_file()

    if not agent and not all_agents:
        names = ", ".join(adapters)
        raise click.UsageError(
            f"Specify an agent or --all. Supported agents: {names}"
        )

    selected = (
        list(adapters.values())
        if all_agents
        else [adapters.get(str(agent).lower())]
    )
    if any(item is None for item in selected):
        names = ", ".join(adapters)
        raise click.UsageError(
            f"Unknown agent: {agent}. Supported agents: {names}"
        )

    for adapter in selected:
        assert adapter is not None
        if not adapter.detect():
            print_warning(f"{adapter.display_name}: not detected; skipping.")
            continue
        print_info(f"{adapter.display_name}: {adapter.note}")
        result = adapter.install(resolved_env, force, dry_run, with_hooks)
        if result.kind == "installed":
            suffix = f" -> {result.path}" if result.path else ""
            print_success(f"{adapter.display_name}: installed{suffix}")
        elif result.kind == "already-wired":
            print_info(
                f"{adapter.display_name}: already wired -> {result.path}"
            )
        else:
            print_error(f"{adapter.display_name}: skipped ({result.reason})")
            if not all_agents:
                sys.exit(1)

    if not Path(resolved_env).exists():
        print_warning(
            f"PowerMem env file does not exist yet: {resolved_env}. "
            "Run `pmem config init` or set POWERMEM_ENV_FILE before "
            "starting the agent."
        )
    print_info("Restart connected agents so they reload MCP configuration.")
