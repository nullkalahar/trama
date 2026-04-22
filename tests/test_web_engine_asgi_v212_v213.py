from __future__ import annotations

import json
import sys
from urllib import error, request

from trama import web_runtime


def _http_json(method: str, url: str, payload: dict[str, object] | None = None) -> tuple[int, dict[str, object]]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, method=method.upper(), data=data, headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=5.0) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), (json.loads(body) if body else {})
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), (json.loads(body) if body else {})


def test_v212_asgi_fallback_automatico_para_legada(monkeypatch) -> None:
    app = web_runtime.WebApp()
    app.engine_http_preferida = "asgi"
    app.engine_http_fallback_automatico = True
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "GET",
            "/ping",
            lambda req: {"status": 200, "json": {"ok": True, "motor": req.get("caminho")}},
            schema={},
            options={},
        )
    )
    monkeypatch.setitem(sys.modules, "uvicorn", object())

    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _m: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        status, payload = _http_json("GET", base + "/ping")
        assert status == 200
        assert payload["ok"] is True
        assert rt._engine_ativa_nome == "legada"
    finally:
        rt.stop()


def test_v213_saude_readiness_liveness_e_limite_operacional() -> None:
    app = web_runtime.WebApp()
    app.limites_operacionais_por_engine["legada"]["max_body_bytes"] = 2048
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/eco",
            lambda req: {"status": 200, "json": {"ok": True, "tam": len(dict(req.get("corpo", {})).get("blob", ""))}},
            schema={},
            options={},
        )
    )
    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _m: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        s_h, p_h = _http_json("GET", base + "/saude")
        s_r, p_r = _http_json("GET", base + "/pronto")
        s_l, p_l = _http_json("GET", base + "/vivo")
        assert (s_h, s_r, s_l) == (200, 200, 200)
        assert p_h["status"] == "up"
        assert p_r["status"] == "ready"
        assert p_l["status"] == "alive"

        # payload maior que limite operacional da engine legada
        s_413, p_413 = _http_json("POST", base + "/eco", {"blob": "x" * 4096})
        assert s_413 == 413
        assert p_413["erro"]["codigo"] == "PAYLOAD_GRANDE"
        assert int(p_413["erro"]["detalhes"]["limite_bytes"]) == 2048

        rt._estado_drenando = True
        s_r2, p_r2 = _http_json("GET", base + "/pronto")
        s_h2, p_h2 = _http_json("GET", base + "/saude")
        assert s_r2 == 503
        assert p_r2["status"] == "draining"
        assert s_h2 == 503
        assert p_h2["status"] == "degradado"
    finally:
        rt.stop()
