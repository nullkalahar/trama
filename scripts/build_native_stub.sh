#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/dist/native"
mkdir -p "$OUT_DIR"

cc "$ROOT_DIR/native/runtime_stub.c" -O2 -o "$OUT_DIR/trama-native-stub"
cc "$ROOT_DIR/native/trama_native.c" -O2 -pthread -lm -o "$OUT_DIR/trama-native"

echo "Stub nativo gerado em: $OUT_DIR/trama-native-stub"
echo "Runtime nativo gerado em: $OUT_DIR/trama-native"
