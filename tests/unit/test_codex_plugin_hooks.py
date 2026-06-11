from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def load_install_hooks_module():
    root = Path(__file__).resolve().parents[2]
    script = root / "apps" / "codex-plugin" / "scripts" / "install-hooks.py"
    spec = importlib.util.spec_from_file_location(
        "powermem_codex_install_hooks", script
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_hooks_payload_preserves_user_hooks():
    module = load_install_hooks_module()
    existing = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 ~/.codex/hooks/user_hook.py",
                        }
                    ]
                },
                {
                    "__powermem_codex_hook__": True,
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                "sh /old/powermem/hooks/"
                                "user-prompt-submit.sh"
                            ),
                        }
                    ],
                },
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 ~/.codex/hooks/stop_hook.py",
                        }
                    ]
                }
            ],
        }
    }
    manifest = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                'sh "${CLAUDE_PLUGIN_ROOT}/hooks/'
                                'user-prompt-submit.sh"'
                            ),
                            "timeout": 15,
                        }
                    ]
                }
            ]
        }
    }

    payload = module.build_hooks_payload(
        existing, manifest, "/tmp/plugin-root"
    )

    entries = payload["hooks"]["UserPromptSubmit"]
    assert len(entries) == 2
    assert (
        entries[0]["hooks"][0]["command"]
        == "python3 ~/.codex/hooks/user_hook.py"
    )
    assert entries[1]["__powermem_codex_hook__"] is True
    assert entries[1]["hooks"][0]["command"] == (
        'sh "/tmp/plugin-root/hooks/user-prompt-submit.sh"'
    )
    assert payload["hooks"]["Stop"] == existing["hooks"]["Stop"]


def test_load_json_object_rejects_invalid_json(tmp_path):
    module = load_install_hooks_module()
    hooks_file = tmp_path / "hooks.json"
    hooks_file.write_text("{not-json", encoding="utf-8")

    with pytest.raises(SystemExit):
        module.load_json_object(hooks_file)


def test_write_json_atomic_creates_backup(tmp_path):
    module = load_install_hooks_module()
    hooks_file = tmp_path / "hooks.json"
    hooks_file.write_text('{"hooks": {}}\n', encoding="utf-8")

    backup = module.write_json_atomic(hooks_file, {"hooks": {"Stop": []}})

    assert backup is not None
    assert backup.is_file()
    assert '"Stop": []' in hooks_file.read_text(encoding="utf-8")
