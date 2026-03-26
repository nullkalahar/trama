#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_PATH="${ROOT_DIR}/.venv-build"
if [[ ! -d "$VENV_PATH" ]]; then
  python3 -m venv "$VENV_PATH"
fi

"$VENV_PATH/bin/python" -m pip install --upgrade pip
"$VENV_PATH/bin/python" -m pip install -e .
"$VENV_PATH/bin/python" -m pip install pyinstaller

"$VENV_PATH/bin/python" -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name trama \
  --paths src \
  scripts/standalone_entry.py

echo "Standalone gerado em: $ROOT_DIR/dist/trama"
