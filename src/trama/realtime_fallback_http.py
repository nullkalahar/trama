"""Transporte HTTP fallback do tempo real da Trama."""

from __future__ import annotations

import uuid
from typing import Any, Callable

from .realtime_core import TempoRealConexao


def processar_fallback_tempo_real_http(
    contexto: Any,
    *,
    app: Any,
    path: str,
    query: dict[str, object],
    headers_map: dict[str, str],
    invocar_sync: Callable[[object, list[object]], object],
    processar_mensagem: Callable[[TempoRealConexao, dict[str, object], Callable[[object, list[object]], object], dict[str, object]], None],
) -> bool:
    if not app.tempo_real.fallback_ativo:
        return False
    prefixo = app.tempo_real.fallback_prefixo
    if not path.startswith(prefixo):
        return False

    raw_body, body, _, _, body_err = contexto._read_body()
    _ = raw_body
    if body_err:
        contexto._send_json(body_err[0], body_err[1], None)
        return True
    corpo = body or {}
    sufixo = path[len(prefixo) :] or "/"

    if sufixo == "/status":
        contexto._send_json(200, app.tempo_real.snapshot(str(query.get("canal") or "") or None), None)
        return True

    if sufixo == "/conectar":
        canal = str(corpo.get("canal") or query.get("canal") or "")
        info = app.tempo_real.rota_info(canal)
        if info is None:
            contexto._send_json(404, {"ok": False, "erro": {"codigo": "CANAL_NAO_ENCONTRADO"}}, None)
            return True
        ok_auth, auth, err_auth = contexto._auth_ws_usuario(headers_map, query, dict(info.get("opcoes", {})))
        if not ok_auth:
            contexto._send_json(401, {"ok": False, "erro": err_auth}, None)
            return True
        cursor_ultimo_raw = corpo.get("cursor_ultimo")
        if cursor_ultimo_raw is None:
            cursor_ultimo_raw = query.get("cursor_ultimo")
        if cursor_ultimo_raw is None:
            cursor_ultimo_raw = query.get("cursor")
        try:
            cursor_ultimo = int(cursor_ultimo_raw) if cursor_ultimo_raw is not None else None
        except Exception:
            cursor_ultimo = None

        ok, obj = app.tempo_real.conectar(
            canal=canal,
            ip=contexto.client_address[0] if contexto.client_address else "0.0.0.0",
            id_usuario=(auth or {}).get("id_usuario"),  # type: ignore[arg-type]
            id_requisicao=str(getattr(contexto, "_trama_id_requisicao", uuid.uuid4().hex)),
            id_traco=str(getattr(contexto, "_trama_id_traco", uuid.uuid4().hex)),
            modo="fallback",
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
        contexto._send_json(
            200,
            {
                "ok": True,
                "id_conexao": c.id_conexao,
                "connection_id": c.id_conexao,
                "id_usuario": c.id_usuario,
                "user_id": c.id_usuario,
                "canal": canal,
                "cursor_ultimo_confirmado": c.cursor_ultimo_confirmado,
            },
            None,
        )
        return True

    if sufixo == "/desconectar":
        id_c = str(corpo.get("id_conexao") or query.get("id_conexao") or query.get("connection_id") or "")
        c = app.tempo_real.por_id(id_c)
        if c is None:
            contexto._send_json(404, {"ok": False, "erro": {"codigo": "CONEXAO_NAO_ENCONTRADA"}}, None)
            return True
        app.tempo_real.desconectar(c, motivo="fallback_desconectar")
        contexto._send_json(200, {"ok": True}, None)
        return True

    if sufixo == "/receber":
        id_c = str(query.get("id_conexao") or query.get("connection_id") or corpo.get("id_conexao") or "")
        c = app.tempo_real.por_id(id_c)
        if c is None:
            contexto._send_json(404, {"ok": False, "erro": {"codigo": "CONEXAO_NAO_ENCONTRADA"}}, None)
            return True
        timeout = query.get("timeout_segundos")
        cursor_desde = query.get("cursor_desde")
        if cursor_desde is None:
            cursor_desde = query.get("cursor")
        try:
            cursor_int = int(cursor_desde) if cursor_desde is not None else None
        except Exception:
            cursor_int = None
        evs = app.tempo_real.receber_fallback(
            c,
            float(timeout) if timeout is not None else None,
            cursor_desde=cursor_int,
        )
        cursor_ate = int(c.cursor_ultimo_confirmado)
        contexto._send_json(200, {"ok": True, "eventos": evs, "cursor_ate": cursor_ate}, None)
        return True

    if sufixo == "/enviar":
        id_c = str(corpo.get("id_conexao") or query.get("id_conexao") or "")
        c = app.tempo_real.por_id(id_c)
        if c is None:
            contexto._send_json(404, {"ok": False, "erro": {"codigo": "CONEXAO_NAO_ENCONTRADA"}}, None)
            return True
        info = app.tempo_real.rota_info(c.canal) or {}
        msg = corpo.get("mensagem", corpo)
        if not isinstance(msg, dict):
            contexto._send_json(422, {"ok": False, "erro": {"codigo": "MENSAGEM_INVALIDA"}}, None)
            return True
        processar_mensagem(c, msg, invocar_sync, info)
        contexto._send_json(200, {"ok": True}, None)
        return True

    contexto._send_json(404, {"ok": False, "erro": {"codigo": "FALLBACK_ROTA_INVALIDA"}}, None)
    return True
