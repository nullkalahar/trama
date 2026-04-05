from __future__ import annotations

import json
from urllib import request

from trama import tooling_runtime
from trama import web_runtime


def _http_json(url: str) -> tuple[int, dict[str, object], dict[str, str]]:
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=5.0) as resp:
        txt = resp.read().decode("utf-8", errors="replace")
        return int(resp.getcode() or 0), (json.loads(txt) if txt else {}), dict(resp.headers.items())


def _http_text(url: str) -> tuple[int, str, dict[str, str]]:
    req = request.Request(url=url, method="GET")
    with request.urlopen(req, timeout=5.0) as resp:
        txt = resp.read().decode("utf-8", errors="replace")
        return int(resp.getcode() or 0), txt, dict(resp.headers.items())


def test_v207_endpoints_observabilidade_prometheus_otel_e_smoke() -> None:
    app = web_runtime.WebApp()
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "GET",
            "/api/v1/ping",
            lambda req: {"status": 200, "json": {"ok": True, "id_requisicao": req.get("id_requisicao")}},
            schema={},
            options={},
        )
    )
    app.observabilidade_ativa = True

    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _msg: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        status_ping, payload_ping, _ = _http_json(base + "/api/v1/ping")
        assert status_ping == 200
        assert payload_ping["ok"] is True

        status_obs, payload_obs, _ = _http_json(base + "/observabilidade")
        assert status_obs == 200
        assert "metricas" in payload_obs
        assert "tracos" in payload_obs
        assert "alertas" in payload_obs

        status_alertas, payload_alertas, _ = _http_json(base + "/alertas")
        assert status_alertas == 200
        assert "alertas" in payload_alertas
        assert "estado" in payload_alertas["alertas"]

        status_metricas, payload_metricas, headers_metricas = _http_text(base + "/metricas")
        assert status_metricas == 200
        assert headers_metricas.get("Content-Type", "").startswith("text/plain")
        assert "trama_runtime_info" in payload_metricas

        status_otlp, payload_otlp, _ = _http_json(base + "/otlp-json")
        assert status_otlp == 200
        assert payload_otlp["ok"] is True
        assert set(["resource", "metrics", "spans", "events", "correlacao"]).issubset(payload_otlp["otlp"].keys())

        smoke = tooling_runtime.smoke_checks_http(base, timeout_segundos=2.0)
        assert smoke["ok"] is True
        caminhos = {x["caminho"] for x in smoke["resultados"]}
        assert {"/saude", "/pronto", "/vivo", "/observabilidade", "/alertas"}.issubset(caminhos)
    finally:
        rt.stop()
