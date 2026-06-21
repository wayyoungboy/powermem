from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_binary_builder_verifies_miniconda_installer_checksum() -> None:
    dockerfile = (ROOT / "docker" / "Dockerfile.binaries-centos7").read_text()

    assert "ARG MINICONDA_SHA256=" in dockerfile
    assert "634d76df5e489c44ade4085552b97bebc786d49245ed1a830022b0b406de5817" in dockerfile
    assert 'echo "${MINICONDA_SHA256}  /tmp/miniconda.sh" | sha256sum -c -' in dockerfile


def test_release_binary_help_smokes_are_bounded() -> None:
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text()

    assert 'timeout 10s "${BIN_ROOT}/bin/powermem" --help' in workflow
    assert 'timeout 10s "${BIN_ROOT}/bin/powermem-server" --help' in workflow


def test_release_binary_tarball_bin_contents_are_exact() -> None:
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text()

    assert 'find "${BIN_ROOT}/bin" -mindepth 1 -maxdepth 1 -printf "%f\\n"' in workflow
    assert 'printf "powermem\\npowermem-mcp\\npowermem-server\\n"' in workflow
    assert "diff -u /tmp/linux-binary-expected-bin-files.txt /tmp/linux-binary-bin-files.txt" in workflow


def test_release_binary_server_smoke_checks_health_json_and_dashboard() -> None:
    workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text()

    assert "http://localhost:18848/api/v1/system/health" in workflow
    assert "http://localhost:18848/dashboard/" in workflow
    assert '"success\\"[[:space:]]*:[[:space:]]*true"' in workflow
    assert '"status\\"[[:space:]]*:[[:space:]]*\\"healthy\\""' in workflow
