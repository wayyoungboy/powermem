#!/usr/bin/env bash
# Build standalone Linux amd64 command binaries for release packaging.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python}"
DIST="${ROOT}/dist-binaries"
BUILD="${ROOT}/build/linux-binaries"
ENTRYPOINTS="${BUILD}/entrypoints"
BIN_DIR="${DIST}/bin"

cd "${ROOT}"

VERSION="$("${PYTHON}" - <<'PY'
import tomllib
with open("pyproject.toml", "rb") as f:
    print(tomllib.load(f)["project"]["version"])
PY
)"

rm -rf "${BUILD}" "${DIST}"
mkdir -p "${ENTRYPOINTS}" "${BIN_DIR}"

cat > "${ENTRYPOINTS}/powermem_cli_entry.py" <<'PY'
from powermem.cli.main import cli

if __name__ == "__main__":
    cli()
PY

cat > "${ENTRYPOINTS}/powermem_server_entry.py" <<'PY'
from server.cli.server import server

if __name__ == "__main__":
    server()
PY

cat > "${ENTRYPOINTS}/powermem_mcp_entry.py" <<'PY'
from powermem.mcp.server import main

if __name__ == "__main__":
    main()
PY

COMMON_OPTS=(
  --onefile
  --clean
  --noconfirm
  --distpath "${BIN_DIR}"
  --workpath "${BUILD}/pyinstaller"
  --specpath "${BUILD}/specs"
  --collect-all powermem
  --collect-all server
  --collect-all fastmcp
  --collect-all pyobvector
  --copy-metadata powermem
  --copy-metadata pydantic
  --copy-metadata pydantic-settings
  --copy-metadata fastmcp
  --copy-metadata pyobvector
)

build_binary() {
  local name="$1"
  local entrypoint="$2"
  echo "Building ${name}"
  "${PYTHON}" -m PyInstaller "${COMMON_OPTS[@]}" --name "${name}" "${entrypoint}"
  chmod +x "${BIN_DIR}/${name}"
  file "${BIN_DIR}/${name}"
  ldd "${BIN_DIR}/${name}"
}

build_binary powermem "${ENTRYPOINTS}/powermem_cli_entry.py"
build_binary powermem-server "${ENTRYPOINTS}/powermem_server_entry.py"
build_binary powermem-mcp "${ENTRYPOINTS}/powermem_mcp_entry.py"

PACKAGE_DIR="${DIST}/powermem-${VERSION}-linux-amd64"
mkdir -p "${PACKAGE_DIR}/bin"
cp -av "${BIN_DIR}/powermem" "${BIN_DIR}/powermem-server" "${BIN_DIR}/powermem-mcp" "${PACKAGE_DIR}/bin/"

cat > "${PACKAGE_DIR}/README.md" <<EOF
# PowerMem Linux amd64 binaries

Built on CentOS 7 for broader glibc compatibility.

Included commands:

- powermem
- powermem-server
- powermem-mcp

Version: ${VERSION}
EOF

( cd "${DIST}" && tar -czf "powermem-${VERSION}-linux-amd64-binaries.tar.gz" "powermem-${VERSION}-linux-amd64" )
( cd "${DIST}" && sha256sum "powermem-${VERSION}-linux-amd64-binaries.tar.gz" > SHA256SUMS )

echo "Built Linux amd64 binaries:"
ls -lh "${BIN_DIR}" "${DIST}/powermem-${VERSION}-linux-amd64-binaries.tar.gz" "${DIST}/SHA256SUMS"
