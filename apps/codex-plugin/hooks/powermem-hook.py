#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SENSITIVE_KEYS = {"api_key", "authorization", "password", "secret", "token"}
MAX_CAPTURE_CHARS = 8000
MAX_RECALL_CHARS = 6000


def data_dir() -> Path:
    for key in (
        "POWERMEM_PLUGIN_DATA",
        "CODEX_PLUGIN_DATA",
        "CLAUDE_PLUGIN_DATA",
    ):
        value = os.environ.get(key)
        if value:
            return Path(value).expanduser()
    return Path.home() / ".codex" / "plugins" / "data" / "memory-powermem"


DATA_DIR = data_dir()
ENV_FILE = DATA_DIR / ".env"
PMEM = DATA_DIR / "venv" / "bin" / "pmem"
LOG_FILE = DATA_DIR / "powermem-hooks.log"


def log(message: str) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")
    except Exception:
        pass


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def enabled() -> bool:
    return PMEM.is_file() and os.access(PMEM, os.X_OK) and ENV_FILE.is_file()


def run_pmem(
    args: list[str], *, input_text: str | None = None, timeout: int = 20
) -> subprocess.CompletedProcess[str] | None:
    if not enabled():
        return None
    env = os.environ.copy()
    env["POWERMEM_ENV_FILE"] = str(ENV_FILE)
    try:
        return subprocess.run(
            [str(PMEM), "--env-file", str(ENV_FILE), *args],
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except Exception as exc:
        log(f"pmem invocation failed: {exc}")
        return None


def session_id(payload: dict[str, Any]) -> str:
    return str(
        payload.get("session_id")
        or payload.get("sessionId")
        or "codex-session"
    )


def cwd(payload: dict[str, Any]) -> str:
    return str(payload.get("cwd") or os.getcwd())


def tool_name(payload: dict[str, Any]) -> str:
    for key in ("tool_name", "toolName", "tool", "name"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return "unknown"


def collect_text(value: Any, out: list[str]) -> None:
    if isinstance(value, str):
        text = value.strip()
        if text:
            out.append(text)
        return
    if isinstance(value, list):
        for item in value:
            collect_text(item, out)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                continue
            collect_text(item, out)


def compact_payload(
    payload: dict[str, Any], limit: int = MAX_CAPTURE_CHARS
) -> str:
    texts: list[str] = []
    collect_text(payload, texts)
    content = "\n".join(texts).strip()
    if len(content) > limit:
        return content[-limit:]
    return content


def add_memory(
    event: str,
    content: str,
    payload: dict[str, Any],
    *,
    memory_type: str = "short_term",
) -> None:
    content = content.strip()
    if not content:
        return
    metadata = {
        "source": "codex-plugin-hook",
        "event": event,
        "cwd": cwd(payload),
    }
    result = run_pmem(
        [
            "memory",
            "add",
            content,
            "--agent-id",
            "codex",
            "--run-id",
            session_id(payload),
            "--metadata",
            json.dumps(metadata, ensure_ascii=False),
            "--memory-type",
            memory_type,
            "--no-infer",
        ],
        timeout=30,
    )
    if result and result.returncode != 0:
        log(f"add_memory {event} failed: {result.stderr.strip()}")


def extract_prompt(payload: dict[str, Any]) -> str:
    for key in ("prompt", "userPrompt", "user_prompt", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return compact_payload(payload, limit=4000)


def recall(prompt: str) -> None:
    if not prompt:
        return
    result = run_pmem(
        [
            "memory",
            "search",
            prompt,
            "--agent-id",
            "codex",
            "--limit",
            "5",
            "--json",
        ],
        timeout=15,
    )
    if not result or result.returncode != 0:
        if result:
            log(f"recall failed: {result.stderr.strip()}")
        return
    text = result.stdout.strip()
    if not text or text in ("[]", "{}"):
        return
    if len(text) > MAX_RECALL_CHARS:
        text = text[:MAX_RECALL_CHARS] + "\n..."
    sys.stdout.write(
        "\nPowerMem recalled relevant memories for this prompt. "
        "Use them as background context only when they are relevant:\n\n"
        f"{text}\n"
    )


def main() -> None:
    event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    payload = read_payload()
    if not enabled():
        return

    if event == "SessionStart":
        add_memory(
            event,
            f"Codex session started in {cwd(payload)}.",
            payload,
            memory_type="working",
        )
        return

    if event == "UserPromptSubmit":
        prompt = extract_prompt(payload)
        recall(prompt)
        add_memory(
            event,
            "Codex user prompt:\n\n" + prompt,
            payload,
            memory_type="working",
        )
        return

    if event in {"PreToolUse", "PostToolUse"}:
        content = compact_payload(payload, limit=5000)
        add_memory(
            event,
            f"Codex {event} for tool {tool_name(payload)}:\n\n{content}",
            payload,
            memory_type="working",
        )
        return

    if event == "PreCompact":
        content = compact_payload(payload)
        add_memory(
            event,
            "Codex context before compaction:\n\n" + content,
            payload,
            memory_type="short_term",
        )
        return

    if event == "Stop":
        content = compact_payload(payload)
        add_memory(
            event,
            "Codex session stop context:\n\n" + content,
            payload,
            memory_type="short_term",
        )


if __name__ == "__main__":
    main()
