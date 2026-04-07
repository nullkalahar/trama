#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re

from trama.builtins import make_builtins
from trama.cli import build_parser
from trama.lexer import KEYWORDS


def _comandos_cli() -> list[str]:
    parser = build_parser()
    comandos: set[str] = set()
    for acao in parser._actions:  # type: ignore[attr-defined]
        if hasattr(acao, "choices") and isinstance(acao.choices, dict):
            comandos.update(str(k) for k in acao.choices.keys())
    return sorted(comandos)


def _classificar_builtin(nome: str) -> str:
    tokens_ingles = (
        "async",
        "await",
        "http_get",
        "http_post",
        "cache_dist",
        "community_",
        "channel_",
        "role_",
        "member_",
        "moderation_",
        "campaign_",
        "sync_",
        "security",
        "openapi",
        "sdk",
        "websocket",
        "realtime",
        "dashboard",
        "runbook",
    )
    if any(t in nome for t in tokens_ingles):
        return "alias_compatibilidade"
    if re.fullmatch(r"[a-z0-9_]+", nome):
        return "canonico_ou_neutro"
    return "outro"


def gerar(saida: Path) -> None:
    palavras_lexer = sorted(KEYWORDS.keys())
    comandos_cli = _comandos_cli()
    builtins = sorted(make_builtins().keys())

    builtins_canonicos = [b for b in builtins if _classificar_builtin(b) == "canonico_ou_neutro"]
    builtins_alias = [b for b in builtins if _classificar_builtin(b) == "alias_compatibilidade"]
    builtins_outros = [b for b in builtins if _classificar_builtin(b) == "outro"]

    linhas: list[str] = []
    linhas.append("# Referencia de Capacidades v2.1.2")
    linhas.append("")
    linhas.append("Documento gerado automaticamente a partir do codigo-fonte da Trama.")
    linhas.append("")
    linhas.append("## Escopo")
    linhas.append("")
    linhas.append("- Lexer: todos os lexemas de palavras-chave reconhecidos.")
    linhas.append("- CLI: todos os comandos oficiais registrados no parser.")
    linhas.append("- Builtins: toda a superficie exposta pela VM/runtime.")
    linhas.append("")
    linhas.append("## lexer_lexemas")
    linhas.append("")
    linhas.append(f"Total: `{len(palavras_lexer)}`")
    linhas.append("")
    for item in palavras_lexer:
        linhas.append(f"- `{item}`")
    linhas.append("")
    linhas.append("## cli_comandos")
    linhas.append("")
    linhas.append(f"Total: `{len(comandos_cli)}`")
    linhas.append("")
    for item in comandos_cli:
        linhas.append(f"- `{item}`")
    linhas.append("")
    linhas.append("## builtins_superficie_total")
    linhas.append("")
    linhas.append(f"Total: `{len(builtins)}`")
    linhas.append("")
    for item in builtins:
        linhas.append(f"- `{item}`")
    linhas.append("")
    linhas.append("## builtins_canonicos_ou_neutros")
    linhas.append("")
    linhas.append(f"Total: `{len(builtins_canonicos)}`")
    linhas.append("")
    for item in builtins_canonicos:
        linhas.append(f"- `{item}`")
    linhas.append("")
    linhas.append("## builtins_aliases_compatibilidade")
    linhas.append("")
    linhas.append(f"Total: `{len(builtins_alias)}`")
    linhas.append("")
    for item in builtins_alias:
        linhas.append(f"- `{item}`")
    if builtins_outros:
        linhas.append("")
        linhas.append("## builtins_outros")
        linhas.append("")
        linhas.append(f"Total: `{len(builtins_outros)}`")
        linhas.append("")
        for item in builtins_outros:
            linhas.append(f"- `{item}`")

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text("\n".join(linhas).strip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera referencia completa de capacidades da linguagem.")
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("docs/REFERENCIA_CAPACIDADES_V2_1_2.md"),
        help="Arquivo markdown de saida.",
    )
    args = parser.parse_args()
    gerar(args.saida)
    print(f"OK: referencia gerada em {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
