#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION="${1:-0.1.0}"
ARCH="${2:-amd64}"
PKG_NAME="trama"
PKG_DIR="build/${PKG_NAME}_${VERSION}_${ARCH}"

BIN_SRC=""
if [[ -x "dist/native/trama-native" ]]; then
  BIN_SRC="dist/native/trama-native"
elif [[ -x "dist/trama" ]]; then
  BIN_SRC="dist/trama"
else
  echo "Erro: binário não encontrado. Rode scripts/build_native_stub.sh (preferencial) ou scripts/build_standalone.sh."
  exit 1
fi

rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN" "$PKG_DIR/usr/bin" "$PKG_DIR/usr/share/doc/trama" "$PKG_DIR/usr/share/trama"

install -m 0755 "$BIN_SRC" "$PKG_DIR/usr/bin/trama"
install -m 0644 README.md "$PKG_DIR/usr/share/doc/trama/README.md"
cp -R selfhost "$PKG_DIR/usr/share/trama/selfhost"

cat > "$PKG_DIR/DEBIAN/control" <<CONTROL
Package: trama
Version: $VERSION
Section: devel
Priority: optional
Architecture: $ARCH
Maintainer: nullkalahar <nullkalahar@users.noreply.github.com>
Description: Linguagem trama (pt-BR) com compilador e VM nativos
 Pacote binario priorizando backend 100% nativo.
CONTROL

dpkg-deb --build "$PKG_DIR"

echo "Pacote .deb gerado em: ${PKG_DIR}.deb"
