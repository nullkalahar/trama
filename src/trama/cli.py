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
from trama_semente.semente import semente_compilar_arquivo
from .vm import VMError, run_bytecode_file, run_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trama", description="Ferramentas da linguagem trama")
    sub = parser.add_subparsers(dest="command")

    executar = sub.add_parser("executar", help="Executa um arquivo .trm")
    executar.add_argument("arquivo", help="Caminho do arquivo fonte .trm")

    executar_tbc = sub.add_parser("executar-tbc", help="Executa bytecode .tbc sem passar pelo compilador")
    executar_tbc.add_argument("arquivo", help="Caminho do arquivo bytecode (.tbc)")

    bytecode = sub.add_parser("bytecode", help="Mostra bytecode de um arquivo .trm")
    bytecode.add_argument("arquivo", help="Caminho do arquivo fonte .trm")

    compilar = sub.add_parser("compilar", help="Compila .trm para bytecode (pipeline self-host padrão)")
    compilar.add_argument("arquivo", help="Caminho do arquivo fonte .trm")
    compilar.add_argument("-o", "--saida", default="programa.tbc", help="Arquivo de saída")

    compilar_legado = sub.add_parser("compilar-legado", help="Compila .trm via implementação Python legada")
    compilar_legado.add_argument("arquivo", help="Caminho do arquivo fonte .trm")
    compilar_legado.add_argument("-o", "--saida", default="programa.tbc", help="Arquivo de saída")

    semente_compilar = sub.add_parser(
        "semente-compilar",
        help="Compila usando compilador semente mínimo de bootstrap",
    )
    semente_compilar.add_argument("arquivo", help="Caminho do arquivo fonte .trm")
    semente_compilar.add_argument("-o", "--saida", default="programa.tbc", help="Arquivo de saída")

    autocompilar = sub.add_parser(
        "autocompilar",
        help="Compila via toolchain self-hosted (.trm compilando .trm)",
    )
    autocompilar.add_argument("arquivo", help="Caminho do arquivo fonte .trm")
    autocompilar.add_argument("-o", "--saida", default="programa.tbc", help="Arquivo de saída")

    paridade = sub.add_parser(
        "paridade-selfhost",
        help="Valida paridade entre compilador clássico e compilador self-hosted",
    )
    paridade.add_argument("arquivo", help="Caminho do arquivo fonte .trm")

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
        if args.command == "executar-tbc":
            run_bytecode_file(args.arquivo)
            return 0

        if args.command == "bytecode":
            codigo = _ler_arquivo(args.arquivo)
            program = compile_source(codigo)
            sys.stdout.write(format_program(program))
            return 0

        if args.command == "compilar":
            resultado = _autocompilar_via_selfhost(args.arquivo, args.saida)
            print(f"Bytecode salvo em: {resultado['saida']}")
            return 0
        if args.command == "compilar-legado":
            codigo = _ler_arquivo(args.arquivo)
            program = compile_source(codigo)
            saida = Path(args.saida)
            if saida.parent != Path("."):
                saida.parent.mkdir(parents=True, exist_ok=True)
            payload = program_to_dict(program)
            saida.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Bytecode salvo em: {saida}")
            return 0
        if args.command == "semente-compilar":
            resultado = semente_compilar_arquivo(args.arquivo, args.saida)
            print(f"Bytecode semente salvo em: {resultado['saida']}")
            return 0
        if args.command == "autocompilar":
            resultado = _autocompilar_via_selfhost(args.arquivo, args.saida)
            print(f"Bytecode self-host salvo em: {resultado['saida']}")
            return 0
        if args.command == "paridade-selfhost":
            ok = _validar_paridade_selfhost(args.arquivo)
            if ok:
                print("Paridade self-host validada com sucesso.")
                return 0
            print("Paridade self-host falhou.", file=sys.stderr)
            return 1
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


def _selfhost_compiler_path() -> Path:
    candidates: list[Path] = []

    # Execução em código-fonte (repositório).
    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / "selfhost" / "compilador" / "mod.trm")

    # Execução empacotada (PyInstaller --onefile).
    meipass = getattr(sys, "_MEIPASS", None)  # type: ignore[attr-defined]
    if meipass:
        candidates.append(Path(str(meipass)) / "selfhost" / "compilador" / "mod.trm")

    # Instalação via pacote (opcional).
    candidates.append(Path("/usr/share/trama/selfhost/compilador/mod.trm"))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise OSError(f"Compilador self-host não encontrado. Locais verificados: {candidates}")


def _escape_trama_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _autocompilar_via_selfhost(arquivo_fonte: str, arquivo_saida: str) -> dict[str, object]:
    compiler_path = _selfhost_compiler_path().resolve()
    fonte = Path(arquivo_fonte).resolve()
    saida = Path(arquivo_saida).resolve()
    if saida.parent != Path("."):
        saida.parent.mkdir(parents=True, exist_ok=True)

    script = "\n".join(
        [
            "função principal()",
            f'    importe "{_escape_trama_string(str(compiler_path))}" como compilador',
            (
                "    retorne compilador[\"compilar_arquivo\"]("
                f'"{_escape_trama_string(str(fonte))}", "{_escape_trama_string(str(saida))}")'
            ),
            "fim",
            "",
        ]
    )
    from .vm import run_source  # import tardio para evitar ciclo

    resultado = run_source(script, source_path=str(compiler_path.parent / "runner_selfhost.trm"))
    if not isinstance(resultado, dict):
        raise RuntimeError("Compilação self-host retornou resultado inválido.")
    return resultado


def _validar_paridade_selfhost(arquivo_fonte: str) -> bool:
    fonte = Path(arquivo_fonte)
    codigo = _ler_arquivo(str(fonte))
    tradicional = json.loads(json.dumps(program_to_dict(compile_source(codigo)), ensure_ascii=False))
    saida = fonte.with_suffix(".selfhost.tbc")
    _autocompilar_via_selfhost(str(fonte), str(saida))
    selfhost = json.loads(saida.read_text(encoding="utf-8"))
    return tradicional == selfhost


if __name__ == "__main__":
    raise SystemExit(main())
