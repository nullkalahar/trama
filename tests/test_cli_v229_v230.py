from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path

from trama.cli import main


def test_cli_v229_sdk_por_ir_e_v230_breaking(tmp_path: Path) -> None:
    ir = tmp_path / "contrato_ir.json"
    ir.write_text(
        json.dumps(
            {
                "ir_contrato": "trama_http_v1",
                "titulo": "API CLI",
                "versao": "2.1.29",
                "rotas": [
                    {
                        "metodo": "GET",
                        "caminho": "/saude",
                        "operation_id": "get_saude",
                        "dto_schemas": {},
                        "contrato_resposta": {"versoes": {"v1": {"campos_obrigatorios": ["ok"]}}},
                    }
                ],
                "componentes": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    sdk = tmp_path / "cliente.py"
    out = StringIO()
    with redirect_stdout(out):
        code = main(["sdk-gerar", "--contrato-ir", str(ir), "--saida", str(sdk), "--linguagem", "python", "--cliente", "ClienteCli"])
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["ok"] is True
    assert "class ClienteCli" in sdk.read_text(encoding="utf-8")

    antes = tmp_path / "antes.json"
    depois = tmp_path / "depois.json"
    antes.write_text(ir.read_text(encoding="utf-8"), encoding="utf-8")
    depois.write_text(
        json.dumps(
            {
                "ir_contrato": "trama_http_v1",
                "titulo": "API CLI",
                "versao": "2.1.30",
                "rotas": [],
                "componentes": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    relatorio = tmp_path / "breaking.json"
    out = StringIO()
    with redirect_stdout(out):
        code = main(["contrato-breaking-verificar", "--antes", str(antes), "--depois", str(depois), "--saida", str(relatorio)])
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["ok"] is False
    assert relatorio.exists()
    assert payload["breaking_changes"][0]["tipo"] == "rota_removida"
