from __future__ import annotations

import json
from urllib import error, request

from trama import web_runtime
from trama.web_engine import EngineHttpServerLegado


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


def _criar_runtime(modo_engine: str) -> web_runtime.WebRuntime:
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
            },
        }
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
            "POST",
            "/api/v1/usuarios",
            criar,
            schema={},
            options={"dto_requisicao": dto},
        )
    )
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "GET",
            "/api/v1/usuarios/1",
            lambda req: {
                "status": 200,
                "json": {"ok": True, "dados": {"id": 1}, "erro": None, "meta": {"v": 2}, "links": {"self": "/api/v1/usuarios/1"}},
            },
            schema={},
            options={"contrato_resposta": contrato},
        )
    )
    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _: None, invoke_callable_sync=lambda fn, args: fn(*args))
    if modo_engine == "legada_explicita":
        rt.engine_http = EngineHttpServerLegado(
            iniciar=rt._start_legacy_httpserver,
            parar=rt._stop_legacy_httpserver,
        )
    rt.start()
    return rt


def _executar_cenario(modo_engine: str) -> dict[str, object]:
    rt = _criar_runtime(modo_engine)
    try:
        base = f"http://127.0.0.1:{rt.port}"
        status_post, payload_post, headers_post = _post_json(base + "/api/v1/usuarios", {"nome": " Ana ", "idade": "33"})
        req_bad = request.Request(
            url=base + "/api/v1/usuarios",
            method="POST",
            data=json.dumps({"nome": "a", "idade": "x"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        status_bad, payload_bad, headers_bad = _open_error(req_bad)
        status_legacy, payload_legacy, headers_legacy = _get_json(
            base + "/api/v1/usuarios/1",
            headers={"X-Contrato-Versao": "legacy"},
        )
        return {
            "post": {"status": status_post, "payload": payload_post, "tipo": headers_post.get("Content-Type")},
            "erro": {
                "status": status_bad,
                "codigo": dict(payload_bad.get("erro") or {}).get("codigo"),
                "tipo": headers_bad.get("Content-Type"),
            },
            "legacy": {
                "status": status_legacy,
                "payload": payload_legacy,
                "versao": headers_legacy.get("X-Contrato-Versao-Aplicada"),
            },
        }
    finally:
        rt.stop()


def test_v216_paridade_engine_http_envelope_headers_e_erros() -> None:
    out_padrao = _executar_cenario("padrao")
    out_legada = _executar_cenario("legada_explicita")

    assert out_padrao == out_legada
    assert out_padrao["post"]["status"] == 201
    assert out_padrao["erro"]["status"] == 422
    assert out_padrao["erro"]["codigo"] == "VALIDACAO_FALHOU"
    assert out_padrao["legacy"]["versao"] == "v1"
