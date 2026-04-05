"""Ferramentas oficiais de desenvolvimento da Trama (v0.9)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
from typing import Any

from .compiler import CompileError, compile_source
from .lexer import LexError
from .parser import ParseError
from .vm import VMError, run_source


@dataclass
class LintIssue:
    arquivo: str
    erro: str


def discover_trm_files(target: str) -> list[Path]:
    root = Path(target)
    if root.is_file() and root.suffix == ".trm":
        return [root]
    return sorted([p for p in root.rglob("*.trm") if p.is_file()])


def run_test_runner(target: str) -> dict[str, Any]:
    files = [p for p in discover_trm_files(target) if p.name.startswith("test_")]
    total = len(files)
    passed = 0
    failed = 0
    details: list[dict[str, str]] = []

    for file in files:
        try:
            run_source(file.read_text(encoding="utf-8"), source_path=str(file))
            passed += 1
            details.append({"arquivo": str(file), "status": "ok"})
        except (LexError, ParseError, CompileError, VMError, OSError) as exc:
            failed += 1
            details.append({"arquivo": str(file), "status": "falha", "erro": str(exc)})

    return {
        "total": total,
        "aprovados": passed,
        "falhos": failed,
        "ok": failed == 0,
        "detalhes": details,
    }


def lint_trm(target: str) -> dict[str, Any]:
    issues: list[LintIssue] = []
    for file in discover_trm_files(target):
        try:
            compile_source(file.read_text(encoding="utf-8"))
        except (LexError, ParseError, CompileError) as exc:
            issues.append(LintIssue(arquivo=str(file), erro=str(exc)))
    return {
        "ok": len(issues) == 0,
        "total_arquivos": len(discover_trm_files(target)),
        "erros": [issue.__dict__ for issue in issues],
    }


def _normalize_source(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out_lines: list[str] = []
    for line in lines:
        line = line.replace("\t", "    ")
        out_lines.append(line.rstrip())
    normalized = "\n".join(out_lines).strip("\n") + "\n"
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized


def format_trm(target: str, write: bool = False) -> dict[str, Any]:
    changed: list[str] = []
    for file in discover_trm_files(target):
        original = file.read_text(encoding="utf-8")
        formatted = _normalize_source(original)
        if formatted != original:
            changed.append(str(file))
            if write:
                file.write_text(formatted, encoding="utf-8")
    return {"ok": True, "alterados": changed, "total_alterados": len(changed), "modo_escrita": write}


def coverage_trm(target: str) -> dict[str, Any]:
    all_files = discover_trm_files(target)
    test_files = [p for p in all_files if p.name.startswith("test_")]
    source_files = [p for p in all_files if not p.name.startswith("test_")]
    if not source_files:
        return {"ok": True, "cobertura_percentual": 100.0, "cobertos": [], "nao_cobertos": []}

    covered: set[Path] = set()
    pattern = re.compile(r'^\s*importe\s+(?:"([^"]+)"|([A-Za-z_][A-Za-z0-9_]*))', re.MULTILINE)
    for tf in test_files:
        covered.add(tf)
        content = tf.read_text(encoding="utf-8")
        for m in pattern.finditer(content):
            module_ref = m.group(1) or m.group(2)
            if not module_ref:
                continue
            if module_ref.endswith(".trm"):
                candidate = (tf.parent / module_ref).resolve()
            else:
                candidate = (tf.parent / f"{module_ref}.trm").resolve()
            if candidate.exists():
                covered.add(candidate)

    source_set = set(p.resolve() for p in source_files)
    covered_source = sorted([str(p) for p in source_set.intersection(covered)])
    uncovered_source = sorted([str(p) for p in source_set.difference(covered)])
    percentual = (len(covered_source) / len(source_files)) * 100.0
    return {
        "ok": True,
        "cobertura_percentual": round(percentual, 2),
        "cobertos": covered_source,
        "nao_cobertos": uncovered_source,
    }


def gerar_template_backend(destino: str, forcar: bool = False) -> dict[str, Any]:
    root = Path(destino)
    if root.exists() and any(root.iterdir()) and not forcar:
        raise RuntimeError("Diretório de template não está vazio. Use --forcar para sobrescrever.")

    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "migrations").mkdir(parents=True, exist_ok=True)
    (root / "seeds").mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)

    (root / "README.md").write_text(
        "# Projeto backend Trama\n\n"
        "## Executar\n\n"
        "```bash\n"
        "trama executar src/app.trm\n"
        "```\n",
        encoding="utf-8",
    )
    (root / "config" / ".env.exemplo").write_text(
        "TRAMA_APP_NOME=backend-trama\nTRAMA_PORTA=8080\nTRAMA_DB_DSN=postgresql://usuario:senha@localhost:5432/app\n",
        encoding="utf-8",
    )
    (root / "src" / "app.trm").write_text(
        "assíncrona função principal()\n"
        "    app = web_criar_app()\n"
        "    web_adicionar_rota_json(app, \"GET\", \"/health\", {\"ok\": verdadeiro}, 200)\n"
        "    servidor = aguarde web_iniciar(app, \"127.0.0.1\", 8080)\n"
        "    exibir(\"servidor em\", servidor[\"base_url\"])\n"
        "fim\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_smoke.trm").write_text(
        "função principal()\n    exibir(\"ok\")\nfim\n",
        encoding="utf-8",
    )
    (root / "migrations" / "001_inicial.sql").write_text(
        "CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nome TEXT NOT NULL);\n",
        encoding="utf-8",
    )
    (root / "seeds" / "001_seed.sql").write_text(
        "INSERT INTO usuarios (nome) VALUES ('admin') ON CONFLICT DO NOTHING;\n",
        encoding="utf-8",
    )
    return {"ok": True, "destino": str(root.resolve())}


def _normalizar_identificador_canonicamente(nome: str) -> str:
    bruto = str(nome or "").strip().lower()
    sem_acento = "".join(ch for ch in unicodedata.normalize("NFD", bruto) if unicodedata.category(ch) != "Mn")
    sem_separador = re.sub(r"[^a-z0-9_]+", "_", sem_acento)
    sem_repeticao = re.sub(r"_+", "_", sem_separador).strip("_")
    if not sem_repeticao:
        return "modulo_exemplo"
    if sem_repeticao[0].isdigit():
        return f"m_{sem_repeticao}"
    return sem_repeticao


def gerar_template_servico(destino: str, forcar: bool = False) -> dict[str, Any]:
    root = Path(destino)
    if root.exists() and any(root.iterdir()) and not forcar:
        raise RuntimeError("Diretório de template não está vazio. Use --forcar para sobrescrever.")

    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "docs").mkdir(parents=True, exist_ok=True)

    (root / "README.md").write_text(
        "# Template de Serviço Trama\n\n"
        "Serviço HTTP canônico em pt-BR com observabilidade e contrato inicial.\n\n"
        "## Comandos\n\n"
        "```bash\n"
        "trama executar src/servico.trm\n"
        "trama testar tests\n"
        "trama openapi-gerar --contrato config/contrato_base.json --saida build/openapi.json\n"
        "```\n",
        encoding="utf-8",
    )
    (root / "config" / ".env.exemplo").write_text(
        "TRAMA_AMBIENTE=dev\nTRAMA_PORTA=8080\nTRAMA_HOST=127.0.0.1\n",
        encoding="utf-8",
    )
    (root / "config" / "contrato_base.json").write_text(
        "{\n"
        "  \"openapi\": \"3.0.3\",\n"
        "  \"info\": {\"title\": \"Servico Trama\", \"version\": \"1.0.0\"},\n"
        "  \"paths\": {\n"
        "    \"/saude\": {\n"
        "      \"get\": {\n"
        "        \"operationId\": \"get_saude\",\n"
        "        \"responses\": {\"200\": {\"description\": \"OK\"}}\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    (root / "src" / "servico.trm").write_text(
        "assíncrona função principal()\n"
        "    app = web_criar_app()\n"
        "    web_adicionar_rota_json(app, \"GET\", \"/saude\", {\"ok\": verdadeiro, \"servico\": \"trama\"}, 200)\n"
        "    web_ativar_observabilidade(app)\n"
        "    servidor = aguarde web_iniciar(app, \"127.0.0.1\", 8080)\n"
        "    exibir(\"servico_ativo\", servidor[\"base_url\"])\n"
        "fim\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_smoke_servico.trm").write_text(
        "função principal()\n"
        "    exibir(\"smoke_servico_ok\")\n"
        "fim\n",
        encoding="utf-8",
    )
    (root / "docs" / "OPERACAO.md").write_text(
        "# Operacao\n\n"
        "1. Inicie o servico com `trama executar src/servico.trm`.\n"
        "2. Valide saude em `/saude`, `/pronto`, `/vivo`.\n"
        "3. Verifique observabilidade em `/observabilidade`, `/alertas`, `/metricas`, `/otlp-json`.\n",
        encoding="utf-8",
    )
    return {"ok": True, "destino": str(root.resolve())}


def gerar_template_modulo(destino: str, nome_modulo: str = "modulo_exemplo", forcar: bool = False) -> dict[str, Any]:
    root = Path(destino)
    if root.exists() and any(root.iterdir()) and not forcar:
        raise RuntimeError("Diretório de template não está vazio. Use --forcar para sobrescrever.")

    nome = _normalizar_identificador_canonicamente(nome_modulo)
    arquivo_mod = f"{nome}.trm"
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)

    (root / "README.md").write_text(
        f"# Template de Modulo Trama: `{nome}`\n\n"
        "Estrutura minima para criar modulo reutilizavel em pt-BR.\n",
        encoding="utf-8",
    )
    (root / "src" / arquivo_mod).write_text(
        "função processar(entrada)\n"
        "    se entrada == nulo\n"
        "        retorne {\"ok\": falso, \"erro\": \"entrada_nula\"}\n"
        "    fim\n"
        "    retorne {\"ok\": verdadeiro, \"dados\": entrada}\n"
        "fim\n",
        encoding="utf-8",
    )
    (root / "tests" / f"test_{nome}.trm").write_text(
        f"importe \"../src/{arquivo_mod}\" como modulo\n"
        "função principal()\n"
        "    resultado = modulo[\"processar\"]({\"id\": 1})\n"
        "    exibir(resultado)\n"
        "fim\n",
        encoding="utf-8",
    )
    return {"ok": True, "destino": str(root.resolve()), "nome_modulo": nome, "arquivo_modulo": arquivo_mod}
