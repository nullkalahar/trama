from __future__ import annotations

import json
from pathlib import Path

from trama import tooling_runtime
from trama import web_runtime


def test_v206_gerar_openapi_de_web_app_e_salvar_sdk(tmp_path: Path) -> None:
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
            "v2": {"campos_obrigatorios": ["ok", "dados", "meta"]},
        },
    }
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/api/v1/usuarios/:id",
            lambda req: {"status": 201, "json": {"ok": True, "dados": req.get("corpo"), "meta": {"versao": "v2"}}},
            schema={},
            options={"dto_requisicao": dto, "contrato_resposta": contrato},
        )
    )

    spec = tooling_runtime.gerar_openapi_web_app(app, titulo="API Trama Teste", versao="2.0.6", servidor_base="http://127.0.0.1:8080")
    assert spec["openapi"] == "3.0.3"
    assert "/api/v1/usuarios/{id}" in spec["paths"]
    op = spec["paths"]["/api/v1/usuarios/{id}"]["post"]
    assert op["operationId"] == "post_api_v1_usuarios_id"
    assert op["requestBody"]["required"] is True
    assert "422" in op["responses"]

    openapi_arquivo = tmp_path / "openapi.json"
    out_openapi = tooling_runtime.salvar_openapi(spec, str(openapi_arquivo))
    assert out_openapi["ok"] is True
    assert openapi_arquivo.exists()
    _ = json.loads(openapi_arquivo.read_text(encoding="utf-8"))

    sdk_py = tmp_path / "cliente_api.py"
    out_sdk_py = tooling_runtime.gerar_sdk_cliente(spec, str(sdk_py), linguagem="python", nome_cliente="ClienteTeste")
    assert out_sdk_py["ok"] is True
    assert "class ClienteTeste" in sdk_py.read_text(encoding="utf-8")

    sdk_ts = tmp_path / "cliente_api.ts"
    out_sdk_ts = tooling_runtime.gerar_sdk_cliente(spec, str(sdk_ts), linguagem="typescript", nome_cliente="ClienteTesteTs")
    assert out_sdk_ts["ok"] is True
    assert "export class ClienteTesteTs" in sdk_ts.read_text(encoding="utf-8")


def test_v206_dashboards_e_runbooks_prontos() -> None:
    dashboards = tooling_runtime.dashboards_operacionais_prontos()
    runbooks = tooling_runtime.runbooks_incidentes_prontos()
    assert dashboards["ok"] is True
    assert runbooks["ok"] is True
    ids_dash = {item["id"] for item in dashboards["dashboards"]}
    codigos_runbooks = {item["codigo"] for item in runbooks["runbooks"]}
    assert {"api", "db", "tempo_real", "jobs"}.issubset(ids_dash)
    assert "runbook_api_erro_alto" in codigos_runbooks
