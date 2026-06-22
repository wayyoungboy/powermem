#!/usr/bin/env python3
"""Smoke test a packaged PowerMem binary archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


def _fail(message: str) -> None:
    raise SystemExit(f"error: {message}")


def _find_one(dist: Path, patterns: list[str]) -> Path:
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(dist.glob(pattern))
    if not matches:
        _fail(f"no archive found in {dist} for patterns: {', '.join(patterns)}")
    if len(matches) > 1:
        _fail(f"multiple archives found: {', '.join(str(path) for path in matches)}")
    return matches[0]


def _package_name(archive: Path) -> str:
    if archive.name.endswith(".tar.gz"):
        name = archive.name[: -len(".tar.gz")]
        return _strip_suffix(name, "-binaries")
    if archive.name.endswith(".zip"):
        name = archive.name[: -len(".zip")]
        return _strip_suffix(name, "-binaries")
    _fail(f"unsupported archive format: {archive.name}")


def _strip_suffix(value: str, suffix: str) -> str:
    if value.endswith(suffix):
        return value[: -len(suffix)]
    return value


def _verify_checksum(archive: Path) -> None:
    checksum_path = archive.with_name(f"{archive.name}.sha256")
    if not checksum_path.is_file():
        _fail(f"missing checksum file: {checksum_path.name}")

    expected = checksum_path.read_text(encoding="utf-8").split()[0]
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if actual != expected:
        _fail(f"checksum mismatch for {archive.name}: expected {expected}, got {actual}")


def _extract(archive: Path, target: Path) -> None:
    if archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as tar:
            try:
                tar.extractall(target, filter="data")
            except TypeError:
                _verify_tar_members(tar, target)
                tar.extractall(target)
        return

    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zip_file:
            zip_file.extractall(target)
        return

    _fail(f"unsupported archive format: {archive.name}")


def _verify_tar_members(tar: tarfile.TarFile, target: Path) -> None:
    root = target.resolve()
    for member in tar.getmembers():
        member_path = (target / member.name).resolve()
        if root != member_path and root not in member_path.parents:
            _fail(f"unsafe tar member path: {member.name}")
        if member.issym() or member.islnk():
            _fail(f"unsafe tar member link: {member.name}")


def _run_help(binary: Path) -> None:
    subprocess.run(
        [str(binary), "--help"],
        check=True,
        timeout=10,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=2) as response:
        return response.read()


def _smoke_server(server_binary: Path, port: int) -> None:
    env = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="powermem-server-smoke-") as tmp:
        env.update(
            {
                "CI": "1",
                "DATABASE_PROVIDER": "sqlite",
                "SQLITE_PATH": str(Path(tmp) / "powermem-binary-smoke.db"),
                "LLM_PROVIDER": "noop",
                "EMBEDDING_PROVIDER": "mock",
                "RERANKER_ENABLED": "false",
                "POWERMEM_SERVER_LOG_FILE": "",
            }
        )
        process = subprocess.Popen(
            [
                str(server_binary),
                "--host",
                "localhost",
                "--port",
                str(port),
                "--workers",
                "1",
                "--no-open-browser",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            deadline = time.monotonic() + 60
            health_body: bytes | None = None
            dashboard_body: bytes | None = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    output = process.stdout.read() if process.stdout else ""
                    _fail(
                        "powermem-server exited before becoming ready "
                        f"with code {process.returncode}\n{output}"
                    )
                try:
                    health_body = _fetch(f"http://localhost:{port}/api/v1/system/health")
                    dashboard_body = _fetch(f"http://localhost:{port}/dashboard/")
                    break
                except urllib.error.HTTPError as exc:
                    if exc.code == 404:
                        _fail("dashboard endpoint returned 404")
                    time.sleep(1)
                except (OSError, urllib.error.URLError):
                    time.sleep(1)

            if health_body is None or dashboard_body is None:
                _fail("powermem-server did not become ready before timeout")

            health = json.loads(health_body.decode("utf-8"))
            if health.get("success") is not True:
                _fail(f"health response did not report success=true: {health}")
            if health.get("data", {}).get("status") != "healthy":
                _fail(f"health response did not report status=healthy: {health}")
            if not dashboard_body.strip():
                _fail("dashboard response body is empty")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


def _smoke_mcp(mcp_binary: Path) -> None:
    try:
        result = subprocess.run(
            [str(mcp_binary), "stdio"],
            input=b"",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return

    if result.returncode != 0:
        _fail(
            "powermem-mcp stdio exited with non-zero status "
            f"{result.returncode}: {result.stderr.decode(errors='replace')}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", default="dist-binaries", type=Path)
    parser.add_argument("--target-os", required=True)
    parser.add_argument("--target-arch", required=True)
    parser.add_argument("--port", default=18848, type=int)
    args = parser.parse_args()

    dist = args.dist.resolve()
    archive = _find_one(
        dist,
        [
            f"powermem-*-{args.target_os}-{args.target_arch}-binaries.tar.gz",
            f"powermem-*-{args.target_os}-{args.target_arch}-binaries.zip",
        ],
    )
    _verify_checksum(archive)

    with tempfile.TemporaryDirectory(prefix="powermem-binary-smoke-") as tmp:
        extract_root = Path(tmp)
        _extract(archive, extract_root)
        package_root = extract_root / _package_name(archive)
        bin_dir = package_root / "bin"
        if not bin_dir.is_dir():
            _fail(f"missing bin directory: {bin_dir}")

        exe_suffix = ".exe" if args.target_os == "windows" else ""
        expected = {
            f"powermem{exe_suffix}",
            f"powermem-server{exe_suffix}",
            f"powermem-mcp{exe_suffix}",
        }
        actual = {path.name for path in bin_dir.iterdir() if path.is_file()}
        if actual != expected:
            _fail(f"unexpected bin contents: expected {sorted(expected)}, got {sorted(actual)}")

        binaries = {
            name: bin_dir / f"{name}{exe_suffix}"
            for name in ("powermem", "powermem-server", "powermem-mcp")
        }
        for binary in binaries.values():
            if args.target_os != "windows" and not os.access(binary, os.X_OK):
                _fail(f"binary is not executable: {binary}")

        _run_help(binaries["powermem"])
        _run_help(binaries["powermem-server"])
        _smoke_server(binaries["powermem-server"], args.port)
        _smoke_mcp(binaries["powermem-mcp"])

    print(f"Smoke test passed for {archive.name}")


if __name__ == "__main__":
    main()
