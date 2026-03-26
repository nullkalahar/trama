#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-packaging/apt-repo}"
DIST="${2:-stable}"
DEB_PATH="${3:-}"

if [[ -z "$DEB_PATH" ]]; then
  echo "Uso: $0 [repo_dir] [dist] <caminho_do_deb>"
  exit 1
fi

reprepro -b "$REPO_DIR" includedeb "$DIST" "$DEB_PATH"
echo "Pacote publicado no repo APT: $DEB_PATH"
