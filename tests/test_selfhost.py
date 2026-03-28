from __future__ import annotations

import json
from pathlib import Path

from trama.cli import main
from trama.vm import run_source


def test_builtin_trama_compilar_fonte_retorna_bytecode_dict() -> None:
    fonte_trama = """
função principal()
    retorne trama_compilar_fonte("função principal()\\n    retorne 7\\nfim\\n")
fim
"""
    resultado = run_source(fonte_trama)
    assert isinstance(resultado, dict)
    assert "entry" in resultado
    assert "functions" in resultado


def test_cli_autocompilar_e_paridade(tmp_path: Path) -> None:
    src = tmp_path / "prog.trm"
    src.write_text("função principal()\n    retorne 1 + 2\nfim\n", encoding="utf-8")

    out_file = tmp_path / "prog.tbc"
    code = main(["autocompilar", str(src), "-o", str(out_file)])
    assert code == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert "entry" in payload

    code = main(["paridade-selfhost", str(src)])
    assert code == 0


def test_cli_compilar_usa_pipeline_selfhost(tmp_path: Path) -> None:
    src = tmp_path / "compilar.trm"
    src.write_text("função principal()\n    retorne 42\nfim\n", encoding="utf-8")

    out_file = tmp_path / "compilar.tbc"
    code = main(["compilar", str(src), "-o", str(out_file)])
    assert code == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert "entry" in payload


def test_cli_semente_compilar(tmp_path: Path) -> None:
    src = tmp_path / "semente.trm"
    src.write_text("função principal()\n    retorne 9\nfim\n", encoding="utf-8")
    out_file = tmp_path / "semente.tbc"
    code = main(["semente-compilar", str(src), "-o", str(out_file)])
    assert code == 0
    payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert "entry" in payload
