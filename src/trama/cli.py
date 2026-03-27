"""CLI da linguagem trama."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .bytecode import format_program, program_to_dict
from .compiler import CompileError, compile_source
from .devtools import coverage_trm, format_trm, gerar_template_backend, lint_trm, run_test_runner
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

    testar = sub.add_parser("testar", help="Executa o test runner oficial para arquivos .trm")
    testar.add_argument("alvo", nargs="?", default=".", help="Arquivo/pasta alvo")
    testar.add_argument("--json", action="store_true", help="Saída em JSON")

    lint = sub.add_parser("lint", help="Valida sintaxe/semântica dos arquivos .trm")
    lint.add_argument("alvo", nargs="?", default=".", help="Arquivo/pasta alvo")
    lint.add_argument("--json", action="store_true", help="Saída em JSON")

    fmt = sub.add_parser("formatar", help="Formata arquivos .trm")
    fmt.add_argument("alvo", nargs="?", default=".", help="Arquivo/pasta alvo")
    fmt.add_argument("--aplicar", action="store_true", help="Aplica mudanças em arquivo")
    fmt.add_argument("--json", action="store_true", help="Saída em JSON")

    cobertura = sub.add_parser("cobertura", help="Relatório de cobertura estática de módulos .trm")
    cobertura.add_argument("alvo", nargs="?", default=".", help="Arquivo/pasta alvo")
    cobertura.add_argument("--json", action="store_true", help="Saída em JSON")

    template = sub.add_parser("template-backend", help="Gera template oficial de backend em Trama")
    template.add_argument("destino", help="Diretório de destino")
    template.add_argument("--forcar", action="store_true", help="Permite sobrescrever diretório não vazio")
    template.add_argument("--json", action="store_true", help="Saída em JSON")

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
        if args.command == "testar":
            report = run_test_runner(args.alvo)
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(
                    f"Total: {report['total']} | Aprovados: {report['aprovados']} | "
                    f"Falhos: {report['falhos']}"
                )
                for item in report["detalhes"]:
                    if item["status"] == "ok":
                        print(f"[OK] {item['arquivo']}")
                    else:
                        print(f"[FALHA] {item['arquivo']}: {item.get('erro', '')}")
            return 0 if report["ok"] else 1
        if args.command == "lint":
            report = lint_trm(args.alvo)
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(f"Arquivos: {report['total_arquivos']} | Erros: {len(report['erros'])}")
                for err in report["erros"]:
                    print(f"[ERRO] {err['arquivo']}: {err['erro']}")
            return 0 if report["ok"] else 1
        if args.command == "formatar":
            report = format_trm(args.alvo, write=bool(args.aplicar))
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                mode = "aplicado" if args.aplicar else "somente análise"
                print(f"Modo: {mode} | Alterados: {report['total_alterados']}")
                for path in report["alterados"]:
                    print(path)
            return 0
        if args.command == "cobertura":
            report = coverage_trm(args.alvo)
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(f"Cobertura: {report['cobertura_percentual']}%")
                print(f"Cobertos: {len(report['cobertos'])} | Não cobertos: {len(report['nao_cobertos'])}")
            return 0
        if args.command == "template-backend":
            report = gerar_template_backend(args.destino, forcar=bool(args.forcar))
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(f"Template backend criado em: {report['destino']}")
            return 0
    except (LexError, ParseError, CompileError, VMError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    print("Comando inválido.", file=sys.stderr)
    return 2


def _ler_arquivo(caminho: str) -> str:
    path = Path(caminho)
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
