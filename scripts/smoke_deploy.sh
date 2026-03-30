#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker não encontrado"
  exit 1
fi

echo "[smoke] build imagem"
docker build -t trama:smoke .

echo "[smoke] executando container"
docker run --rm trama:smoke trama --help >/tmp/trama_smoke_out.txt

echo "[smoke] saída"
cat /tmp/trama_smoke_out.txt

echo "[smoke] ok"
