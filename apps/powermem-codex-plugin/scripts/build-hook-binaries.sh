#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
OUT="$ROOT/hooks/bin"
mkdir -p "$OUT"

build_one() {
  goos="$1"
  goarch="$2"
  ext="${3:-}"
  echo "building powermem-hook-${goos}-${goarch}${ext}"
  (cd "$ROOT" && CGO_ENABLED=0 GOOS="$goos" GOARCH="$goarch" go build -trimpath -ldflags="-s -w" -o "$OUT/powermem-hook-${goos}-${goarch}${ext}" ./cmd/powermem-hook)
}

build_one darwin amd64
build_one darwin arm64
build_one linux amd64
build_one linux arm64
build_one windows amd64 .exe
