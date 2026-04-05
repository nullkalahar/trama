from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from urllib import request
from urllib.error import HTTPError

import pytest

from trama import web_runtime


def _invoke(fn: object, args: list[object]) -> object:
    assert callable(fn)
    return fn(*args)


def _start_runtime(app: web_runtime.WebApp) -> web_runtime.WebRuntime:
    rt = web_runtime.WebRuntime(
        app=app,
        host="127.0.0.1",
        port=0,
        out=lambda _msg: None,
        invoke_callable_sync=_invoke,
    )
    rt.start()
    return rt


def _http_json(method: str, url: str, body: dict[str, object] | None = None) -> tuple[int, dict[str, object]]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(url=url, method=method.upper(), data=data, headers=headers)
    try:
        with request.urlopen(req, timeout=3.0) as resp:
            txt = resp.read().decode("utf-8", errors="replace")
            return int(resp.getcode() or 0), json.loads(txt)
    except HTTPError as exc:
        txt = exc.read().decode("utf-8", errors="replace")
        return int(exc.code), json.loads(txt)


def _hub_distribuido(grupo: str, instancia: str, auto: bool = False) -> web_runtime.TempoRealHub:
    hub = web_runtime.TempoRealHub()
    hub.registrar_rota("/ws/dist", lambda req: {"aceitar": True}, {})
    cfg = hub.configurar_distribuicao(
        ativar=True,
        grupo=grupo,
        id_instancia=instancia,
        auto_sincronizar=auto,
        backplane="memoria",
    )
    assert cfg["ok"] is True
    return hub


def test_v203_multino_presenca_salas_sincronizadas() -> None:
    a = _hub_distribuido("g_v203_ps", "a")
    b = _hub_distribuido("g_v203_ps", "b")

    ok, c1 = a.conectar("/ws/dist", "127.0.0.1", "u1", "r1", "t1", "fallback")
    assert ok is True
    assert isinstance(c1, web_runtime.TempoRealConexao)
    ok_sala, err_sala = a.entrar_sala(c1, "lobby")
    assert ok_sala is True
    assert err_sala is None

    aplicados = b.sincronizar_distribuicao()
    assert aplicados >= 2

    snap_b = b.snapshot("/ws/dist")
    canal = snap_b["canais"][0]
    assert canal["conexoes_remotas"] >= 1
    assert canal["salas_remotas"]["lobby"] >= 1


def test_v203_broadcast_distribuido_com_cursor_global() -> None:
    a = _hub_distribuido("g_v203_bc", "a")
    b = _hub_distribuido("g_v203_bc", "b")

    ok1, _ = a.conectar("/ws/dist", "127.0.0.1", "u1", "r1", "t1", "fallback")
    ok2, c2 = b.conectar("/ws/dist", "127.0.0.1", "u2", "r2", "t2", "fallback")
    assert ok1 is True and ok2 is True
    assert isinstance(c2, web_runtime.TempoRealConexao)

    pub = a.publicar_mensagem("/ws/dist", "evt", {"ok": True}, exigir_ack=True)
    assert int(pub["cursor"]) > 0

    b.sincronizar_distribuicao()
    eventos = c2.drenar(10)
    entregues = [e for e in eventos if e.get("evento") == "evt"]
    assert len(entregues) == 1
    ev = entregues[0]
    assert int(ev["cursor"]) == int(pub["cursor"])
    assert ev["dados"]["ok"] is True


def test_v203_ack_nack_reenvio_ordenado_multino() -> None:
    a = _hub_distribuido("g_v203_ack", "a")
    b = _hub_distribuido("g_v203_ack", "b")

    ok2, c2 = b.conectar("/ws/dist", "127.0.0.1", "u2", "r2", "t2", "fallback")
    assert ok2 is True
    assert isinstance(c2, web_runtime.TempoRealConexao)

    pub = a.publicar_mensagem("/ws/dist", "chat", {"txt": "oi"}, id_usuario="u2", exigir_ack=True)
    b.sincronizar_distribuicao()
    eventos = [e for e in c2.drenar(10) if e.get("evento") == "chat"]
    assert len(eventos) == 1
    msg = eventos[0]
    msg_id = str(msg["id_mensagem"])
    cursor = int(msg["cursor"])

    nack = b.confirmar_ack("/ws/dist", msg_id, c2.id_conexao, status="nack")
    assert nack["ok"] is True
    a.sincronizar_distribuicao()
    b.sincronizar_distribuicao()

    retry_events = [e for e in c2.drenar(10) if str(e.get("id_mensagem")) == msg_id]
    assert len(retry_events) >= 1
    assert all(int(e.get("cursor", 0)) == cursor for e in retry_events)

    ack = b.confirmar_ack("/ws/dist", msg_id, c2.id_conexao, status="ack")
    assert ack["ok"] is True
    a.sincronizar_distribuicao()

    pend_a = a.snapshot("/ws/dist")["canais"][0]["pendencias_ack"]
    assert pend_a == 0


def test_v203_reconexao_cursor_fallback_http() -> None:
    app = web_runtime.WebApp()
    app.tempo_real.registrar_rota("/ws/rec", lambda req: {"aceitar": True}, {})
    app.tempo_real.ativar_fallback("/tempo-real/fallback", 1.0)
    rt = _start_runtime(app)
    try:
        base = f"http://127.0.0.1:{rt.port}/tempo-real/fallback"

        s1, c1 = _http_json("POST", base + "/conectar", {"canal": "/ws/rec"})
        assert s1 == 200
        id_c1 = str(c1["id_conexao"])

        app.tempo_real.publicar_mensagem("/ws/rec", "m1", {"n": 1})
        r1s, r1 = _http_json("GET", base + f"/receber?id_conexao={id_c1}&timeout_segundos=0.1")
        assert r1s == 200
        assert len(r1["eventos"]) >= 1
        cursor_ate = int(r1.get("cursor_ate", 0))
        assert cursor_ate > 0

        _http_json("POST", base + "/desconectar", {"id_conexao": id_c1})

        s2, c2 = _http_json(
            "POST",
            base + f"/conectar?cursor_ultimo={cursor_ate}",
            {"canal": "/ws/rec"},
        )
        assert s2 == 200
        id_c2 = str(c2["id_conexao"])

        app.tempo_real.publicar_mensagem("/ws/rec", "m2", {"n": 2})
        r2s, r2 = _http_json("GET", base + f"/receber?id_conexao={id_c2}&timeout_segundos=0.1")
        assert r2s == 200
        eventos_m2 = [e for e in r2["eventos"] if e.get("evento") == "m2"]
        assert len(eventos_m2) >= 1
        assert all(int(e.get("cursor", 0)) > cursor_ate for e in eventos_m2)
    finally:
        rt.stop()


def test_v203_integracao_multino_fallback_broadcast_distribuido() -> None:
    app_a = web_runtime.WebApp()
    app_b = web_runtime.WebApp()
    app_a.tempo_real.registrar_rota("/ws/multi", lambda req: {"aceitar": True}, {})
    app_b.tempo_real.registrar_rota("/ws/multi", lambda req: {"aceitar": True}, {})
    app_a.tempo_real.ativar_fallback("/tempo-real/fallback", 1.0)
    app_b.tempo_real.ativar_fallback("/tempo-real/fallback", 1.0)
    app_a.tempo_real.configurar_distribuicao(ativar=True, grupo="g_v203_http_multi", id_instancia="a", auto_sincronizar=False)
    app_b.tempo_real.configurar_distribuicao(ativar=True, grupo="g_v203_http_multi", id_instancia="b", auto_sincronizar=False)
    rt_a = _start_runtime(app_a)
    rt_b = _start_runtime(app_b)
    try:
        base_a = f"http://127.0.0.1:{rt_a.port}/tempo-real/fallback"
        base_b = f"http://127.0.0.1:{rt_b.port}/tempo-real/fallback"
        s1, c1 = _http_json("POST", base_a + "/conectar", {"canal": "/ws/multi"})
        s2, c2 = _http_json("POST", base_b + "/conectar", {"canal": "/ws/multi"})
        assert s1 == 200 and s2 == 200
        id_b = str(c2["id_conexao"])

        pub = app_a.tempo_real.publicar_mensagem("/ws/multi", "evt_dist", {"ok": True})
        assert int(pub["cursor"]) > 0
        app_b.tempo_real.sincronizar_distribuicao()

        rc, body = _http_json("GET", base_b + f"/receber?id_conexao={id_b}&timeout_segundos=0.2")
        assert rc == 200
        assert body["ok"] is True
        assert any(e.get("evento") == "evt_dist" for e in body["eventos"])
    finally:
        rt_a.stop()
        rt_b.stop()


def test_v203_limites_usuario_sala_e_metricas() -> None:
    hub = _hub_distribuido("g_v203_lim", "a")
    hub.definir_limites(
        {
            "max_mensagens_por_janela": 10,
            "max_mensagens_por_janela_usuario": 2,
            "max_mensagens_por_janela_sala": 2,
            "janela_rate_segundos": 30,
        }
    )
    ok, c = hub.conectar("/ws/dist", "127.0.0.1", "u1", "r1", "t1", "fallback")
    assert ok is True
    assert isinstance(c, web_runtime.TempoRealConexao)

    assert hub.validar_rate(c, {"sala": "s1"}) is True
    assert hub.validar_rate(c, {"sala": "s1"}) is True
    assert hub.validar_rate(c, {"sala": "s1"}) is False

    hub.publicar_mensagem("/ws/dist", "evt", {"x": 1}, exigir_ack=False)
    st = hub.snapshot("/ws/dist")
    assert st["metricas"]["entregues"] >= 1


def test_v203_fallback_quando_backplane_indisponivel_sem_quebra() -> None:
    hub = _hub_distribuido("g_v203_fb", "a")
    ok, c = hub.conectar("/ws/dist", "127.0.0.1", "u1", "r1", "t1", "fallback")
    assert ok is True
    assert isinstance(c, web_runtime.TempoRealConexao)

    cfg = hub.configurar_backplane(disponivel=False)
    assert cfg["ok"] is True

    pub = hub.publicar_mensagem("/ws/dist", "evt", {"ok": True}, exigir_ack=False)
    assert pub["backplane_degradado"] is True

    eventos = c.drenar(10)
    assert any(e.get("evento") == "evt" for e in eventos)

    st = hub.snapshot("/ws/dist")
    assert st["distribuicao"]["degradado"] is True
    assert st["metricas"]["falhas_backplane"] >= 1

    hub.configurar_backplane(disponivel=True)


def test_v203_concorrencia_alta_com_ordenacao_por_canal() -> None:
    a = _hub_distribuido("g_v203_stress", "a")
    b = _hub_distribuido("g_v203_stress", "b")

    ok, c = b.conectar("/ws/dist", "127.0.0.1", "u_stress", "r1", "t1", "fallback")
    assert ok is True
    assert isinstance(c, web_runtime.TempoRealConexao)

    total_por_publicador = 120
    erros: list[str] = []

    def pub_em(hub: web_runtime.TempoRealHub, prefixo: str) -> None:
        try:
            for i in range(total_por_publicador):
                hub.publicar_mensagem("/ws/dist", "evt_stress", {"origem": prefixo, "n": i})
        except Exception as exc:  # noqa: BLE001
            erros.append(str(exc))

    t1 = threading.Thread(target=pub_em, args=(a, "a"))
    t2 = threading.Thread(target=pub_em, args=(b, "b"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert erros == []
    b.sincronizar_distribuicao()
    eventos = [e for e in c.drenar(1000) if e.get("evento") == "evt_stress"]
    assert len(eventos) == total_por_publicador * 2

    cursores = [int(e.get("cursor", 0)) for e in eventos]
    assert all(cu > 0 for cu in cursores)
    assert cursores == sorted(cursores)
    assert len(set(cursores)) == len(cursores)


def test_v203_backplane_redis_integracao_real() -> None:
    redis_url = os.environ.get("TRAMA_TEST_REDIS_URL")
    proc: subprocess.Popen[bytes] | None = None
    workdir: Path | None = None

    if not redis_url:
        redis_bin = shutil.which("redis-server")
        if redis_bin:
            workdir = Path(".local/tmp/v203_redis_test")
            workdir.mkdir(parents=True, exist_ok=True)
            porta = 6391
            cfg = workdir / "redis_v203.conf"
            cfg.write_text(
                "\n".join(
                    [
                        f"port {porta}",
                        "bind 127.0.0.1",
                        "save \"\"",
                        "appendonly no",
                        "daemonize no",
                        f"dir {workdir}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            proc = subprocess.Popen([redis_bin, str(cfg)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.25)
            redis_url = f"redis://127.0.0.1:{porta}/0"
        else:
            pytest.skip("Sem redis-server local e sem TRAMA_TEST_REDIS_URL para validar integração redis.")

    sufixo = f"{int(time.time() * 1000)}"
    grupo_redis = f"g_v203_redis_{sufixo}"
    chave_prefixo = f"trama:test:v203:{sufixo}"

    a = web_runtime.TempoRealHub()
    b = web_runtime.TempoRealHub()
    a.registrar_rota("/ws/dist", lambda req: {"aceitar": True}, {})
    b.registrar_rota("/ws/dist", lambda req: {"aceitar": True}, {})
    a.configurar_distribuicao(
        ativar=True,
        grupo=grupo_redis,
        id_instancia="a",
        auto_sincronizar=False,
        backplane="redis",
        redis_url=redis_url,
        chave_prefixo_redis=chave_prefixo,
    )
    b.configurar_distribuicao(
        ativar=True,
        grupo=grupo_redis,
        id_instancia="b",
        auto_sincronizar=False,
        backplane="redis",
        redis_url=redis_url,
        chave_prefixo_redis=chave_prefixo,
    )
    try:
        ok, c = b.conectar("/ws/dist", "127.0.0.1", "u_redis", "r1", "t1", "fallback")
        assert ok is True
        assert isinstance(c, web_runtime.TempoRealConexao)

        pub = a.publicar_mensagem("/ws/dist", "evt_redis", {"ok": True})
        assert int(pub["cursor"]) > 0
        aplicados = b.sincronizar_distribuicao()
        assert aplicados >= 1
        eventos = [e for e in c.drenar(20) if e.get("evento") == "evt_redis"]
        assert len(eventos) == 1
        assert eventos[0]["dados"]["ok"] is True
    finally:
        if proc is not None:
            proc.terminate()
            proc.wait(timeout=3)
