from __future__ import annotations

import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

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
