"""Transporte WebSocket do tempo real da Trama."""

from __future__ import annotations

import json
import socket
import time
import uuid
from typing import Any, Callable

from . import observability_runtime
from .realtime_core import TempoRealConexao


def processar_upgrade_websocket_tempo_real(
    contexto: Any,
    *,
    app: Any,
    path: str,
    query: dict[str, object],
    headers_map: dict[str, str],
    invocar_sync: Callable[[object, list[object]], object],
    processar_mensagem: Callable[[TempoRealConexao, dict[str, object], Callable[[object, list[object]], object], dict[str, object]], None],
) -> bool:
    upgrade = str(headers_map.get("upgrade", "")).lower()
    connection = str(headers_map.get("connection", "")).lower()
    if upgrade != "websocket" or "upgrade" not in connection:
        return False
    info = app.tempo_real.rota_info(path)
    if info is None:
        return False
    sec_key = str(headers_map.get("sec-websocket-key", "")).strip()
    if not sec_key:
        contexto._send_json(400, {"ok": False, "erro": {"codigo": "WS_HANDSHAKE_INVALIDO", "mensagem": "Sec-WebSocket-Key ausente."}}, None)
        return True

    ok_auth, auth, err_auth = contexto._auth_ws_usuario(headers_map, query, dict(info.get("opcoes", {})))
    if not ok_auth:
        contexto._send_json(401, {"ok": False, "erro": err_auth}, None)
        return True

    cursor_q = query.get("cursor_ultimo")
    if cursor_q is None:
        cursor_q = query.get("cursor")
    try:
        cursor_ultimo = int(cursor_q) if cursor_q is not None else None
    except Exception:
        cursor_ultimo = None

    ok, obj = app.tempo_real.conectar(
        canal=path,
        ip=contexto.client_address[0] if contexto.client_address else "0.0.0.0",
        id_usuario=(auth or {}).get("id_usuario"),  # type: ignore[arg-type]
        id_requisicao=str(getattr(contexto, "_trama_id_requisicao", uuid.uuid4().hex)),
        id_traco=str(getattr(contexto, "_trama_id_traco", uuid.uuid4().hex)),
        modo="websocket",
        socket_conn=contexto.connection,
        cursor_ultimo=cursor_ultimo,
    )
    if not ok:
        contexto._send_json(429, {"ok": False, "erro": obj}, None)
        return True
    c = obj  # type: ignore[assignment]
    assert isinstance(c, TempoRealConexao)

    h = info.get("handler")
    if h is not None:
        try:
            req = contexto._ctx_conexao(c, {"evento": "conectar"})
            res = invocar_sync(h, [req])
            if isinstance(res, dict) and res.get("aceitar") is False:
                app.tempo_real.desconectar(c, motivo="negada")
                contexto._send_json(403, {"ok": False, "erro": {"codigo": "CONEXAO_NEGADA"}}, None)
                return True
        except Exception:
            app.tempo_real.desconectar(c, motivo="erro_handler")
            contexto._send_json(500, {"ok": False, "erro": {"codigo": "ERRO_HANDLER_CONECTAR"}}, None)
            return True

    accept = contexto._ws_accept_key(sec_key)
    contexto.send_response(101, "Switching Protocols")
    contexto.send_header("Upgrade", "websocket")
    contexto.send_header("Connection", "Upgrade")
    contexto.send_header("Sec-WebSocket-Accept", accept)
    contexto._add_common_headers({})
    contexto.end_headers()
    contexto.close_connection = False
    contexto.connection.settimeout(0.2)

    try:
        ultimo_ping = 0.0
        contexto._emitir_evento_ws(
            c,
            {
                "ok": True,
                "evento": "conectado",
                "id_conexao": c.id_conexao,
                "connection_id": c.id_conexao,
                "id_usuario": c.id_usuario,
                "user_id": c.id_usuario,
                "canal": c.canal,
                "cursor_ultimo_confirmado": c.cursor_ultimo_confirmado,
            },
        )
        while c.ativa:
            pendentes = c.drenar(100)
            for p in pendentes:
                contexto._emitir_evento_ws(c, p)

            try:
                opcode, payload = contexto._ws_recv_frame(contexto.connection)
            except socket.timeout:
                hb = float(app.tempo_real.limites["heartbeat_segundos"])
                if time.time() - ultimo_ping >= hb:
                    contexto._ws_send_frame(contexto.connection, b"", opcode=0x9)
                    ultimo_ping = time.time()
                continue
            if opcode == 0x8:
                contexto._ws_send_frame(contexto.connection, b"", opcode=0x8)
                break
            if opcode == 0x9:
                contexto._ws_send_frame(contexto.connection, payload, opcode=0xA)
                continue
            if opcode == 0xA:
                c.ultimo_heartbeat_em = time.time()
                continue
            if opcode != 0x1:
                continue
            texto = payload.decode("utf-8", errors="replace")
            try:
                if texto.startswith("42"):
                    # Compatibilidade mínima Socket.IO: 42["evento",{...}]
                    raw = json.loads(texto[2:])
                    if isinstance(raw, list) and len(raw) >= 1:
                        msg = {
                            "tipo": str(raw[0]),
                            "socketio_evento": str(raw[0]),
                            "dados": raw[1] if len(raw) >= 2 else {},
                        }
                    else:
                        msg = {}
                else:
                    msg = json.loads(texto) if texto.strip() else {}
            except json.JSONDecodeError:
                contexto._emitir_evento_ws(c, {"ok": False, "erro": {"codigo": "MENSAGEM_JSON_INVALIDA"}})
                continue
            if not isinstance(msg, dict):
                contexto._emitir_evento_ws(c, {"ok": False, "erro": {"codigo": "MENSAGEM_INVALIDA"}})
                continue
            processar_mensagem(c, msg, invocar_sync, info)
    except Exception as exc:  # noqa: BLE001
        observability_runtime.registrar_runtime_metrica(
            "tempo_real",
            "erro_conexao",
            labels={"canal": c.canal, "erro": str(exc)[:120]},
        )
    finally:
        app.tempo_real.desconectar(c, motivo="websocket_encerrado")
        if h is not None:
            try:
                req = contexto._ctx_conexao(c, {"evento": "desconectar"})
                invocar_sync(h, [req])
            except Exception:
                pass
    return True
