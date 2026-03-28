#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="${1:-1.0.0}"
ARCH="${2:-amd64}"

scripts/build_selfhost.sh
scripts/build_standalone.sh
scripts/package_deb.sh "$VERSION" "$ARCH"

# Sanidade: compilar e executar sem usar compilador em runtime.
./dist/trama compilar examples/ola_mundo.trm -o dist/selfhost/ola_mundo.tbc
./dist/trama executar-tbc dist/selfhost/ola_mundo.tbc >/dev/null

echo "Release self-host pronta: build/trama_${VERSION}_${ARCH}.deb"
