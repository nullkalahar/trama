#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:8080/saude}"

if command -v curl >/dev/null 2>&1; then
  code="$(curl -sS -o /tmp/trama_health_body -w '%{http_code}' "$URL" || true)"
  if [[ "$code" != "200" ]]; then
    echo "healthcheck falhou: status=$code url=$URL"
    cat /tmp/trama_health_body 2>/dev/null || true
    exit 1
  fi
  echo "healthcheck ok: $URL"
  exit 0
fi

echo "curl não encontrado para healthcheck"
exit 1
