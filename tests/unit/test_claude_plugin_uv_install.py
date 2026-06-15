import os
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMMON_SH = ROOT / "apps" / "claude-code-plugin" / "scripts" / "common.sh"
INIT_SH = ROOT / "apps" / "claude-code-plugin" / "scripts" / "init.sh"
SCRIPT_ARG0 = ROOT / "apps" / "claude-code-plugin" / "scripts" / "init.sh"


def run_common(script: str, tmp_path: Path, *, bin_dir: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env["PATH"] = f"{bin_dir or tmp_path / 'bin'}:/usr/bin:/bin"
    env["POWERMEM_DATA_DIR"] = str(tmp_path / ".powermem")
    command = textwrap.dedent(
        f"""
        set -eu
        . "{COMMON_SH}"
        {script}
        """
    )
    return subprocess.run(
        ["sh", "-c", command, str(SCRIPT_ARG0)],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    path.chmod(0o755)


def fake_curl_install_script() -> str:
    return r"""
        #!/usr/bin/env sh
        printf '%s\n' "$*" > "$HOME/curl_args"
        cat <<'INSTALL'
        mkdir -p "$HOME/.local/bin"
        cat > "$HOME/.local/bin/uv" <<'UV'
        #!/usr/bin/env sh
        echo fake-uv
        UV
        chmod +x "$HOME/.local/bin/uv"
        printf '%s\n' "${UV_DOWNLOAD_URL:-}" > "$HOME/uv_download_url"
        INSTALL
    """


def test_ensure_uv_reuses_existing_uv(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    write_executable(
        bin_dir / "uv",
        """
        #!/usr/bin/env sh
        echo existing-uv
        """,
    )

    result = run_common(
        """
        ensure_uv
        printf '%s\n' "$UV_BIN"
        """,
        tmp_path,
        bin_dir=bin_dir,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(bin_dir / "uv")
    assert not (tmp_path / "curl_args").exists()


def test_ensure_uv_installs_from_ustc_for_cn(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    write_executable(bin_dir / "curl", fake_curl_install_script())

    result = run_common(
        """
        detect_public_ip_country() { printf 'CN\n'; }
        ensure_uv
        printf 'UV_BIN=%s\n' "$UV_BIN"
        cat "$HOME/curl_args"
        printf 'DOWNLOAD=%s\n' "$(cat "$HOME/uv_download_url")"
        """,
        tmp_path,
        bin_dir=bin_dir,
    )

    assert result.returncode == 0, result.stderr
    assert f"UV_BIN={tmp_path}/.local/bin/uv" in result.stdout
    assert "mirrors.ustc.edu.cn/github-release/astral-sh/uv/LatestRelease/uv-installer.sh" in result.stdout
    assert "DOWNLOAD=https://mirrors.ustc.edu.cn/github-release/astral-sh/uv/LatestRelease/" in result.stdout


def test_ensure_uv_installs_from_astral_for_non_cn(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    write_executable(bin_dir / "curl", fake_curl_install_script())

    result = run_common(
        """
        detect_public_ip_country() { printf 'US\n'; }
        ensure_uv
        printf 'UV_BIN=%s\n' "$UV_BIN"
        cat "$HOME/curl_args"
        printf 'DOWNLOAD=%s\n' "$(cat "$HOME/uv_download_url")"
        """,
        tmp_path,
        bin_dir=bin_dir,
    )

    assert result.returncode == 0, result.stderr
    assert f"UV_BIN={tmp_path}/.local/bin/uv" in result.stdout
    assert "https://astral.sh/uv/install.sh" in result.stdout
    assert "DOWNLOAD=" in result.stdout
    assert "mirrors.ustc.edu.cn" not in result.stdout


def test_uvx_run_uses_tuna_index_for_cn(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    write_executable(
        bin_dir / "uv",
        """
        #!/usr/bin/env sh
        printf '%s\n' "$*" > "$HOME/uv_args"
        """,
    )

    result = run_common(
        """
        detect_public_ip_country() { printf 'CN\n'; }
        uvx_run --python /tmp/python3.11 --from powermem[server,seekdb] powermem-server --host 127.0.0.1 --port 8848
        cat "$HOME/uv_args"
        """,
        tmp_path,
        bin_dir=bin_dir,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith(
        "tool run --default-index https://pypi.tuna.tsinghua.edu.cn/simple "
        "--python /tmp/python3.11 --from powermem[server,seekdb] "
        "powermem-server --host 127.0.0.1 --port 8848"
    )


def test_init_uses_uvx_launcher_instead_of_plugin_venv_install() -> None:
    script = INIT_SH.read_text(encoding="utf-8")

    assert 'tool run \\' in script
    assert "--from \"$PACKAGE\"" in script
    assert "powermem-server --host 127.0.0.1 --port \"$port\"" in script
    assert "uv_pip_install" not in script
    assert "venv_powermem_server" not in script
