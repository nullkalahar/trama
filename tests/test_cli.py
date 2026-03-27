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


def test_cli_erro_retorna_1(tmp_path: Path) -> None:
    src = _write(tmp_path, "erro.trm", "retorne 1\n")
    err = StringIO()
    with redirect_stderr(err):
        code = main(["executar", str(src)])
    assert code == 1
    assert "Erro:" in err.getvalue()
