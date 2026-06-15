from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from trama.cli import main


def test_cli_v227_contrato_ir_e_v228_openapi_a_partir_de_ir(tmp_path: Path) -> None:
    contrato = tmp_path / "contrato_legacy.json"
    contrato.write_text(json.dumps({"paths": {"/api/v1/ping": {"get": {"operationId": "get_ping"}}}}, ensure_ascii=False), encoding="utf-8")
    ir_saida = tmp_path / "contrato_ir.json"
    openapi_saida = tmp_path / "openapi.json"

    out = StringIO()
    with redirect_stdout(out):
        code = main(
            [
                "contrato-ir-gerar",
                "--contrato",
                str(contrato),
                "--saida",
                str(ir_saida),
                "--titulo",
                "API CLI",
                "--versao",
                "2.1.27",
            ]
        )
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["ok"] is True
    ir = json.loads(ir_saida.read_text(encoding="utf-8"))
    assert ir["ir_contrato"] == "trama_http_v1"

    out = StringIO()
    with redirect_stdout(out):
        code = main(
            [
                "openapi-gerar",
                "--contrato",
                str(ir_saida),
                "--saida",
                str(openapi_saida),
            ]
        )
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["ok"] is True
    spec = json.loads(openapi_saida.read_text(encoding="utf-8"))
    assert spec["openapi"] == "3.0.3"
