from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from trama.cli import main


def test_cli_v208_testes_avancados_gera_relatorios(tmp_path: Path) -> None:
    json_out = tmp_path / "relatorio_v208.json"
    md_out = tmp_path / "relatorio_v208.md"
    out = StringIO()
    with redirect_stdout(out):
        code = main(
            [
                "testes-avancados-v208",
                "--perfil",
                "rapido",
                "--sem-postgres",
                "--sem-redis",
                "--saida-json",
                str(json_out),
                "--saida-md",
                str(md_out),
                "--json",
            ]
        )
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["ok"] is True
    assert Path(str(payload["arquivo_json"])).exists()
    assert Path(str(payload["arquivo_md"])).exists()
