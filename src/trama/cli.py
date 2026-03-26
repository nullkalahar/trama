"""CLI inicial da linguagem trama."""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trama", description="Ferramentas da linguagem trama")
    sub = parser.add_subparsers(dest="command")

    executar = sub.add_parser("executar", help="Executa um arquivo .trm")
    executar.add_argument("arquivo", help="Caminho do arquivo fonte .trm")

    bytecode = sub.add_parser("bytecode", help="Mostra bytecode de um arquivo .trm")
    bytecode.add_argument("arquivo", help="Caminho do arquivo fonte .trm")

    compilar = sub.add_parser("compilar", help="Compila .trm para bytecode")
    compilar.add_argument("arquivo", help="Caminho do arquivo fonte .trm")
    compilar.add_argument("-o", "--saida", default="programa.tbc", help="Arquivo de saída")

    sub.add_parser("repl", help="Abre REPL (planejado para fase futura)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "repl":
        print("REPL ainda não implementado.")
        return 0

    if args.command in {"executar", "bytecode", "compilar"}:
        print(f"Comando '{args.command}' reconhecido. Implementação em andamento.")
        return 0

    print("Comando inválido.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
