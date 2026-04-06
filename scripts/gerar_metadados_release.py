#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def gerar(versao: str, artefatos: list[Path], saida: Path) -> dict:
    payload = {
        "versao": versao,
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "artefatos": [],
    }
    for p in artefatos:
        if not p.exists():
            payload["artefatos"].append(
                {
                    "caminho": str(p),
                    "existe": False,
                    "tamanho_bytes": 0,
                    "sha256": None,
                }
            )
            continue
        payload["artefatos"].append(
            {
                "caminho": str(p),
                "existe": True,
                "tamanho_bytes": p.stat().st_size,
                "sha256": _sha256(p),
            }
        )

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera metadados auditaveis da release.")
    parser.add_argument("--versao", required=True)
    parser.add_argument("--saida", required=True, type=Path)
    parser.add_argument("--artefato", required=True, action="append", type=Path)
    args = parser.parse_args()

    payload = gerar(args.versao, args.artefato, args.saida)
    print(json.dumps({"ok": True, "versao": payload["versao"], "saida": str(args.saida)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
