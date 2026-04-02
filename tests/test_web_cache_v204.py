from __future__ import annotations

import json
from urllib import request

from trama import cache_runtime
from trama import web_runtime


def _get_json(url: str) -> tuple[int, dict[str, object]]:
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=5.0) as resp:
        return int(resp.status), json.loads(resp.read().decode("utf-8"))


def test_v204_cache_resposta_http_com_invalidez() -> None:
    cache_runtime.cache_limpar()
    contador = {"n": 0}

    def handler(req):
        contador["n"] += 1
        return {"status": 200, "json": {"ok": True, "dados": {"contador": contador["n"]}}}

    app = web_runtime.WebApp()
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "GET",
            "/api/v1/cacheado",
            handler,
            schema={},
            options={"cache_resposta": {"namespace": "http_teste", "ttl_segundos": 1.0}},
        )
    )

    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        s1, p1 = _get_json(base + "/api/v1/cacheado")
        s2, p2 = _get_json(base + "/api/v1/cacheado")
        assert s1 == 200 and s2 == 200
        assert p1["dados"]["contador"] == 1
        assert p2["dados"]["contador"] == 1

        cache_runtime.cache_distribuido_invalidar_chave("GET:/api/v1/cacheado?", namespace="http_teste")
        s3, p3 = _get_json(base + "/api/v1/cacheado")
        assert s3 == 200
        assert p3["dados"]["contador"] == 2
    finally:
        rt.stop()

