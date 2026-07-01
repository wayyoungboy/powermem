#!/usr/bin/env bash
# Build a portable zip of the Codex plugin for sharing or offline install.
# Output: apps/powermem-codex-plugin/dist/powermem-codex-plugin-<version>.zip
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${PLUGIN_ROOT}/../.." && pwd)"
DIST="${PLUGIN_ROOT}/dist"
PYTHON_BIN="${PYTHON_BIN:-python3}"

VERSION="$(
  "${PYTHON_BIN}" -c "import json; print(json.load(open('${PLUGIN_ROOT}/.codex-plugin/plugin.json'))['version'])"
)"
ZIP_NAME="powermem-codex-plugin-${VERSION}.zip"
ZIP_PATH="${DIST}/${ZIP_NAME}"

if ! command -v zip >/dev/null 2>&1; then
  echo "error: 'zip' not found. Install zip (for example: apt-get install zip) or zip manually." >&2
  exit 1
fi

bash "${PLUGIN_ROOT}/scripts/build-hook-binaries.sh"

mkdir -p "${DIST}"
TMP="$(mktemp -d)"
cleanup() { rm -rf "${TMP}"; }
trap cleanup EXIT

STAGE="${TMP}/powermem-codex-plugin"
PLUGIN_STAGE="${STAGE}/apps/powermem-codex-plugin"
MARKETPLACE_STAGE="${STAGE}/.agents/plugins"
mkdir -p "${PLUGIN_STAGE}" "${MARKETPLACE_STAGE}"

cp "${REPO_ROOT}/.agents/plugins/marketplace.json" "${MARKETPLACE_STAGE}/"
cp -R "${PLUGIN_ROOT}/.codex-plugin" "${PLUGIN_STAGE}/"
cp -R "${PLUGIN_ROOT}/hooks" "${PLUGIN_STAGE}/"
chmod +x "${PLUGIN_STAGE}/hooks/run-hook.sh" 2>/dev/null || true
cp -R "${PLUGIN_ROOT}/skills" "${PLUGIN_STAGE}/"
[[ -f "${PLUGIN_ROOT}/README.md" ]] && cp "${PLUGIN_ROOT}/README.md" "${PLUGIN_STAGE}/"
[[ -f "${PLUGIN_ROOT}/SETUP.md" ]] && cp "${PLUGIN_ROOT}/SETUP.md" "${PLUGIN_STAGE}/"
[[ -f "${PLUGIN_ROOT}/UNINSTALL.md" ]] && cp "${PLUGIN_ROOT}/UNINSTALL.md" "${PLUGIN_STAGE}/"
[[ -f "${PLUGIN_ROOT}/go.mod" ]] && cp "${PLUGIN_ROOT}/go.mod" "${PLUGIN_STAGE}/"
[[ -d "${PLUGIN_ROOT}/cmd" ]] && cp -R "${PLUGIN_ROOT}/cmd" "${PLUGIN_STAGE}/"
[[ -d "${PLUGIN_ROOT}/scripts" ]] && cp -R "${PLUGIN_ROOT}/scripts" "${PLUGIN_STAGE}/"
[[ -f "${PLUGIN_ROOT}/codex-flow.svg" ]] && cp "${PLUGIN_ROOT}/codex-flow.svg" "${PLUGIN_STAGE}/"

rm -f "${ZIP_PATH}"
(cd "${TMP}" && zip -r "${ZIP_PATH}" "powermem-codex-plugin" -x "*.DS_Store" -x "*__pycache__*" -x "*.pyc")

echo "Packaged: ${ZIP_PATH}"
ls -lh "${ZIP_PATH}"
