from __future__ import annotations

import json
from urllib import error, request

from trama import web_runtime


def _post_json(url: str, payload: dict[str, object], headers: dict[str, str] | None = None) -> tuple[int, dict[str, object], dict[str, str]]:
    req = request.Request(
        url=url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **dict(headers or {})},
    )
    with request.urlopen(req, timeout=5.0) as resp:
        return int(resp.status), json.loads(resp.read().decode("utf-8")), dict(resp.headers.items())


def _get_json(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object], dict[str, str]]:
    req = request.Request(url=url, method="GET", headers=dict(headers or {}))
    with request.urlopen(req, timeout=5.0) as resp:
        return int(resp.status), json.loads(resp.read().decode("utf-8")), dict(resp.headers.items())


def _open_error(req: request.Request) -> tuple[int, dict[str, object], dict[str, str]]:
    try:
        with request.urlopen(req, timeout=5.0):
            raise AssertionError("esperava erro HTTP")
    except error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))
        return int(exc.code), payload, dict(exc.headers.items())


def test_v202_dto_coercao_sanitizacao_e_remocao_campos() -> None:
    app = web_runtime.WebApp()

    def criar(req):
        return {"status": 201, "json": {"ok": True, "dados": req["corpo"]}}

    dto = {
        "corpo": {
            "tipo": "objeto",
            "permitir_campos_extras": False,
            "campos": {
                "nome": {"tipo": "texto", "obrigatorio": True, "sanitizar": {"trim": True}},
                "idade": {"tipo": "inteiro", "coagir": True, "minimo": 0},
                "ativo": {"tipo": "logico", "coagir": True, "padrao": True},
                "tags": {"tipo": "lista", "itens": {"tipo": "texto", "sanitizar": {"trim": True}}},
            },
        }
    }
    options = {"dto_requisicao": dto, "contrato_entrada": {"campos_permitidos": {"corpo": ["nome", "idade", "ativo", "tags"]}}}
    app.routes.append(web_runtime.WebRoute.dynamic("POST", "/api/v1/usuarios", criar, schema={}, options=options))

    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        status, payload, _ = _post_json(
            base + "/api/v1/usuarios",
            {"nome": "  Ana  ", "idade": "33", "ativo": "true", "tags": [" x ", "y"], "extra": "descartar"},
        )
        assert status == 201
        assert payload["ok"] is True
        assert payload["dados"] == {"nome": "Ana", "idade": 33, "ativo": True, "tags": ["x", "y"]}
    finally:
        rt.stop()


def test_v202_dto_erro_padronizado_por_campo() -> None:
    app = web_runtime.WebApp()
    dto = {
        "corpo": {
            "tipo": "objeto",
            "campos": {
                "nome": {"tipo": "texto", "obrigatorio": True, "sanitizar": {"trim": True}, "tamanho_min": 2},
                "idade": {"tipo": "inteiro", "coagir": True, "minimo": 0},
            },
        }
    }
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/api/v1/usuarios",
            lambda req: {"status": 201, "json": {"ok": True, "dados": req["corpo"]}},
            schema={},
            options={"dto_requisicao": dto},
        )
    )

    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        req = request.Request(
            url=base + "/api/v1/usuarios",
            method="POST",
            data=json.dumps({"nome": "a", "idade": "x"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        status, payload, _ = _open_error(req)
        assert status == 422
        assert payload["erro"]["codigo"] == "VALIDACAO_FALHOU"
        campos = payload["erro"]["detalhes"]["campos"]
        assert isinstance(campos, list)
        assert all(set(["codigo", "campo", "mensagem", "detalhes"]).issubset(item.keys()) for item in campos)
        codigos = {item["codigo"] for item in campos}
        assert "TIPO_INVALIDO" in codigos
        assert "TAMANHO_MINIMO_INVALIDO" in codigos
    finally:
        rt.stop()


def test_v202_contrato_versionado_retrocompativel() -> None:
    app = web_runtime.WebApp()

    def ok(req):
        return {
            "status": 200,
            "json": {"ok": True, "dados": {"id": 1}, "erro": None, "meta": {"v": 2}, "links": {"self": "/api/v1/usuarios/1"}},
        }

    contrato = {
        "versao_padrao": "v2",
        "versoes": {
            "v1": {"envelope": True, "campos_obrigatorios": ["ok", "dados", "erro", "meta"]},
            "v2": {"envelope": True, "campos_obrigatorios": ["ok", "dados", "erro", "meta", "links"]},
        },
        "retrocompativel": {"legacy": "v1"},
    }
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "GET",
            "/api/v1/usuarios/1",
            ok,
            schema={},
            options={"contrato_resposta": contrato},
        )
    )

    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        status_ok, payload_ok, headers_ok = _get_json(base + "/api/v1/usuarios/1", headers={"X-Contrato-Versao": "legacy"})
        assert status_ok == 200
        assert payload_ok["ok"] is True
        assert headers_ok.get("X-Contrato-Versao-Aplicada") == "v1"

        req_bad = request.Request(url=base + "/api/v1/usuarios/1", method="GET", headers={"X-Contrato-Versao": "v999"})
        status_bad, payload_bad, headers_bad = _open_error(req_bad)
        assert status_bad == 400
        assert payload_bad["erro"]["codigo"] == "CONTRATO_VERSAO_INVALIDA"
        assert headers_bad.get("X-Contrato-Versao-Solicitada") == "v999"
    finally:
        rt.stop()
