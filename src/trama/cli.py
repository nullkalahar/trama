"""CLI da linguagem trama."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from .bytecode import format_program, program_to_dict
from .compiler import CompileError, compile_source
from .devtools import coverage_trm, format_trm, gerar_template_backend, lint_trm, run_test_runner
from .devtools import gerar_template_modulo, gerar_template_servico
from . import db_runtime
from .lexer import LexError
from . import observability_runtime
from .parser import ParseError
from . import testes_avancados_runtime
from . import tooling_runtime
from trama_semente.semente import semente_compilar_arquivo
from .vm import VMError, run_bytecode_file, run_source


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trama", description="Ferramentas da linguagem trama")
    parser.add_argument(
        "--diagnostico-runtime",
        action="store_true",
        help="Exibe backend de runtime/compilação ativo no binário atual",
    )
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

    template_servico = sub.add_parser("template-servico", help="Gera template canônico de serviço")
    template_servico.add_argument("destino", help="Diretório de destino")
    template_servico.add_argument("--forcar", action="store_true", help="Permite sobrescrever diretório não vazio")
    template_servico.add_argument("--json", action="store_true", help="Saída em JSON")

    template_modulo = sub.add_parser("template-modulo", help="Gera template canônico de módulo")
    template_modulo.add_argument("destino", help="Diretório de destino")
    template_modulo.add_argument("--nome", default="modulo_exemplo", help="Nome canônico do módulo")
    template_modulo.add_argument("--forcar", action="store_true", help="Permite sobrescrever diretório não vazio")
    template_modulo.add_argument("--json", action="store_true", help="Saída em JSON")

    openapi = sub.add_parser("openapi-gerar", help="Gera OpenAPI a partir de contrato em JSON")
    openapi.add_argument("--contrato", required=True, help="Arquivo JSON com contrato (paths/openapi ou rota simplificada)")
    openapi.add_argument("--saida", required=True, help="Arquivo OpenAPI de saída (.json)")
    openapi.add_argument("--titulo", default="API Trama", help="Título da API")
    openapi.add_argument("--versao", default="1.0.0", help="Versão da API")
    openapi.add_argument("--servidor", default="", help="URL base do servidor (opcional)")

    sdk = sub.add_parser("sdk-gerar", help="Gera SDK cliente a partir de OpenAPI")
    sdk.add_argument("--openapi", required=True, help="Arquivo OpenAPI JSON")
    sdk.add_argument("--saida", required=True, help="Arquivo SDK de saída")
    sdk.add_argument("--linguagem", default="python", choices=["python", "typescript", "ts"], help="Linguagem do SDK")
    sdk.add_argument("--cliente", default="ClienteApiTrama", help="Nome da classe cliente")

    admin_usuario_criar = sub.add_parser("admin-usuario-criar", help="Cria usuário administrativo local")
    admin_usuario_criar.add_argument("--id", required=True, help="ID do usuário")
    admin_usuario_criar.add_argument("--nome", default="", help="Nome do usuário")
    admin_usuario_criar.add_argument("--papeis", default="", help="Papeis separados por vírgula")

    admin_usuario_listar = sub.add_parser("admin-usuario-listar", help="Lista usuários administrativos locais")
    admin_usuario_listar.add_argument("--json", action="store_true", help="Saída em JSON")

    admin_permissao = sub.add_parser("admin-permissao-conceder", help="Concede permissões para usuário administrativo")
    admin_permissao.add_argument("--id", required=True, help="ID do usuário")
    admin_permissao.add_argument("--permissoes", required=True, help="Permissões separadas por vírgula")

    admin_jobs = sub.add_parser("admin-jobs-listar", help="Lista resumo operacional de jobs")
    admin_jobs.add_argument("--json", action="store_true", help="Saída em JSON")

    admin_manut = sub.add_parser("admin-manutencao-status", help="Status de manutenção operacional")
    admin_manut.add_argument("--json", action="store_true", help="Saída em JSON")

    mig_aplicar = sub.add_parser("migracao-aplicar-v2", help="Aplica migração versionada v2 padronizada")
    mig_aplicar.add_argument("--dsn", required=True, help="DSN de banco")
    mig_aplicar.add_argument("--versao", required=True, help="Versão da migração")
    mig_aplicar.add_argument("--nome", required=True, help="Nome da migração")
    mig_aplicar.add_argument("--up-arquivo", required=True, help="Arquivo SQL up")
    mig_aplicar.add_argument("--down-arquivo", default="", help="Arquivo SQL down")
    mig_aplicar.add_argument("--ambiente", default="dev", help="Ambiente: dev/teste/prod")
    mig_aplicar.add_argument("--dry-run", action="store_true", help="Executa em modo de simulação")

    mig_trilha = sub.add_parser("migracao-trilha-listar", help="Lista trilha de migrações v2")
    mig_trilha.add_argument("--dsn", required=True, help="DSN de banco")
    mig_trilha.add_argument("--limite", default=20, type=int, help="Limite de registros")
    mig_trilha.add_argument("--json", action="store_true", help="Saída em JSON")

    seed_aplicar = sub.add_parser("seed-aplicar-ambiente", help="Aplica seed por ambiente padronizada")
    seed_aplicar.add_argument("--dsn", required=True, help="DSN de banco")
    seed_aplicar.add_argument("--ambiente", required=True, help="Ambiente: dev/teste/prod")
    seed_aplicar.add_argument("--nome", required=True, help="Nome da seed")
    seed_aplicar.add_argument("--sql-arquivo", required=True, help="Arquivo SQL da seed")

    op_diag = sub.add_parser("operacao-diagnostico", help="Diagnóstico operacional padronizado")
    op_diag.add_argument("--json", action="store_true", help="Saída em JSON")

    op_smoke = sub.add_parser("operacao-smoke-check", help="Executa smoke checks HTTP")
    op_smoke.add_argument("--base-url", required=True, help="URL base da aplicação")
    op_smoke.add_argument("--timeout", default=2.0, type=float, help="Timeout por requisição")
    op_smoke.add_argument("--json", action="store_true", help="Saída em JSON")

    v208 = sub.add_parser("testes-avancados-v208", help="Executa harness v2.0.8 (integracao/e2e/carga/contrato/caos)")
    v208.add_argument("--perfil", default="completo", choices=["completo", "rapido"], help="Perfil de execucao")
    v208.add_argument("--sem-postgres", action="store_true", help="Nao valida fixture PostgreSQL")
    v208.add_argument("--sem-redis", action="store_true", help="Nao valida fixture Redis")
    v208.add_argument("--saida-json", default=".local/test-results/v208_relatorio.json", help="Arquivo de relatorio JSON")
    v208.add_argument("--saida-md", default=".local/test-results/v208_relatorio.md", help="Arquivo de relatorio Markdown")
    v208.add_argument("--json", action="store_true", help="Exibe resumo final em JSON")

    v212 = sub.add_parser(
        "testes-avancados-v212",
        help="Executa suite critica v2.1.2 (unitario/integracao/contrato/paridade/caos/seguranca)",
    )
    v212.add_argument("--perfil", default="completo", choices=["completo", "rapido"], help="Perfil de execucao")
    v212.add_argument("--saida-json", default=".local/test-results/v212_relatorio.json", help="Arquivo de relatorio JSON")
    v212.add_argument("--saida-md", default=".local/test-results/v212_relatorio.md", help="Arquivo de relatorio Markdown")
    v212.add_argument("--json", action="store_true", help="Exibe resumo final em JSON")

    sub.add_parser("repl", help="Abre REPL (planejado para fase futura)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if bool(args.diagnostico_runtime):
        # Canônico pt-BR
        print("backend_runtime=python_legado")
        print("backend_compilador=python_com_ponte_selfhost")
        print("requer_python_host=sim")
        # Compatibilidade (legado/inglês)
        print("runtime_backend=python_legacy")
        print("compilador_backend=python_com_selfhost_bridge")
        print("python_host_required=sim")
        return 0

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
            program = compile_source(codigo, arquivo=args.arquivo)
            sys.stdout.write(format_program(program))
            return 0

        if args.command == "compilar":
            resultado = _autocompilar_via_selfhost(args.arquivo, args.saida)
            print(f"Bytecode salvo em: {resultado['saida']}")
            return 0
        if args.command == "compilar-legado":
            codigo = _ler_arquivo(args.arquivo)
            program = compile_source(codigo, arquivo=args.arquivo)
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
        if args.command == "template-servico":
            report = gerar_template_servico(args.destino, forcar=bool(args.forcar))
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(f"Template de serviço criado em: {report['destino']}")
            return 0
        if args.command == "template-modulo":
            report = gerar_template_modulo(args.destino, nome_modulo=args.nome, forcar=bool(args.forcar))
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(f"Template de módulo criado em: {report['destino']}")
            return 0
        if args.command == "openapi-gerar":
            contrato = json.loads(Path(args.contrato).read_text(encoding="utf-8"))
            if "openapi" in contrato and "paths" in contrato:
                spec = contrato
                if args.titulo:
                    spec.setdefault("info", {})
                    if isinstance(spec["info"], dict):
                        spec["info"]["title"] = args.titulo
                        spec["info"]["version"] = args.versao
                if args.servidor:
                    spec["servers"] = [{"url": args.servidor}]
            else:
                spec = {
                    "openapi": "3.0.3",
                    "info": {"title": args.titulo, "version": args.versao},
                    "servers": [{"url": args.servidor}] if args.servidor else [],
                    "paths": dict(contrato.get("paths", {})),
                }
            out = tooling_runtime.salvar_openapi(spec, args.saida)
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0
        if args.command == "sdk-gerar":
            spec = json.loads(Path(args.openapi).read_text(encoding="utf-8"))
            out = tooling_runtime.gerar_sdk_cliente(spec, args.saida, linguagem=args.linguagem, nome_cliente=args.cliente)
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0
        if args.command == "admin-usuario-criar":
            estado = _admin_carregar_estado()
            uid = str(args.id)
            usuarios = dict(estado.get("usuarios", {}))
            usuario = dict(usuarios.get(uid, {}))
            usuario["id"] = uid
            usuario["nome"] = str(args.nome or usuario.get("nome", ""))
            papeis = [p.strip() for p in str(args.papeis or "").split(",") if p.strip()]
            usuario["papeis"] = sorted(set(list(usuario.get("papeis", [])) + papeis))
            usuario.setdefault("permissoes", [])
            usuarios[uid] = usuario
            estado["usuarios"] = usuarios
            _admin_salvar_estado(estado)
            print(json.dumps({"ok": True, "usuario": usuario}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "admin-usuario-listar":
            estado = _admin_carregar_estado()
            usuarios = list(dict(estado.get("usuarios", {})).values())
            payload = {"ok": True, "total": len(usuarios), "usuarios": usuarios}
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"Total usuários: {len(usuarios)}")
                for u in usuarios:
                    print(f"- {u.get('id')} ({u.get('nome', '')})")
            return 0
        if args.command == "admin-permissao-conceder":
            estado = _admin_carregar_estado()
            uid = str(args.id)
            usuarios = dict(estado.get("usuarios", {}))
            if uid not in usuarios:
                raise RuntimeError("Usuário administrativo não encontrado.")
            usuario = dict(usuarios[uid])
            perms = [p.strip() for p in str(args.permissoes).split(",") if p.strip()]
            usuario["permissoes"] = sorted(set(list(usuario.get("permissoes", [])) + perms))
            usuarios[uid] = usuario
            estado["usuarios"] = usuarios
            _admin_salvar_estado(estado)
            print(json.dumps({"ok": True, "usuario": usuario}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "admin-jobs-listar":
            snap = observability_runtime.metricas_snapshot()
            payload = {"ok": True, "jobs": {"metricas": snap}}
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print("Resumo de jobs coletado de métricas.")
            return 0
        if args.command == "admin-manutencao-status":
            payload = {
                "ok": True,
                "estado": "operacional",
                "dashboards": tooling_runtime.dashboards_operacionais_prontos().get("dashboards", []),
                "runbooks": tooling_runtime.runbooks_incidentes_prontos().get("runbooks", []),
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print("Manutenção operacional: estado=operacional")
            return 0
        if args.command == "migracao-aplicar-v2":
            up_sql = Path(args.up_arquivo).read_text(encoding="utf-8")
            down_sql = Path(args.down_arquivo).read_text(encoding="utf-8") if args.down_arquivo else ""
            out = asyncio.run(
                _db_migracao_aplicar_v2(
                    dsn=args.dsn,
                    versao=args.versao,
                    nome=args.nome,
                    up_sql=up_sql,
                    down_sql=down_sql,
                    ambiente=args.ambiente,
                    dry_run=bool(args.dry_run),
                )
            )
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0
        if args.command == "migracao-trilha-listar":
            trilha = asyncio.run(_db_migracao_trilha_listar(args.dsn, limite=int(args.limite)))
            if args.json:
                print(json.dumps({"ok": True, "trilha": trilha}, ensure_ascii=False, indent=2))
            else:
                print(f"Trilha: {len(trilha)} registros")
                for item in trilha:
                    print(f"- {item.get('versao')} {item.get('nome')} [{item.get('status')}]")
            return 0
        if args.command == "seed-aplicar-ambiente":
            sql = Path(args.sql_arquivo).read_text(encoding="utf-8")
            out = asyncio.run(_db_seed_aplicar_ambiente(args.dsn, args.ambiente, args.nome, sql))
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0
        if args.command == "operacao-diagnostico":
            payload = _operacao_diagnostico()
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"estado={payload['estado']} runtime={payload['runtime']}")
            return 0
        if args.command == "operacao-smoke-check":
            payload = tooling_runtime.smoke_checks_http(base_url=args.base_url, timeout_segundos=float(args.timeout))
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"smoke_ok={payload['ok']} duracao_ms={round(float(payload['duracao_ms']), 2)}")
            return 0
        if args.command == "testes-avancados-v208":
            rel = testes_avancados_runtime.executar_suite_v208(
                perfil=str(args.perfil),
                validar_postgres=not bool(args.sem_postgres),
                validar_redis=not bool(args.sem_redis),
            )
            out_json = testes_avancados_runtime.salvar_relatorio_json(rel, str(args.saida_json))
            out_md = testes_avancados_runtime.salvar_relatorio_markdown(rel, str(args.saida_md))
            payload = {
                "ok": bool(rel.get("ok")),
                "perfil": rel.get("perfil"),
                "duracao_ms": rel.get("duracao_ms"),
                "arquivo_json": out_json.get("arquivo"),
                "arquivo_md": out_md.get("arquivo"),
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"v208_ok={payload['ok']} duracao_ms={round(float(payload['duracao_ms']), 2)}")
                print(f"relatorio_json={payload['arquivo_json']}")
                print(f"relatorio_md={payload['arquivo_md']}")
            return 0 if bool(rel.get("ok")) else 1
        if args.command == "testes-avancados-v212":
            rel = testes_avancados_runtime.executar_suite_v212(
                perfil=str(args.perfil),
            )
            out_json = testes_avancados_runtime.salvar_relatorio_json(rel, str(args.saida_json))
            out_md = testes_avancados_runtime.salvar_relatorio_markdown(rel, str(args.saida_md))
            payload = {
                "ok": bool(rel.get("ok")),
                "perfil": rel.get("perfil"),
                "duracao_ms": rel.get("duracao_ms"),
                "arquivo_json": out_json.get("arquivo"),
                "arquivo_md": out_md.get("arquivo"),
                "baseline": rel.get("baseline", {}),
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"v212_ok={payload['ok']} duracao_ms={round(float(payload['duracao_ms']), 2)}")
                print(f"relatorio_json={payload['arquivo_json']}")
                print(f"relatorio_md={payload['arquivo_md']}")
            return 0 if bool(rel.get("ok")) else 1
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


def _admin_estado_arquivo() -> Path:
    p = Path(".local") / "admin_estado.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _admin_carregar_estado() -> dict[str, object]:
    path = _admin_estado_arquivo()
    if not path.exists():
        return {"usuarios": {}, "versao": "1"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"usuarios": {}, "versao": "1"}


def _admin_salvar_estado(estado: dict[str, object]) -> None:
    path = _admin_estado_arquivo()
    path.write_text(json.dumps(estado, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


async def _db_migracao_aplicar_v2(
    dsn: str,
    versao: str,
    nome: str,
    up_sql: str,
    down_sql: str,
    ambiente: str,
    dry_run: bool,
) -> dict[str, object]:
    conn = await db_runtime.conectar(dsn)
    try:
        return await db_runtime.migracao_aplicar_versionada_v2(
            conn=conn,
            versao=versao,
            nome=nome,
            up_sql=up_sql,
            down_sql=down_sql,
            ambiente=ambiente,
            dry_run=dry_run,
        )
    finally:
        await db_runtime.fechar(conn)


async def _db_migracao_trilha_listar(dsn: str, limite: int) -> list[dict[str, object]]:
    conn = await db_runtime.conectar(dsn)
    try:
        return await db_runtime.migracao_trilha_listar(conn, limite=limite)
    finally:
        await db_runtime.fechar(conn)


async def _db_seed_aplicar_ambiente(dsn: str, ambiente: str, nome: str, sql: str) -> dict[str, object]:
    conn = await db_runtime.conectar(dsn)
    try:
        return await db_runtime.seed_aplicar_ambiente(conn, ambiente, nome, sql)
    finally:
        await db_runtime.fechar(conn)


def _operacao_diagnostico() -> dict[str, object]:
    alertas = observability_runtime.alertas_avaliar()
    estado = "ok" if str(alertas.get("estado", "ok")) == "ok" else "degradado"
    return {
        "ok": True,
        "estado": estado,
        "runtime": "python_legado",
        "backend_compilador": "python_com_ponte_selfhost",
        "alertas": alertas,
        "dashboards": tooling_runtime.dashboards_operacionais_prontos().get("dashboards", []),
        "runbooks": tooling_runtime.runbooks_incidentes_prontos().get("runbooks", []),
    }


if __name__ == "__main__":
    raise SystemExit(main())
