"""
PowerMem agent connector commands.

This command detects common agent runtimes and merges a PowerMem MCP server
entry into each runtime's config.
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

from ..utils.output import print_error, print_info, print_success, print_warning


JsonObject = Dict[str, Any]


def _home() -> Path:
    return Path.home()


def _default_env_file() -> str:
    return os.environ.get("POWERMEM_ENV_FILE", str(_home() / ".powermem" / ".env"))


def _mcp_block(env_file: str) -> JsonObject:
    return {
        "command": "uvx",
        "args": ["powermem-mcp"],
        "env": {
            "POWERMEM_ENV_FILE": env_file,
        },
    }


def _opencode_mcp_block(env_file: str) -> JsonObject:
    return {
        "type": "local",
        "command": [
            "sh",
            "-c",
            f'POWERMEM_ENV_FILE="${{POWERMEM_ENV_FILE:-{env_file}}}" exec uvx powermem-mcp',
        ],
        "enabled": True,
    }


def _copilot_mcp_block(env_file: str) -> JsonObject:
    return {
        "type": "local",
        "command": "uvx",
        "args": ["powermem-mcp"],
        "env": {
            "POWERMEM_ENV_FILE": env_file,
        },
        "tools": ["*"],
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
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _write_json_atomic(path: Path, data: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_text_atomic(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)


def _same_uvx_powermem(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("command") != "uvx":
        return False
    args = entry.get("args")
    return isinstance(args, list) and "powermem-mcp" in args


def _same_opencode_powermem(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    command = entry.get("command")
    return isinstance(command, list) and "powermem-mcp" in " ".join(map(str, command))


def _same_copilot_powermem(entry: Any) -> bool:
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
    extra_entry: Optional[JsonObject] = None,
) -> ConnectResult:
    existing = _read_json(config_path)
    data: JsonObject = dict(existing or {})
    servers = data.get(wrapper_key)
    if not isinstance(servers, dict):
        servers = {}

    current = servers.get("powermem")
    if _same_uvx_powermem(current) and not force:
        return ConnectResult("already-wired", config_path)

    entry = _mcp_block(env_file)
    if extra_entry:
        entry.update(extra_entry)
    servers["powermem"] = entry
    data[wrapper_key] = servers

    if dry_run:
        print_info(f"[dry-run] Would write {wrapper_key}.powermem in {config_path}")
        return ConnectResult("installed", config_path)

    backup = None
    if config_path.exists():
        backup = _backup_path(config_path, label)
        shutil.copy2(config_path, backup)
        print_info(f"Backup: {backup}")

    _write_json_atomic(config_path, data)
    verify = _read_json(config_path)
    verify_servers = verify.get(wrapper_key) if verify else None
    if not isinstance(verify_servers, dict) or not _same_uvx_powermem(verify_servers.get("powermem")):
        return ConnectResult("skipped", config_path, "verification-failed")
    return ConnectResult("installed", config_path)


def _install_copilot_cli(env_file: str, force: bool, dry_run: bool, with_hooks: bool) -> ConnectResult:
    copilot_home = Path(os.environ.get("COPILOT_HOME", str(_home() / ".copilot"))).expanduser()
    config_path = copilot_home / "mcp-config.json"
    existing = _read_json(config_path)
    data: JsonObject = dict(existing or {})
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    current = servers.get("powermem")
    if _same_copilot_powermem(current) and not force:
        return ConnectResult("already-wired", config_path)
    servers["powermem"] = _copilot_mcp_block(env_file)
    data["mcpServers"] = servers

    if dry_run:
        print_info(f"[dry-run] Would write mcpServers.powermem in {config_path}")
        return ConnectResult("installed", config_path)

    if config_path.exists():
        backup = _backup_path(config_path, "copilot-cli")
        shutil.copy2(config_path, backup)
        print_info(f"Backup: {backup}")
    _write_json_atomic(config_path, data)
    verify = _read_json(config_path)
    verify_servers = verify.get("mcpServers") if verify else None
    if not isinstance(verify_servers, dict) or not _same_copilot_powermem(verify_servers.get("powermem")):
        return ConnectResult("skipped", config_path, "verification-failed")
    return ConnectResult("installed", config_path)


def _insert_yaml_block(text: str, root_key: str, child_block: str) -> str:
    lines = text.splitlines()
    root_index = next((i for i, line in enumerate(lines) if line.strip() == f"{root_key}:"), None)
    if root_index is None:
        prefix = "\n" if text and not text.endswith("\n") else ""
        return f"{text}{prefix}{root_key}:\n{child_block}"

    insert_index = len(lines)
    for i in range(root_index + 1, len(lines)):
        line = lines[i]
        if line.strip() and not line.startswith((" ", "\t", "-")):
            insert_index = i
            break
    lines[insert_index:insert_index] = child_block.rstrip("\n").splitlines()
    return "\n".join(lines) + "\n"


def _install_continue(env_file: str, force: bool, dry_run: bool, with_hooks: bool) -> ConnectResult:
    config_path = _home() / ".continue" / "config.yaml"
    existing = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    if "powermem-mcp" in existing and not force:
        return ConnectResult("already-wired", config_path)

    block = (
        "  - name: powermem\n"
        "    command: uvx\n"
        "    args:\n"
        "      - powermem-mcp\n"
        "    env:\n"
        f'      POWERMEM_ENV_FILE: "${{POWERMEM_ENV_FILE:-{env_file}}}"\n'
    )
    updated = _insert_yaml_block(existing, "mcpServers", block)

    if dry_run:
        print_info(f"[dry-run] Would write mcpServers powermem entry in {config_path}")
        return ConnectResult("installed", config_path)

    if config_path.exists():
        backup = _backup_path(config_path, "continue")
        shutil.copy2(config_path, backup)
        print_info(f"Backup: {backup}")
    _write_text_atomic(config_path, updated)
    if "powermem-mcp" not in config_path.read_text(encoding="utf-8"):
        return ConnectResult("skipped", config_path, "verification-failed")
    return ConnectResult("installed", config_path)


def _install_goose(env_file: str, force: bool, dry_run: bool, with_hooks: bool) -> ConnectResult:
    config_path = _home() / ".config" / "goose" / "config.yaml"
    existing = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    if "powermem-mcp" in existing and not force:
        return ConnectResult("already-wired", config_path)

    block = (
        "  powermem:\n"
        "    name: PowerMem\n"
        "    cmd: uvx\n"
        "    args:\n"
        "      - powermem-mcp\n"
        "    enabled: true\n"
        "    envs:\n"
        f'      POWERMEM_ENV_FILE: "${{POWERMEM_ENV_FILE:-{env_file}}}"\n'
        "    type: stdio\n"
        "    timeout: 300\n"
    )
    updated = _insert_yaml_block(existing, "extensions", block)

    if dry_run:
        print_info(f"[dry-run] Would write extensions.powermem in {config_path}")
        return ConnectResult("installed", config_path)

    if config_path.exists():
        backup = _backup_path(config_path, "goose")
        shutil.copy2(config_path, backup)
        print_info(f"Backup: {backup}")
    _write_text_atomic(config_path, updated)
    if "powermem-mcp" not in config_path.read_text(encoding="utf-8"):
        return ConnectResult("skipped", config_path, "verification-failed")
    return ConnectResult("installed", config_path)


def _install_hermes(env_file: str, force: bool, dry_run: bool, with_hooks: bool) -> ConnectResult:
    config_path = _home() / ".hermes" / "config.yaml"
    existing = config_path.read_text(encoding="utf-8") if config_path.is_file() else ""
    if "powermem-mcp" in existing and not force:
        return ConnectResult("already-wired", config_path)

    block = (
        "  powermem:\n"
        "    command: uvx\n"
        "    args:\n"
        "      - powermem-mcp\n"
        "    env:\n"
        f'      POWERMEM_ENV_FILE: "${{POWERMEM_ENV_FILE:-{env_file}}}"\n'
    )
    updated = _insert_yaml_block(existing, "mcp_servers", block)

    if dry_run:
        print_info(f"[dry-run] Would write mcp_servers.powermem in {config_path}")
        return ConnectResult("installed", config_path)

    if config_path.exists():
        backup = _backup_path(config_path, "hermes")
        shutil.copy2(config_path, backup)
        print_info(f"Backup: {backup}")
    _write_text_atomic(config_path, updated)
    if "powermem-mcp" not in config_path.read_text(encoding="utf-8"):
        return ConnectResult("skipped", config_path, "verification-failed")
    return ConnectResult("installed", config_path)


def _manual_adapter(reason: str) -> Callable[[str, bool, bool, bool], ConnectResult]:
    def install(env_file: str, force: bool, dry_run: bool, with_hooks: bool) -> ConnectResult:
        return ConnectResult("manual", None, reason)

    return install


def _install_claude_hooks(env_file: str, force: bool, dry_run: bool) -> ConnectResult:
    settings_path = _home() / ".claude" / "settings.json"
    plugin_root_env = os.environ.get("POWERMEM_CLAUDE_PLUGIN_ROOT", "").strip()
    plugin_root = (
        Path(plugin_root_env).expanduser()
        if plugin_root_env
        else Path(__file__).resolve().parents[4] / "apps" / "claude-code-plugin"
    )
    hook_script = plugin_root / "hooks" / "run-hook.sh"
    if not hook_script.is_file():
        return ConnectResult("skipped", settings_path, f"hook-script-not-found:{hook_script}")
    hook_manifest_path = plugin_root / "hooks" / "hooks.json"
    manifest = _read_json(hook_manifest_path)
    manifest_hooks = manifest.get("hooks") if manifest else None
    if not isinstance(manifest_hooks, dict):
        return ConnectResult("skipped", settings_path, f"hook-manifest-not-found:{hook_manifest_path}")

    existing = _read_json(settings_path)
    data: JsonObject = dict(existing or {})
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}

    plugin_root_str = str(plugin_root)
    hook_script_str = str(hook_script)
    for event, manifest_entries in manifest_hooks.items():
        if not isinstance(manifest_entries, list):
            continue
        entries = hooks.get(event)
        if not isinstance(entries, list):
            entries = []
        kept = [item for item in entries if not _is_powermem_hook_entry(item, plugin_root_str, hook_script_str)]
        resolved = []
        for item in manifest_entries:
            if not isinstance(item, dict):
                continue
            hook_handlers = item.get("hooks")
            if not isinstance(hook_handlers, list):
                continue
            next_item: JsonObject = {"__powermem_connect_hook__": True, "hooks": []}
            if isinstance(item.get("matcher"), str):
                next_item["matcher"] = item["matcher"]
            for handler in hook_handlers:
                if not isinstance(handler, dict):
                    continue
                command = str(handler.get("command", "")).replace("${CLAUDE_PLUGIN_ROOT}", plugin_root_str)
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
        print_info(f"[dry-run] Would merge PowerMem hooks into {settings_path}")
        return ConnectResult("installed", settings_path)

    if settings_path.exists():
        backup = _backup_path(settings_path, "claude-settings")
        shutil.copy2(settings_path, backup)
        print_info(f"Backup: {backup}")

    _write_json_atomic(settings_path, data)
    return ConnectResult("installed", settings_path)


def _is_powermem_hook_entry(entry: Any, plugin_root: str, hook_script: str) -> bool:
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
        if normalized_hook_script in command or (normalized_root in command and "run-hook.sh" in command):
            return True
    return False


def _install_claude_code(env_file: str, force: bool, dry_run: bool, with_hooks: bool) -> ConnectResult:
    result = _install_json_mcp(
        label="claude-code",
        config_path=_home() / ".claude.json",
        wrapper_key="mcpServers",
        env_file=env_file,
        force=force,
        dry_run=dry_run,
    )
    if with_hooks:
        hook_result = _install_claude_hooks(env_file, force, dry_run)
        if hook_result.kind == "skipped":
            print_warning(f"Claude Code hooks skipped: {hook_result.reason}")
    return result


def _install_codex(env_file: str, force: bool, dry_run: bool, with_hooks: bool) -> ConnectResult:
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
        return ConnectResult("installed", None)
    env = os.environ.copy()
    env.setdefault("POWERMEM_ENV_FILE", env_file)
    proc = subprocess.run(cmd, text=True, capture_output=True, env=env, check=False)
    if proc.returncode != 0:
        return ConnectResult("skipped", None, proc.stderr.strip() or "codex-mcp-add-failed")
    if with_hooks:
        print_info("Codex plugin installs hooks through marketplace; use the Codex plugin for lifecycle capture.")
    return ConnectResult("installed", _home() / ".codex" / "config.toml")


def _install_opencode(env_file: str, force: bool, dry_run: bool, with_hooks: bool) -> ConnectResult:
    config_path = _home() / ".config" / "opencode" / "opencode.json"
    plugin_config_path = _home() / ".config" / "opencode" / "plugins" / "powermem-config.json"
    existing = _read_json(config_path)
    data: JsonObject = dict(existing or {})
    servers = data.get("mcp")
    if not isinstance(servers, dict):
        servers = {}
    current = servers.get("powermem")
    if _same_opencode_powermem(current) and not force:
        return ConnectResult("already-wired", config_path)
    servers["powermem"] = _opencode_mcp_block(env_file)
    data["mcp"] = servers

    if with_hooks:
        plugins = data.get("plugin")
        if isinstance(plugins, str):
            plugins = [plugins]
        if not isinstance(plugins, list):
            plugins = []
        plugin_path = str(_home() / ".config" / "opencode" / "plugins" / "powermem-capture.ts")
        if plugin_path not in plugins:
            plugins.append(plugin_path)
        data["plugin"] = plugins
        powermem_config = data.get("powermem")
        if not isinstance(powermem_config, dict):
            powermem_config = {}
        powermem_config["envFile"] = env_file
        data["powermem"] = powermem_config

    if dry_run:
        print_info(f"[dry-run] Would write OpenCode config in {config_path}")
        if with_hooks:
            print_info(f"[dry-run] Would write OpenCode PowerMem plugin config in {plugin_config_path}")
        return ConnectResult("installed", config_path)

    if config_path.exists():
        backup = _backup_path(config_path, "opencode")
        shutil.copy2(config_path, backup)
        print_info(f"Backup: {backup}")

    _write_json_atomic(config_path, data)

    if with_hooks:
        source = Path(__file__).resolve().parents[4] / "apps" / "opencode-plugin" / "powermem-capture.ts"
        target = _home() / ".config" / "opencode" / "plugins" / "powermem-capture.ts"
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            _write_json_atomic(plugin_config_path, {"envFile": env_file})
        else:
            print_warning(f"OpenCode plugin source not found: {source}")

    return ConnectResult("installed", config_path)


def _install_openclaw(env_file: str, force: bool, dry_run: bool, with_hooks: bool) -> ConnectResult:
    config_path = _home() / ".openclaw" / "openclaw.json"
    existing = _read_json(config_path)
    data: JsonObject = dict(existing or {})
    entry = _mcp_block(env_file)

    mcp = data.get("mcp")
    if isinstance(mcp, dict):
        servers = mcp.get("servers")
        if not isinstance(servers, dict):
            servers = {}
        current = servers.get("powermem")
        if _same_uvx_powermem(current) and not force:
            return ConnectResult("already-wired", config_path)
        servers["powermem"] = entry
        mcp["servers"] = servers
        data["mcp"] = mcp
    else:
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            servers = {}
        current = servers.get("powermem")
        if _same_uvx_powermem(current) and not force:
            return ConnectResult("already-wired", config_path)
        servers["powermem"] = entry
        data["mcpServers"] = servers

    if dry_run:
        print_info(f"[dry-run] Would write PowerMem MCP entry in {config_path}")
        return ConnectResult("installed", config_path)

    if config_path.exists():
        backup = _backup_path(config_path, "openclaw")
        shutil.copy2(config_path, backup)
        print_info(f"Backup: {backup}")
    _write_json_atomic(config_path, data)
    return ConnectResult("installed", config_path)


def _detect_dir(path: Path) -> Callable[[], bool]:
    return lambda: path.exists()


def _antigravity_dir(home: Path) -> Path:
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Antigravity" / "User"
    return home / ".config" / "Antigravity" / "User"


def _adapters() -> Dict[str, Adapter]:
    home = _home()
    antigravity_dir = _antigravity_dir(home)
    copilot_home = Path(os.environ.get("COPILOT_HOME", str(home / ".copilot"))).expanduser()
    return {
        "claude-code": Adapter(
            "claude-code",
            "Claude Code",
            _detect_dir(home / ".claude"),
            _install_claude_code,
            "MCP via ~/.claude.json; optional hooks fallback via ~/.claude/settings.json.",
        ),
        "codex": Adapter(
            "codex",
            "Codex",
            lambda: shutil.which("codex") is not None or (home / ".codex").exists(),
            _install_codex,
            "MCP via `codex mcp add`; full hooks/skills through the Codex plugin.",
        ),
        "copilot-cli": Adapter(
            "copilot-cli",
            "GitHub Copilot CLI",
            _detect_dir(copilot_home),
            _install_copilot_cli,
            "MCP via mcp-config.json.",
        ),
        "continue": Adapter(
            "continue",
            "Continue",
            _detect_dir(home / ".continue"),
            _install_continue,
            "MCP via ~/.continue/config.yaml.",
        ),
        "cursor": Adapter(
            "cursor",
            "Cursor",
            _detect_dir(home / ".cursor"),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="cursor",
                config_path=home / ".cursor" / "mcp.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via ~/.cursor/mcp.json.",
        ),
        "gemini-cli": Adapter(
            "gemini-cli",
            "Gemini CLI",
            _detect_dir(home / ".gemini"),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="gemini-cli",
                config_path=home / ".gemini" / "settings.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via ~/.gemini/settings.json.",
        ),
        "qwen": Adapter(
            "qwen",
            "Qwen Code",
            _detect_dir(home / ".qwen"),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="qwen",
                config_path=home / ".qwen" / "settings.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via ~/.qwen/settings.json.",
        ),
        "kiro": Adapter(
            "kiro",
            "Kiro",
            _detect_dir(home / ".kiro"),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="kiro",
                config_path=home / ".kiro" / "settings" / "mcp.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via ~/.kiro/settings/mcp.json.",
        ),
        "hermes": Adapter(
            "hermes",
            "Hermes",
            _detect_dir(home / ".hermes"),
            _install_hermes,
            "MCP via ~/.hermes/config.yaml.",
        ),
        "pi": Adapter(
            "pi",
            "Pi",
            _detect_dir(home / ".pi"),
            _manual_adapter("native-extension-install-required"),
            "Native extension host; manual extension registration is required.",
        ),
        "openhuman": Adapter(
            "openhuman",
            "OpenHuman",
            _detect_dir(home / ".openhuman"),
            _manual_adapter("native-memory-trait-required"),
            "Native memory-trait host; manual trait registration is required.",
        ),
        "goose": Adapter(
            "goose",
            "Goose",
            _detect_dir(home / ".config" / "goose"),
            _install_goose,
            "MCP extension via ~/.config/goose/config.yaml.",
        ),
        "qoder": Adapter(
            "qoder",
            "Qoder",
            lambda: shutil.which("qodercli") is not None or (home / ".qoder").exists(),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="qoder",
                config_path=home / ".qoder" / "settings.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via ~/.qoder/settings.json.",
        ),
        "opencode": Adapter(
            "opencode",
            "OpenCode",
            _detect_dir(home / ".config" / "opencode"),
            _install_opencode,
            "MCP via ~/.config/opencode/opencode.json; optional plugin capture with --with-hooks.",
        ),
        "openclaw": Adapter(
            "openclaw",
            "OpenClaw",
            _detect_dir(home / ".openclaw"),
            _install_openclaw,
            "MCP via ~/.openclaw/openclaw.json.",
        ),
        "cline": Adapter(
            "cline",
            "Cline",
            _detect_dir(home / ".cline"),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="cline",
                config_path=home / ".cline" / "mcp.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via ~/.cline/mcp.json.",
        ),
        "windsurf": Adapter(
            "windsurf",
            "Windsurf",
            _detect_dir(home / ".codeium" / "windsurf"),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="windsurf",
                config_path=home / ".codeium" / "windsurf" / "mcp_config.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via ~/.codeium/windsurf/mcp_config.json.",
        ),
        "warp": Adapter(
            "warp",
            "Warp",
            _detect_dir(home / ".warp"),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="warp",
                config_path=home / ".warp" / ".mcp.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via ~/.warp/.mcp.json.",
        ),
        "zed": Adapter(
            "zed",
            "Zed",
            _detect_dir(home / ".config" / "zed"),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="zed",
                config_path=home / ".config" / "zed" / "settings.json",
                wrapper_key="context_servers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via ~/.config/zed/settings.json.",
        ),
        "droid": Adapter(
            "droid",
            "Droid",
            _detect_dir(home / ".factory"),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="droid",
                config_path=home / ".factory" / "mcp.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
                extra_entry={"type": "stdio"},
            ),
            "MCP via ~/.factory/mcp.json.",
        ),
        "antigravity": Adapter(
            "antigravity",
            "Antigravity",
            _detect_dir(antigravity_dir),
            lambda env_file, force, dry_run, with_hooks: _install_json_mcp(
                label="antigravity",
                config_path=antigravity_dir / "mcp_config.json",
                wrapper_key="mcpServers",
                env_file=env_file,
                force=force,
                dry_run=dry_run,
            ),
            "MCP via mcp_config.json.",
        ),
    }


@click.command(name="connect")
@click.argument("agent", required=False)
@click.option("--all", "all_agents", is_flag=True, help="Connect every detected supported agent.")
@click.option("--dry-run", is_flag=True, help="Print planned changes without writing files.")
@click.option("--force", is_flag=True, help="Overwrite an existing PowerMem MCP entry.")
@click.option("--with-hooks", is_flag=True, help="Also install host-specific hooks/plugins when supported.")
@click.option("--env-file", type=click.Path(), default=None, help="PowerMem .env file used by uvx powermem-mcp.")
def connect_group(agent, all_agents, dry_run, force, with_hooks, env_file):
    """Wire PowerMem into coding agents and MCP clients."""
    adapters = _adapters()
    resolved_env = env_file or _default_env_file()

    if not agent and not all_agents:
        names = ", ".join(adapters)
        raise click.UsageError(f"Specify an agent or --all. Supported agents: {names}")

    selected = list(adapters.values()) if all_agents else [adapters.get(str(agent).lower())]
    if any(item is None for item in selected):
        names = ", ".join(adapters)
        raise click.UsageError(f"Unknown agent: {agent}. Supported agents: {names}")

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
            print_info(f"{adapter.display_name}: already wired -> {result.path}")
        elif result.kind == "manual":
            print_warning(f"{adapter.display_name}: manual setup required ({result.reason})")
        else:
            print_error(f"{adapter.display_name}: skipped ({result.reason})")
            if not all_agents:
                sys.exit(1)

    if not Path(resolved_env).exists():
        print_warning(
            f"PowerMem env file does not exist yet: {resolved_env}. "
            "Run `pmem config init` or set POWERMEM_ENV_FILE before starting the agent."
        )
    print_info("Restart connected agents so they reload MCP configuration.")
