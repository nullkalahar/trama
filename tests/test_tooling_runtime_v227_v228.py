from __future__ import annotations

import json
from pathlib import Path

from trama import tooling_runtime
from trama import web_runtime


def test_v227_ir_formal_de_web_app() -> None:
    app = web_runtime.WebApp()
    dto = {
        "corpo": {
            "tipo": "objeto",
            "campos": {
                "nome": {"tipo": "texto", "obrigatorio": True},
                "idade": {"tipo": "inteiro", "coagir": True},
            },
        }
    }
    contrato = {
        "versao_padrao": "v2",
        "versoes": {
            "v1": {"campos_obrigatorios": ["ok", "dados"]},
            "v2": {"campos_obrigatorios": ["ok", "dados", "meta"]},
        },
    }
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/api/v1/usuarios/:id",
            lambda req: {"status": 201, "json": {"ok": True, "dados": req.get("corpo"), "meta": {"v": "v2"}}},
            schema={},
            options={"dto_requisicao": dto, "contrato_resposta": contrato, "jwt_segredo": "segredo"},
        )
    )
    ir = tooling_runtime.gerar_ir_web_app(app, titulo="API IR", versao="2.1.27", servidor_base="http://127.0.0.1:8080")
    assert ir["ir_contrato"] == "trama_http_v1"
    assert ir["rotas"][0]["metodo"] == "POST"
    assert ir["rotas"][0]["dto_schemas"]["corpo"]["type"] == "object"
    assert ir["rotas"][0]["autenticacao"]["jwt_ativo"] is True
    assert ir["rotas"][0]["versionamento"]["versao_padrao"] == "v2"


def test_v228_openapi_consumindo_ir_formal(tmp_path: Path) -> None:
    ir = {
        "ir_contrato": "trama_http_v1",
        "titulo": "API IR CLI",
        "versao": "2.1.28",
        "servidores": [{"url": "http://127.0.0.1:9999"}],
        "rotas": [
            {
                "metodo": "GET",
                "caminho": "/api/v1/ping/{id}",
                "operation_id": "get_api_v1_ping_id",
                "resumo": "GET /api/v1/ping/{id}",
                "parametros_path": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "dto_schemas": {},
                "contrato_resposta": {
                    "versao_padrao": "v1",
                    "versoes": {"v1": {"campos_obrigatorios": ["ok", "dados", "meta"]}},
                },
            }
        ],
        "componentes": {"erro_padrao": {"type": "object"}},
    }
    spec = tooling_runtime.gerar_openapi_de_ir(ir)
    assert spec["openapi"] == "3.0.3"
    assert spec["paths"]["/api/v1/ping/{id}"]["get"]["operationId"] == "get_api_v1_ping_id"

    ir_path = tmp_path / "contrato_ir.json"
    out_ir = tooling_runtime.salvar_ir_contrato(ir, str(ir_path))
    assert out_ir["ok"] is True
    assert json.loads(ir_path.read_text(encoding="utf-8"))["ir_contrato"] == "trama_http_v1"
