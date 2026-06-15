from __future__ import annotations

from pathlib import Path

from trama import tooling_runtime
from trama import web_runtime


def test_v229_sdk_gerado_a_partir_do_ir_formal(tmp_path: Path) -> None:
    app = web_runtime.WebApp()
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/api/v1/usuarios/:id",
            lambda req: {"status": 200, "json": {"ok": True}},
            schema={},
            options={
                "dto_requisicao": {
                    "corpo": {
                        "tipo": "objeto",
                        "campos": {
                            "nome": {"tipo": "texto", "obrigatorio": True},
                        },
                    }
                },
                "contrato_resposta": {
                    "versao_padrao": "v1",
                    "versoes": {"v1": {"campos_obrigatorios": ["ok"]}},
                },
            },
        )
    )
    ir = tooling_runtime.gerar_ir_web_app(app, titulo="API SDK", versao="2.1.29")
    sdk_py = tmp_path / "cliente.py"
    sdk_ts = tmp_path / "cliente.ts"

    out_py = tooling_runtime.gerar_sdk_cliente(ir, str(sdk_py), linguagem="python", nome_cliente="ClienteIrPy")
    out_ts = tooling_runtime.gerar_sdk_cliente(ir, str(sdk_ts), linguagem="typescript", nome_cliente="ClienteIrTs")

    assert out_py["ok"] is True
    assert out_py["ir_contrato"] == "trama_http_v1"
    assert "class ClienteIrPy" in sdk_py.read_text(encoding="utf-8")
    assert "def post_api_v1_usuarios_id" in sdk_py.read_text(encoding="utf-8")
    assert "def contrato" in sdk_py.read_text(encoding="utf-8")

    assert out_ts["ok"] is True
    assert "export class ClienteIrTs" in sdk_ts.read_text(encoding="utf-8")
    assert "async post_api_v1_usuarios_id" in sdk_ts.read_text(encoding="utf-8")
    assert "contrato()" in sdk_ts.read_text(encoding="utf-8")


def test_v230_breaking_changes_em_contrato() -> None:
    antes = {
        "ir_contrato": "trama_http_v1",
        "titulo": "API Contrato",
        "versao": "1.0.0",
        "rotas": [
            {
                "metodo": "POST",
                "caminho": "/usuarios",
                "operation_id": "post_usuarios",
                "dto_schemas": {
                    "corpo": {
                        "type": "object",
                        "required": ["nome"],
                        "properties": {
                            "nome": {"type": "string"},
                        },
                    }
                },
                "contrato_resposta": {
                    "versoes": {"v1": {"campos_obrigatorios": ["ok", "dados"]}},
                },
            }
        ],
        "componentes": {},
    }
    depois = {
        "ir_contrato": "trama_http_v1",
        "titulo": "API Contrato",
        "versao": "2.0.0",
        "rotas": [
            {
                "metodo": "POST",
                "caminho": "/usuarios",
                "operation_id": "post_usuarios",
                "dto_schemas": {
                    "corpo": {
                        "type": "object",
                        "required": ["nome", "email"],
                        "properties": {
                            "nome": {"type": "string"},
                            "email": {"type": "string"},
                        },
                    }
                },
                "contrato_resposta": {
                    "versoes": {"v1": {"campos_obrigatorios": ["ok"]}},
                },
            }
        ],
        "componentes": {},
    }

    diff = tooling_runtime.verificar_breaking_changes_contrato(antes, depois)
    tipos = {item["tipo"] for item in diff["breaking_changes"]}

    assert diff["ok"] is False
    assert "campo_requisicao_obrigatorio_adicionado" in tipos
    assert "campo_resposta_obrigatorio_removido" in tipos
