"""Módulo de sessão e rotação de tokens."""

from __future__ import annotations

from dataclasses import dataclass, field
import threading
from typing import Any

from .. import observability_runtime
from .comum import SecurityError, agora, novo_id
from .jwt import jwt_criar, jwt_verificar
from .politicas import token_bloquear, token_esta_bloqueado


def _emitir_metrica(evento: str, valor: float = 1.0, labels: dict[str, object] | None = None) -> None:
    observability_runtime.registrar_runtime_metrica("seguranca", evento, valor=float(valor), labels=dict(labels or {}))


@dataclass
class _SessaoAuth:
    id_sessao: str
    id_usuario: str
    id_dispositivo: str
    refresh_jti_atual: str
    ativa: bool = True
    criada_em: float = field(default_factory=agora)
    atualizada_em: float = field(default_factory=agora)
    expira_em: float | None = None
    metadados: dict[str, object] = field(default_factory=dict)


_SESSAO_LOCK = threading.RLock()
_SESSOES: dict[str, _SessaoAuth] = {}
_SESSAO_POR_USUARIO: dict[str, set[str]] = {}
_SESSAO_POR_DISPOSITIVO: dict[tuple[str, str], set[str]] = {}


def sessao_criar(
    id_usuario: str,
    id_dispositivo: str | None = None,
    ttl_refresh_segundos: int = 30 * 24 * 3600,
    metadados: dict[str, object] | None = None,
) -> dict[str, object]:
    usuario = str(id_usuario or "").strip()
    if not usuario:
        raise SecurityError("id_usuario é obrigatório para criar sessão.")
    dispositivo = str(id_dispositivo or "dispositivo_padrao").strip() or "dispositivo_padrao"
    id_sessao = novo_id("sessao")
    refresh_jti = novo_id("refresh")
    ttl = max(int(ttl_refresh_segundos), 1)
    agora_local = agora()
    sessao = _SessaoAuth(
        id_sessao=id_sessao,
        id_usuario=usuario,
        id_dispositivo=dispositivo,
        refresh_jti_atual=refresh_jti,
        ativa=True,
        criada_em=agora_local,
        atualizada_em=agora_local,
        expira_em=agora_local + ttl,
        metadados=dict(metadados or {}),
    )
    with _SESSAO_LOCK:
        _SESSOES[id_sessao] = sessao
        _SESSAO_POR_USUARIO.setdefault(usuario, set()).add(id_sessao)
        _SESSAO_POR_DISPOSITIVO.setdefault((usuario, dispositivo), set()).add(id_sessao)
    _emitir_metrica("sessao_criada")
    return {
        "ok": True,
        "id_sessao": id_sessao,
        "id_usuario": usuario,
        "id_dispositivo": dispositivo,
        "refresh_jti": refresh_jti,
        "expira_em": sessao.expira_em,
    }


def sessao_obter(id_sessao: str) -> dict[str, object] | None:
    sid = str(id_sessao or "").strip()
    if not sid:
        return None
    with _SESSAO_LOCK:
        s = _SESSOES.get(sid)
        if s is None:
            return None
        return {
            "id_sessao": s.id_sessao,
            "id_usuario": s.id_usuario,
            "id_dispositivo": s.id_dispositivo,
            "refresh_jti_atual": s.refresh_jti_atual,
            "ativa": bool(s.ativa),
            "criada_em": float(s.criada_em),
            "atualizada_em": float(s.atualizada_em),
            "expira_em": s.expira_em,
            "metadados": dict(s.metadados),
        }


def sessao_ativa(id_sessao: str) -> bool:
    sid = str(id_sessao or "").strip()
    if not sid:
        return False
    now = agora()
    with _SESSAO_LOCK:
        s = _SESSOES.get(sid)
        if s is None or not s.ativa:
            return False
        if s.expira_em is not None and float(s.expira_em) <= now:
            s.ativa = False
            s.atualizada_em = now
            return False
        return True


def _revogar_sessao_ids(ids: set[str], motivo: str) -> int:
    now = agora()
    total = 0
    with _SESSAO_LOCK:
        for sid in set(ids):
            s = _SESSOES.get(sid)
            if s is None:
                continue
            if s.ativa:
                total += 1
            s.ativa = False
            s.atualizada_em = now
    if total > 0:
        _emitir_metrica("sessao_revogada", total, {"motivo": str(motivo)})
    return total


def sessao_revogar(id_sessao: str, motivo: str = "manual") -> dict[str, object]:
    qtd = _revogar_sessao_ids({str(id_sessao or "")}, motivo=motivo)
    return {"ok": True, "revogadas": int(qtd), "motivo": str(motivo)}


def sessao_revogar_dispositivo(id_usuario: str, id_dispositivo: str, motivo: str = "dispositivo") -> dict[str, object]:
    chave = (str(id_usuario or ""), str(id_dispositivo or ""))
    with _SESSAO_LOCK:
        ids = set(_SESSAO_POR_DISPOSITIVO.get(chave, set()))
    qtd = _revogar_sessao_ids(ids, motivo=motivo)
    return {"ok": True, "revogadas": int(qtd), "motivo": str(motivo)}


def sessao_revogar_usuario(id_usuario: str, motivo: str = "usuario") -> dict[str, object]:
    usr = str(id_usuario or "")
    with _SESSAO_LOCK:
        ids = set(_SESSAO_POR_USUARIO.get(usr, set()))
    qtd = _revogar_sessao_ids(ids, motivo=motivo)
    return {"ok": True, "revogadas": int(qtd), "motivo": str(motivo)}


def token_acesso_emitir(
    id_usuario: str,
    segredo: str,
    exp_segundos: int = 900,
    id_sessao: str | None = None,
    id_dispositivo: str | None = None,
    permissoes: list[str] | None = None,
    claims_extras: dict[str, object] | None = None,
) -> str:
    payload: dict[str, object] = {
        "sub": str(id_usuario),
        "id_usuario": str(id_usuario),
        "tipo_token": "acesso",
        "permissoes": list(permissoes or []),
    }
    if id_sessao:
        payload["sid"] = str(id_sessao)
        payload["id_sessao"] = str(id_sessao)
    if id_dispositivo:
        payload["did"] = str(id_dispositivo)
        payload["id_dispositivo"] = str(id_dispositivo)
    payload.update(dict(claims_extras or {}))
    _emitir_metrica("token_acesso_emitido")
    return jwt_criar(payload, segredo, exp_segundos=exp_segundos)


def refresh_token_emitir(
    id_usuario: str,
    segredo: str,
    id_sessao: str,
    id_dispositivo: str | None = None,
    exp_segundos: int = 30 * 24 * 3600,
    claims_extras: dict[str, object] | None = None,
) -> str:
    sid = str(id_sessao or "").strip()
    if not sid:
        raise SecurityError("id_sessao é obrigatório para refresh token.")
    with _SESSAO_LOCK:
        sessao = _SESSOES.get(sid)
        if sessao is None:
            raise SecurityError("sessao_inexistente")
        if not sessao.ativa:
            raise SecurityError("sessao_revogada")
        jti = novo_id("rt")
        sessao.refresh_jti_atual = jti
        sessao.atualizada_em = agora()
    payload: dict[str, object] = {
        "sub": str(id_usuario),
        "id_usuario": str(id_usuario),
        "sid": sid,
        "id_sessao": sid,
        "did": str(id_dispositivo or sessao.id_dispositivo),
        "id_dispositivo": str(id_dispositivo or sessao.id_dispositivo),
        "jti": jti,
        "tipo_token": "refresh",
    }
    payload.update(dict(claims_extras or {}))
    _emitir_metrica("refresh_emitido")
    return jwt_criar(payload, segredo, exp_segundos=exp_segundos)


def refresh_token_trocar(
    token_refresh: str,
    segredo: str,
    exp_segundos: int = 30 * 24 * 3600,
) -> dict[str, object]:
    claims = jwt_verificar(token_refresh, segredo)
    tipo = str(claims.get("tipo_token") or "")
    if tipo != "refresh":
        raise SecurityError("token_nao_refresh")
    sid = str(claims.get("sid") or claims.get("id_sessao") or "").strip()
    jti = str(claims.get("jti") or "").strip()
    uid = str(claims.get("id_usuario") or claims.get("sub") or "").strip()
    did = str(claims.get("id_dispositivo") or claims.get("did") or "").strip() or "dispositivo_padrao"
    if not sid or not jti or not uid:
        raise SecurityError("refresh_token_malformado")
    now = agora()
    with _SESSAO_LOCK:
        sessao = _SESSOES.get(sid)
        if sessao is None or not sessao.ativa:
            raise SecurityError("sessao_revogada")
        if sessao.expira_em is not None and float(sessao.expira_em) <= now:
            sessao.ativa = False
            sessao.atualizada_em = now
            raise SecurityError("sessao_expirada")
        if jti != sessao.refresh_jti_atual:
            sessao.ativa = False
            sessao.atualizada_em = now
            ttl_reuso = max(float(claims.get("exp", now + 60)) - now, 60.0)
            token_bloquear(token_refresh, ttl_reuso, motivo="refresh_reuso_detectado")
            _emitir_metrica("refresh_reuso_detectado")
            raise SecurityError("refresh_reuso_detectado")
        novo_jti = novo_id("rt")
        sessao.refresh_jti_atual = novo_jti
        sessao.atualizada_em = now
    if token_esta_bloqueado(token_refresh):
        _emitir_metrica("refresh_negado", labels={"motivo": "denylist"})
        raise SecurityError("refresh_token_revogado")
    ttl_antigo = max(float(claims.get("exp", now + 60)) - now, 60.0)
    token_bloquear(token_refresh, ttl_antigo, motivo="refresh_rotacionado")
    payload_novo: dict[str, Any] = {
        "sub": uid,
        "id_usuario": uid,
        "sid": sid,
        "id_sessao": sid,
        "did": did,
        "id_dispositivo": did,
        "jti": novo_jti,
        "tipo_token": "refresh",
    }
    novo_refresh = jwt_criar(payload_novo, segredo, exp_segundos=exp_segundos)
    _emitir_metrica("refresh_rotacionado")
    return {
        "ok": True,
        "id_usuario": uid,
        "id_sessao": sid,
        "id_dispositivo": did,
        "refresh_token": novo_refresh,
        "refresh_jti": novo_jti,
    }
