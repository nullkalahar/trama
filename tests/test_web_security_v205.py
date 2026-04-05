from __future__ import annotations

import json
import time
from urllib import error, request

from trama import security_runtime
from trama import web_runtime


def _invoke(fn: object, args: list[object]) -> object:
    assert callable(fn)
    return fn(*args)


def _start(app: web_runtime.WebApp) -> web_runtime.WebRuntime:
    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _msg: None, invoke_callable_sync=_invoke)
    rt.start()
    return rt


def _http(method: str, url: str, body: dict[str, object] | None = None, headers: dict[str, str] | None = None) -> tuple[int, dict[str, object], dict[str, str]]:
    hdr = {"Content-Type": "application/json; charset=utf-8"}
    hdr.update(dict(headers or {}))
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, method=method.upper(), data=data, headers=hdr)
    try:
        with request.urlopen(req, timeout=5.0) as resp:
            txt = resp.read().decode("utf-8", errors="replace")
            payload = json.loads(txt) if txt else {}
            return int(resp.getcode() or 0), payload, dict(resp.headers.items())
    except error.HTTPError as exc:
        txt = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(txt) if txt else {}
        return int(exc.code), payload, dict(exc.headers.items())


def test_v205_http_hardening_cors_estrito_producao() -> None:
    app = web_runtime.WebApp()
    app.ambiente = "producao"
    app.cors_origens_por_ambiente["producao"] = ["https://app.trama.local"]
    app.routes.append(web_runtime.WebRoute.dynamic("GET", "/ping", lambda req: {"status": 200, "json": {"ok": True}}, {}, {}))

    rt = _start(app)
    try:
        base = f"http://127.0.0.1:{rt.port}"
        st_block, payload_block, _ = _http("GET", base + "/ping", headers={"Origin": "https://evil.local"})
        assert st_block == 403
        assert payload_block["erro"]["codigo"] == "CORS_ORIGEM_NAO_PERMITIDA"

        st_ok, payload_ok, h_ok = _http("GET", base + "/ping", headers={"Origin": "https://app.trama.local"})
        assert st_ok == 200
        assert payload_ok["ok"] is True
        assert h_ok.get("Strict-Transport-Security")
        assert h_ok.get("X-Content-Type-Options") == "nosniff"
        assert h_ok.get("X-Frame-Options") == "DENY"
        assert h_ok.get("Referrer-Policy") == "no-referrer"
        assert "Content-Security-Policy" in h_ok
    finally:
        rt.stop()


def test_v205_auth_revogacao_imediata_http_e_auditoria_admin() -> None:
    segredo = "seg-v205-http"
    app = web_runtime.WebApp()

    def admin(req: dict[str, object]) -> dict[str, object]:
        return {"status": 200, "json": {"ok": True, "id_usuario": req.get("id_usuario")}}

    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "GET",
            "/admin/sensivel",
            admin,
            schema={},
            options={
                "jwt_segredo": segredo,
                "jwt_validar_revogacao": True,
                "auditoria_admin": {"acao": "admin_sensivel", "alvo": "recurso_x"},
            },
        )
    )

    rt = _start(app)
    try:
        base = f"http://127.0.0.1:{rt.port}"
        token = security_runtime.jwt_criar({"sub": "u-1", "id_usuario": "u-1"}, segredo, exp_segundos=60)

        st1, payload1, _ = _http("GET", base + "/admin/sensivel", headers={"Authorization": f"Bearer {token}"})
        assert st1 == 200
        assert payload1["id_usuario"] == "u-1"

        security_runtime.token_bloquear(token, ttl_segundos=60, motivo="logout")
        st2, payload2, _ = _http("GET", base + "/admin/sensivel", headers={"Authorization": f"Bearer {token}"})
        assert st2 == 401
        assert payload2["erro"]["codigo"] == "TOKEN_REVOGADO"
        assert set(["codigo", "mensagem", "detalhes"]).issubset(payload2["erro"].keys())

        logs = security_runtime.auditoria_seguranca_listar(limite=20, acao="admin_sensivel")
        assert len(logs) >= 2
        assert {"sucesso", "negado"}.issubset({str(x["resultado"]) for x in logs[:5]})
    finally:
        rt.stop()


def test_v205_rate_limit_distribuido_rota_ip_usuario_multino_e_fallback() -> None:
    segredo = "seg-v205-rl"
    grupo = f"g_v205_http_rl_{int(time.time() * 1000)}"

    def mk_app(instancia: str, backend: str = "memoria", redis_url: str | None = None) -> web_runtime.WebApp:
        app = web_runtime.WebApp()
        app.routes.append(
            web_runtime.WebRoute.dynamic(
                "GET",
                "/protegido",
                lambda req: {"status": 200, "json": {"ok": True, "u": req.get("id_usuario")}},
                schema={},
                options={"jwt_segredo": segredo},
            )
        )
        app.rate_limits_distribuidos.append(
            web_runtime.RateLimitDistribuidoPolicy(
                method="GET",
                path="/protegido",
                max_requisicoes=3,
                janela_segundos=30,
                chaves=["rota", "ip", "usuario"],
                grupo=grupo,
                id_instancia=instancia,
                backend=backend,
                redis_url=redis_url,
                chave_prefixo="trama:test:v205:rl",
            )
        )
        return app

    rt_a = _start(mk_app("a"))
    rt_b = _start(mk_app("b"))
    try:
        token = security_runtime.jwt_criar({"sub": "u_rl", "id_usuario": "u_rl"}, segredo, exp_segundos=120)
        headers = {"Authorization": f"Bearer {token}"}
        base_a = f"http://127.0.0.1:{rt_a.port}"
        base_b = f"http://127.0.0.1:{rt_b.port}"

        s1, _, _ = _http("GET", base_a + "/protegido", headers=headers)
        s2, _, _ = _http("GET", base_b + "/protegido", headers=headers)
        s3, _, _ = _http("GET", base_a + "/protegido", headers=headers)
        s4, p4, _ = _http("GET", base_b + "/protegido", headers=headers)

        assert [s1, s2, s3] == [200, 200, 200]
        assert s4 == 429
        assert p4["erro"]["codigo"] == "RATE_LIMIT_EXCEDIDO"
        assert set(["codigo", "mensagem", "detalhes"]).issubset(p4["erro"].keys())
        assert p4["erro"]["detalhes"]["escopo"] in {"rota", "ip", "usuario"}
    finally:
        rt_a.stop()
        rt_b.stop()

    # backend indisponivel: deve degradar sem bypass inseguro (continua limitando)
    grupo_fb = f"g_v205_http_rl_fb_{int(time.time() * 1000)}"
    app_fb = mk_app("fb", backend="redis", redis_url="redis://127.0.0.1:63999/0")
    app_fb.rate_limits_distribuidos[0].grupo = grupo_fb
    rt_fb = _start(app_fb)
    try:
        token = security_runtime.jwt_criar({"sub": "u_fb", "id_usuario": "u_fb"}, segredo, exp_segundos=120)
        headers = {"Authorization": f"Bearer {token}"}
        base = f"http://127.0.0.1:{rt_fb.port}"
        s1, _, _ = _http("GET", base + "/protegido", headers=headers)
        s2, _, _ = _http("GET", base + "/protegido", headers=headers)
        s3, _, _ = _http("GET", base + "/protegido", headers=headers)
        s4, p4, _ = _http("GET", base + "/protegido", headers=headers)
        assert [s1, s2, s3] == [200, 200, 200]
        assert s4 == 429
        assert p4["erro"]["detalhes"]["degradado"] is True
    finally:
        rt_fb.stop()


def test_v205_realtime_rejeita_token_revogado_no_fallback() -> None:
    app = web_runtime.WebApp()
    segredo = "seg-v205-ws"
    app.tempo_real.registrar_rota("/ws/seg", lambda req: {"aceitar": True}, {"jwt_segredo": segredo, "jwt_validar_revogacao": True})
    app.tempo_real.ativar_fallback("/tempo-real/fallback", 1.0)

    rt = _start(app)
    try:
        token = security_runtime.jwt_criar({"sub": "u_ws", "id_usuario": "u_ws"}, segredo, exp_segundos=120)
        security_runtime.token_bloquear(token, ttl_segundos=60, motivo="logout")
        base = f"http://127.0.0.1:{rt.port}/tempo-real/fallback"
        status, payload, _ = _http(
            "POST",
            base + "/conectar",
            body={"canal": "/ws/seg"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status == 401
        assert payload["erro"]["codigo"] == "TOKEN_REVOGADO"
    finally:
        rt.stop()
