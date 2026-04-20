#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="${1:-2.1.3}"
ARCH="${2:-amd64}"

scripts/build_native_stub.sh
scripts/package_deb.sh "$VERSION" "$ARCH"

./dist/native/trama-native --diagnostico-runtime | tee .local/test-results/v209_diagnostico_runtime.txt >/dev/null

echo "Release nativa pronta: build/trama_${VERSION}_${ARCH}.deb"
