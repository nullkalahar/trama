from __future__ import annotations

import base64
import json
import os
import socket
import struct
import time

from trama import security_runtime
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


def _http_read_head(sock: socket.socket) -> bytes:
    data = b""
    while b"\r\n\r\n" not in data:
        part = sock.recv(4096)
        if not part:
            break
        data += part
    return data


def _ws_connect(host: str, port: int, path: str, extra_headers: dict[str, str] | None = None) -> tuple[socket.socket, int]:
    s = socket.create_connection((host, port), timeout=2.0)
    s.settimeout(2.0)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    hdrs = {
        "Host": f"{host}:{port}",
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Sec-WebSocket-Version": "13",
        "Sec-WebSocket-Key": key,
    }
    hdrs.update(extra_headers or {})
    req = "GET {} HTTP/1.1\r\n{}\r\n\r\n".format(path, "\r\n".join(f"{k}: {v}" for k, v in hdrs.items()))
    s.sendall(req.encode("utf-8"))
    head = _http_read_head(s)
    first = head.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
    code = int(first.split(" ")[1])
    return s, code


def _ws_send_json(sock: socket.socket, payload: dict[str, object]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    b1 = 0x81
    ln = len(data)
    mask = os.urandom(4)
    if ln <= 125:
        head = bytes([b1, 0x80 | ln])
    elif ln <= 65535:
        head = bytes([b1, 0x80 | 126]) + struct.pack("!H", ln)
    else:
        head = bytes([b1, 0x80 | 127]) + struct.pack("!Q", ln)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    sock.sendall(head + mask + masked)


def _ws_recv_frame(sock: socket.socket) -> tuple[int, bytes]:
    hdr = sock.recv(2)
    if len(hdr) < 2:
        raise ConnectionError("sem frame")
    b1, b2 = hdr[0], hdr[1]
    opcode = b1 & 0x0F
    ln = b2 & 0x7F
    if ln == 126:
        ln = struct.unpack("!H", sock.recv(2))[0]
    elif ln == 127:
        ln = struct.unpack("!Q", sock.recv(8))[0]
    data = b""
    while len(data) < ln:
        part = sock.recv(ln - len(data))
        if not part:
            break
        data += part
    return opcode, data


def _ws_recv_json_event(sock: socket.socket, evento: str | None = None, timeout: float = 5.0) -> dict[str, object]:
    end = time.time() + timeout
    while time.time() < end:
        opcode, data = _ws_recv_frame(sock)
        if opcode in {0x9, 0xA, 0x8}:
            continue
        if opcode != 0x1:
            continue
        payload = json.loads(data.decode("utf-8", errors="replace"))
        if evento is None:
            return payload
        if payload.get("evento") == evento:
            return payload
    raise AssertionError(f"evento websocket não recebido: {evento}")


def _http_json(method: str, url: str, body: dict[str, object] | None = None) -> tuple[int, dict[str, object]]:
    from urllib import request
    from urllib.error import HTTPError

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


def test_v13_websocket_auth_jwt_handshake() -> None:
    app = web_runtime.WebApp()

    def handler(req: dict[str, object]) -> dict[str, object]:
        _ = req
        return {"aceitar": True}

    app.tempo_real.registrar_rota("/ws/seguro", handler, {"jwt_segredo": "segredo-ws"})
    rt = _start_runtime(app)
    try:
        s1, code1 = _ws_connect("127.0.0.1", rt.port, "/ws/seguro")
        assert code1 == 401
        s1.close()

        tok = security_runtime.jwt_criar({"sub": "u1"}, "segredo-ws", 60)
        s2, code2 = _ws_connect("127.0.0.1", rt.port, f"/ws/seguro?token={tok}")
        assert code2 == 101
        ev = _ws_recv_json_event(s2, "conectado")
        assert ev["id_usuario"] == "u1"
        _ws_send_json(s2, {"tipo": "ping"})
        pong = _ws_recv_json_event(s2, "pong")
        assert pong["evento"] == "pong"
        s2.close()
    finally:
        rt.stop()


def test_v13_salas_presence_typing_read_receipt_broadcast_seletivo() -> None:
    app = web_runtime.WebApp()
    app.tempo_real.registrar_rota("/ws/chat", lambda req: {"aceitar": True}, {})
    rt = _start_runtime(app)
    try:
        c1, code1 = _ws_connect("127.0.0.1", rt.port, "/ws/chat")
        c2, code2 = _ws_connect("127.0.0.1", rt.port, "/ws/chat")
        assert code1 == 101
        assert code2 == 101

        e1 = _ws_recv_json_event(c1, "conectado")
        e2 = _ws_recv_json_event(c2, "conectado")
        assert e1["id_conexao"] != e2["id_conexao"]

        _ws_send_json(c1, {"tipo": "entrar_sala", "sala": "sala-1"})
        _ws_send_json(c2, {"tipo": "entrar_sala", "sala": "sala-1"})
        _ = _ws_recv_json_event(c1, "entrar_sala")
        _ = _ws_recv_json_event(c2, "entrar_sala")

        _ws_send_json(c1, {"tipo": "typing", "sala": "sala-1", "digitando": True})
        ev_typing = _ws_recv_json_event(c2, "typing")
        assert ev_typing["dados"]["sala"] == "sala-1"

        _ws_send_json(c1, {"tipo": "read_receipt", "sala": "sala-1", "mensagem_id": "m-1"})
        ev_rr = _ws_recv_json_event(c2, "read_receipt")
        assert ev_rr["dados"]["mensagem_id"] == "m-1"

        _ws_send_json(c1, {"tipo": "broadcast_conexao", "id_conexao": e2["id_conexao"], "evento": "privado", "dados": {"ok": True}})
        ev_priv = _ws_recv_json_event(c2, "privado")
        assert ev_priv["dados"]["ok"] is True

        c1.close()
        c2.close()
    finally:
        rt.stop()


def test_v13_fallback_e_limites() -> None:
    app = web_runtime.WebApp()
    app.tempo_real.registrar_rota("/ws/fallback", lambda req: {"aceitar": True}, {"jwt_segredo": "seg-fb"})
    app.tempo_real.ativar_fallback("/tempo-real/fallback", 2.0)
    app.tempo_real.definir_limites({"max_conexoes_por_ip": 1, "max_mensagens_por_janela": 2, "janela_rate_segundos": 10})
    rt = _start_runtime(app)
    try:
        tok = security_runtime.jwt_criar({"sub": "u-fb"}, "seg-fb", 60)
        base = f"http://127.0.0.1:{rt.port}/tempo-real/fallback"

        c1_status, c1_payload = _http_json(
            "POST",
            base + f"/conectar?token={tok}",
            {"canal": "/ws/fallback"},
        )
        assert c1_status == 200
        id_c = str(c1_payload["id_conexao"])

        c2_status, _ = _http_json(
            "POST",
            base + f"/conectar?token={tok}",
            {"canal": "/ws/fallback"},
        )
        assert c2_status == 429

        s1, _ = _http_json("POST", base + "/enviar", {"id_conexao": id_c, "mensagem": {"tipo": "ping"}})
        s2, _ = _http_json("POST", base + "/enviar", {"id_conexao": id_c, "mensagem": {"tipo": "ping"}})
        s3, _ = _http_json("POST", base + "/enviar", {"id_conexao": id_c, "mensagem": {"tipo": "ping"}})
        assert s1 == 200
        assert s2 == 200
        assert s3 == 200

        rcv_status, rcv_payload = _http_json("GET", base + f"/receber?id_conexao={id_c}&timeout_segundos=0.2")
        assert rcv_status == 200
        eventos = list(rcv_payload.get("eventos", []))
        assert any(e.get("evento") == "pong" for e in eventos)
        assert any((e.get("erro") or {}).get("codigo") == "RATE_MENSAGENS_EXCEDIDO" for e in eventos)

        ds_status, ds_payload = _http_json("POST", base + "/desconectar", {"id_conexao": id_c})
        assert ds_status == 200
        assert ds_payload["ok"] is True
    finally:
        rt.stop()


def test_v15_ack_reenvio_e_socketio_minimo() -> None:
    app = web_runtime.WebApp()

    def handler(req: dict[str, object]) -> dict[str, object]:
        if req.get("evento") == "mensagem":
            msg = req.get("mensagem", {})
            if isinstance(msg, dict) and msg.get("tipo") == "chat":
                return {
                    "destino": "sala",
                    "sala": "lobby",
                    "evento": "chat_msg",
                    "dados": {"txt": msg.get("txt")},
                    "exigir_ack": True,
                }
        return {"aceitar": True}

    app.tempo_real.registrar_rota("/ws/v15", handler, {})
    rt = _start_runtime(app)
    try:
        c1, code1 = _ws_connect("127.0.0.1", rt.port, "/ws/v15")
        c2, code2 = _ws_connect("127.0.0.1", rt.port, "/ws/v15")
        assert code1 == 101
        assert code2 == 101
        _ = _ws_recv_json_event(c1, "conectado")
        _ = _ws_recv_json_event(c2, "conectado")

        _ws_send_json(c1, {"tipo": "entrar_sala", "sala": "lobby"})
        _ws_send_json(c2, {"tipo": "entrar_sala", "sala": "lobby"})
        _ = _ws_recv_json_event(c1, "entrar_sala")
        _ = _ws_recv_json_event(c2, "entrar_sala")

        # Compat Socket.IO mínima: 42["chat",{...}]
        _ws_send_json(c1, {"tipo": "chat", "txt": "json"})
        sio_payload = json.dumps(["chat", {"txt": "sio"}], ensure_ascii=False).encode("utf-8")
        ln = len(sio_payload) + 2
        mask = os.urandom(4)
        header = bytes([0x81, 0x80 | ln])
        raw = b"42" + sio_payload
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(raw))
        c1.sendall(header + mask + masked)

        ev1 = _ws_recv_json_event(c2, "chat_msg")
        assert "id_mensagem" in ev1
        assert ev1.get("exigir_ack") is True
        msg_id = str(ev1["id_mensagem"])

        _ws_send_json(c2, {"tipo": "ack", "id_mensagem": msg_id})
        ack_res = _ws_recv_json_event(c2, "ack_resultado")
        assert ack_res["dados"]["ok"] is True

        reenviar = app.tempo_real.reenviar_pendentes("/ws/v15", id_mensagem=msg_id)
        assert reenviar["ok"] is True
        assert "reenvios" in reenviar

        c1.close()
        c2.close()
    finally:
        rt.stop()
