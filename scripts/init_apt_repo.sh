#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REPO_DIR="${1:-packaging/apt-repo}"
DIST="${2:-stable}"
COMP="${3:-main}"
CODENAME="${4:-trama}"
GPG_KEY_ID="${5:-}"

if [[ -z "$GPG_KEY_ID" ]]; then
  echo "Uso: $0 [repo_dir] [dist] [component] [codename] <gpg_key_id>"
  exit 1
fi

mkdir -p "$REPO_DIR/conf"

cat > "$REPO_DIR/conf/distributions" <<CONF
Origin: trama
Label: trama
Codename: $CODENAME
Suite: $DIST
Architectures: amd64
Components: $COMP
Description: Repositório APT da linguagem trama
SignWith: $GPG_KEY_ID
CONF

echo "Repo APT inicializado em $REPO_DIR"
echo "Para adicionar um pacote:"
echo "  reprepro -b $REPO_DIR includedeb $DIST /caminho/trama_versao_amd64.deb"
