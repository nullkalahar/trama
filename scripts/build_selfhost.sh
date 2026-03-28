#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist/selfhost"

mkdir -p "${OUT_DIR}"

PYTHONPATH="${ROOT_DIR}/src" python3 -m trama.cli compilar "${ROOT_DIR}/selfhost/compilador/mod.trm" -o "${OUT_DIR}/compilador.tbc"
PYTHONPATH="${ROOT_DIR}/src" python3 -m trama.cli compilar "${ROOT_DIR}/selfhost/runtime/mod.trm" -o "${OUT_DIR}/runtime.tbc"

echo "Build self-host concluído em ${OUT_DIR}"
