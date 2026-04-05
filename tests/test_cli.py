from __future__ import annotations

import json
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
import os
from pathlib import Path
import threading

from trama.cli import main


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_cli_executar(tmp_path: Path) -> None:
    src = _write(
        tmp_path,
        "ok.trm",
        "função principal()\n    exibir(\"olá\")\nfim\n",
    )
    out = StringIO()
    with redirect_stdout(out):
        code = main(["executar", str(src)])
    assert code == 0
    assert "olá" in out.getvalue()


def test_cli_bytecode(tmp_path: Path) -> None:
    src = _write(tmp_path, "bc.trm", "função principal()\nretorne 1 + 2\nfim\n")
    out = StringIO()
    with redirect_stdout(out):
        code = main(["bytecode", str(src)])
    text = out.getvalue()
    assert code == 0
    assert "== ENTRY ==" in text
    assert "== FUNCTIONS ==" in text
    assert "func principal()" in text


def test_cli_compilar_gera_json(tmp_path: Path) -> None:
    src = _write(tmp_path, "c.trm", "função principal()\nretorne 10\nfim\n")
    out_file = tmp_path / "programa.tbc"
    code = main(["compilar", str(src), "-o", str(out_file)])
    assert code == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert "entry" in payload
    assert "functions" in payload
    assert any(fn["name"] == "principal" for fn in payload["functions"].values())


def test_cli_executar_tbc(tmp_path: Path) -> None:
    src = _write(tmp_path, "prog.trm", "função principal()\n    exibir(\"tbc\")\nfim\n")
    out_file = tmp_path / "prog.tbc"
    code = main(["compilar", str(src), "-o", str(out_file)])
    assert code == 0

    out = StringIO()
    with redirect_stdout(out):
        code = main(["executar-tbc", str(out_file)])
    assert code == 0
    assert "tbc" in out.getvalue()


def test_cli_erro_retorna_1(tmp_path: Path) -> None:
    src = _write(tmp_path, "erro.trm", "retorne 1\n")
    err = StringIO()
    with redirect_stderr(err):
        code = main(["executar", str(src)])
    assert code == 1
    assert "Erro:" in err.getvalue()


def test_cli_testar_e_lint(tmp_path: Path) -> None:
    test_file = _write(tmp_path, "test_ok.trm", "função principal()\n    exibir(\"ok\")\nfim\n")
    _ = test_file
    bad_file = _write(tmp_path, "bad.trm", "retorne 1\n")
    _ = bad_file

    out = StringIO()
    with redirect_stdout(out):
        code = main(["testar", str(tmp_path)])
    assert code == 0
    assert "Aprovados" in out.getvalue()

    out = StringIO()
    with redirect_stdout(out):
        code = main(["lint", str(tmp_path)])
    assert code == 1
    assert "Erros" in out.getvalue()


def test_cli_formatar_cobertura_template(tmp_path: Path) -> None:
    src = _write(tmp_path, "mod.trm", "função principal()\t\n    exibir(\"x\")    \nfim")
    _write(
        tmp_path,
        "test_mod.trm",
        "importe \"mod.trm\" como m\nfunção principal()\n    m[\"principal\"]()\nfim\n",
    )
    out = StringIO()
    with redirect_stdout(out):
        code = main(["formatar", str(src), "--aplicar"])
    assert code == 0
    assert "Alterados" in out.getvalue()

    out = StringIO()
    with redirect_stdout(out):
        code = main(["cobertura", str(tmp_path)])
    assert code == 0
    assert "Cobertura:" in out.getvalue()

    dst = tmp_path / "meu_backend"
    out = StringIO()
    with redirect_stdout(out):
        code = main(["template-backend", str(dst)])
    assert code == 0
    assert (dst / "src" / "app.trm").exists()


def test_cli_diagnostico_runtime_campos_canonicos_e_compat() -> None:
    out = StringIO()
    with redirect_stdout(out):
        code = main(["--diagnostico-runtime"])
    assert code == 0
    text = out.getvalue()
    assert "backend_runtime=" in text
    assert "backend_compilador=" in text
    assert "requer_python_host=" in text
    assert "runtime_backend=" in text
    assert "compilador_backend=" in text
    assert "python_host_required=" in text


def test_cli_template_servico_modulo_openapi_sdk_admin_ops(tmp_path: Path) -> None:
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        out = StringIO()
        with redirect_stdout(out):
            code = main(["template-servico", str(tmp_path / "serv"), "--json"])
        assert code == 0
        payload = json.loads(out.getvalue())
        assert payload["ok"] is True
        assert (tmp_path / "serv" / "src" / "servico.trm").exists()

        out = StringIO()
        with redirect_stdout(out):
            code = main(["template-modulo", str(tmp_path / "mod"), "--nome", "Módulo Ágil", "--json"])
        assert code == 0
        payload = json.loads(out.getvalue())
        assert payload["ok"] is True
        assert payload["nome_modulo"] == "modulo_agil"

        contrato = tmp_path / "contrato.json"
        contrato.write_text(
            json.dumps(
                {
                    "openapi": "3.0.3",
                    "info": {"title": "Api Teste", "version": "1.0.0"},
                    "paths": {"/saude": {"get": {"operationId": "get_saude", "responses": {"200": {"description": "OK"}}}}},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        out_openapi = tmp_path / "openapi.json"
        out = StringIO()
        with redirect_stdout(out):
            code = main(["openapi-gerar", "--contrato", str(contrato), "--saida", str(out_openapi)])
        assert code == 0
        assert out_openapi.exists()

        out_sdk = tmp_path / "sdk.py"
        out = StringIO()
        with redirect_stdout(out):
            code = main(
                [
                    "sdk-gerar",
                    "--openapi",
                    str(out_openapi),
                    "--saida",
                    str(out_sdk),
                    "--linguagem",
                    "python",
                ]
            )
        assert code == 0
        assert "class ClienteApiTrama" in out_sdk.read_text(encoding="utf-8")

        out = StringIO()
        with redirect_stdout(out):
            code = main(["admin-usuario-criar", "--id", "u1", "--nome", "Admin", "--papeis", "ops,root"])
        assert code == 0
        payload = json.loads(out.getvalue())
        assert payload["usuario"]["id"] == "u1"

        out = StringIO()
        with redirect_stdout(out):
            code = main(["admin-permissao-conceder", "--id", "u1", "--permissoes", "jobs:executar,usuarios:listar"])
        assert code == 0
        payload = json.loads(out.getvalue())
        assert "jobs:executar" in payload["usuario"]["permissoes"]

        out = StringIO()
        with redirect_stdout(out):
            code = main(["admin-usuario-listar", "--json"])
        assert code == 0
        payload = json.loads(out.getvalue())
        assert payload["total"] == 1

        out = StringIO()
        with redirect_stdout(out):
            code = main(["admin-jobs-listar", "--json"])
        assert code == 0
        payload = json.loads(out.getvalue())
        assert payload["ok"] is True

        out = StringIO()
        with redirect_stdout(out):
            code = main(["admin-manutencao-status", "--json"])
        assert code == 0
        payload = json.loads(out.getvalue())
        assert payload["estado"] == "operacional"

        out = StringIO()
        with redirect_stdout(out):
            code = main(["operacao-diagnostico", "--json"])
        assert code == 0
        payload = json.loads(out.getvalue())
        assert payload["ok"] is True
        assert "dashboards" in payload
    finally:
        os.chdir(cwd)


def test_cli_migracao_seed_diagnostico_smoke(tmp_path: Path) -> None:
    db_file = tmp_path / "cli_v206.db"
    up = tmp_path / "up.sql"
    down = tmp_path / "down.sql"
    seed = tmp_path / "seed.sql"
    up.write_text("CREATE TABLE IF NOT EXISTS itens (id INTEGER PRIMARY KEY, nome TEXT);\n", encoding="utf-8")
    down.write_text("DROP TABLE IF EXISTS itens;\n", encoding="utf-8")
    seed.write_text("INSERT INTO itens (id, nome) VALUES (1, 'x');\n", encoding="utf-8")
    dsn = f"sqlite:///{db_file}"

    out = StringIO()
    with redirect_stdout(out):
        code = main(
            [
                "migracao-aplicar-v2",
                "--dsn",
                dsn,
                "--versao",
                "206.001",
                "--nome",
                "init",
                "--up-arquivo",
                str(up),
                "--down-arquivo",
                str(down),
                "--ambiente",
                "teste",
            ]
        )
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["aplicada"] is True

    out = StringIO()
    with redirect_stdout(out):
        code = main(["migracao-trilha-listar", "--dsn", dsn, "--limite", "10", "--json"])
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["ok"] is True
    assert len(payload["trilha"]) >= 1

    out = StringIO()
    with redirect_stdout(out):
        code = main(["seed-aplicar-ambiente", "--dsn", dsn, "--ambiente", "teste", "--nome", "s1", "--sql-arquivo", str(seed)])
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["ok"] is True

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = b"{\"ok\":true}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # noqa: A003
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        out = StringIO()
        with redirect_stdout(out):
            code = main(["operacao-smoke-check", "--base-url", f"http://127.0.0.1:{port}", "--json"])
        assert code == 0
        payload = json.loads(out.getvalue())
        assert payload["ok"] is True
        assert any(item["caminho"] == "/saude" for item in payload["resultados"])
    finally:
        server.shutdown()
        server.server_close()
