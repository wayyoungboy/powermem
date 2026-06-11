from __future__ import annotations

import json

from powermem.cli.commands import connect


def test_install_json_mcp_does_not_overwrite_custom_entry_without_force(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    monkeypatch.setattr(connect, "_home", lambda: home)
    config_path = tmp_path / "config.json"
    original = {
        "mcpServers": {
            "powermem": {
                "url": "http://localhost:8848/mcp",
            },
            "other": {
                "command": "other-mcp",
            },
        }
    }
    config_path.write_text(json.dumps(original), encoding="utf-8")

    result = connect._install_json_mcp(
        label="test",
        config_path=config_path,
        wrapper_key="mcpServers",
        env_file="/tmp/powermem.env",
        force=False,
        dry_run=False,
    )

    assert result.kind == "skipped"
    assert result.reason == "powermem-entry-exists-use-force"
    assert json.loads(config_path.read_text(encoding="utf-8")) == original


def test_install_json_mcp_overwrites_custom_entry_with_force(
    tmp_path, monkeypatch
):
    home = tmp_path / "home"
    monkeypatch.setattr(connect, "_home", lambda: home)
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "powermem": {
                        "url": "http://localhost:8848/mcp",
                    },
                    "other": {
                        "command": "other-mcp",
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    result = connect._install_json_mcp(
        label="test",
        config_path=config_path,
        wrapper_key="mcpServers",
        env_file="/tmp/powermem.env",
        force=True,
        dry_run=False,
    )

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert result.kind == "installed"
    assert payload["mcpServers"]["powermem"] == {
        "command": "uvx",
        "args": ["powermem-mcp"],
        "env": {
            "POWERMEM_ENV_FILE": "/tmp/powermem.env",
        },
    }
    assert payload["mcpServers"]["other"] == {
        "command": "other-mcp",
    }
    assert list((home / ".powermem" / "backups").iterdir())


def test_install_json_mcp_rejects_non_object_server_root(tmp_path):
    config_path = tmp_path / "config.json"
    original = {"mcpServers": []}
    config_path.write_text(json.dumps(original), encoding="utf-8")

    result = connect._install_json_mcp(
        label="test",
        config_path=config_path,
        wrapper_key="mcpServers",
        env_file="/tmp/powermem.env",
        force=True,
        dry_run=False,
    )

    assert result.kind == "skipped"
    assert result.reason == "mcpServers-root-not-object"
    assert json.loads(config_path.read_text(encoding="utf-8")) == original
