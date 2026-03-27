"""CLI da linguagem trama."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .bytecode import format_program, program_to_dict
from .compiler import CompileError, compile_source
from .lexer import LexError
from .parser import ParseError
from .vm import VMError, run_source


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

    try:
        if args.command == "executar":
            codigo = _ler_arquivo(args.arquivo)
            run_source(codigo, source_path=args.arquivo)
            return 0

        if args.command == "bytecode":
            codigo = _ler_arquivo(args.arquivo)
            program = compile_source(codigo)
            sys.stdout.write(format_program(program))
            return 0

        if args.command == "compilar":
            codigo = _ler_arquivo(args.arquivo)
            program = compile_source(codigo)
            saida = Path(args.saida)
            if saida.parent != Path("."):
                saida.parent.mkdir(parents=True, exist_ok=True)
            payload = program_to_dict(program)
            saida.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Bytecode salvo em: {saida}")
            return 0
    except (LexError, ParseError, CompileError, VMError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    print("Comando inválido.", file=sys.stderr)
    return 2


def _ler_arquivo(caminho: str) -> str:
    path = Path(caminho)
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
