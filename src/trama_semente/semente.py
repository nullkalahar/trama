"""Compilador semente mínimo de bootstrap.

Mantém escopo reduzido: compilar um arquivo .trm para .tbc.
"""

from __future__ import annotations

import json
from pathlib import Path

from trama.bytecode import program_to_dict
from trama.compiler import compile_source


def semente_compilar_arquivo(arquivo_fonte: str, arquivo_saida: str) -> dict[str, object]:
    fonte = Path(arquivo_fonte)
    saida = Path(arquivo_saida)
    codigo = fonte.read_text(encoding="utf-8")
    payload = program_to_dict(compile_source(codigo))
    if saida.parent != Path("."):
        saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "fonte": str(fonte), "saida": str(saida)}


# Alias transitório para compatibilidade.
seed_compilar_arquivo = semente_compilar_arquivo
