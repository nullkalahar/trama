"""Base de autenticação federada/OIDC."""

from __future__ import annotations

import json
import threading
import time
from typing import Any
from urllib import request

from .comum import SecurityError
from .jwks import jwt_verificar_jwks

_OIDC_LOCK = threading.RLock()
_OIDC_PROVEDORES: dict[str, dict[str, Any]] = {}


def _issuer_normalizar(issuer_url: str) -> str:
    issuer = str(issuer_url or "").strip().rstrip("/")
    if not issuer:
        raise SecurityError("issuer_url OIDC é obrigatório.")
    return issuer


def _http_json(url: str, timeout_segundos: float = 2.0) -> dict[str, Any]:
    req = request.Request(str(url), headers={"Accept": "application/json"})  # noqa: S310
    try:
        with request.urlopen(req, timeout=float(timeout_segundos)) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise SecurityError(f"falha ao consultar endpoint OIDC: {exc}") from exc
    try:
        data = json.loads(body)
    except Exception as exc:  # noqa: BLE001
        raise SecurityError("resposta OIDC inválida (JSON malformado).") from exc
    if not isinstance(data, dict):
        raise SecurityError("resposta OIDC inválida (objeto esperado).")
    return data


def oidc_descobrir_configuracao(issuer_url: str, *, timeout_segundos: float = 2.0) -> dict[str, Any]:
    issuer = _issuer_normalizar(issuer_url)
    url = f"{issuer}/.well-known/openid-configuration"
    cfg = _http_json(url, timeout_segundos=timeout_segundos)
    iss = str(cfg.get("issuer") or "").strip().rstrip("/")
    if not iss:
        cfg["issuer"] = issuer
    elif iss != issuer:
        raise SecurityError("issuer retornado no discovery OIDC não confere com o configurado.")
    if not str(cfg.get("jwks_uri") or "").strip():
        raise SecurityError("configuração OIDC inválida: 'jwks_uri' ausente.")
    return cfg


def oidc_configurar_provedor(
    nome: str,
    issuer_url: str,
    *,
    audiencia: str | list[str] | None = None,
    timeout_segundos: float = 2.0,
    cache_ttl_jwks_segundos: float = 300.0,
) -> dict[str, Any]:
    nome_s = str(nome or "").strip()
    if not nome_s:
        raise SecurityError("nome do provedor OIDC é obrigatório.")
    cfg = oidc_descobrir_configuracao(issuer_url, timeout_segundos=timeout_segundos)
    prov = {
        "nome": nome_s,
        "issuer": str(cfg["issuer"]).rstrip("/"),
        "audiencia": audiencia,
        "jwks_uri": str(cfg["jwks_uri"]),
        "configuracao": dict(cfg),
        "timeout_segundos": float(timeout_segundos),
        "cache_ttl_jwks_segundos": float(cache_ttl_jwks_segundos),
        "atualizado_em": time.time(),
    }
    with _OIDC_LOCK:
        _OIDC_PROVEDORES[nome_s] = prov
    return dict(prov)


def oidc_obter_provedor(nome: str) -> dict[str, Any] | None:
    nome_s = str(nome or "").strip()
    if not nome_s:
        return None
    with _OIDC_LOCK:
        item = _OIDC_PROVEDORES.get(nome_s)
    return dict(item) if item else None


def oidc_listar_provedores() -> list[dict[str, Any]]:
    with _OIDC_LOCK:
        return [dict(v) for v in _OIDC_PROVEDORES.values()]


def oidc_remover_provedor(nome: str) -> bool:
    nome_s = str(nome or "").strip()
    if not nome_s:
        return False
    with _OIDC_LOCK:
        return _OIDC_PROVEDORES.pop(nome_s, None) is not None


def oidc_validar_token(
    nome_provedor: str,
    token: str,
    *,
    leeway_segundos: int = 0,
    audiencia: str | list[str] | None = None,
    emissor: str | None = None,
) -> dict[str, Any]:
    prov = oidc_obter_provedor(nome_provedor)
    if prov is None:
        raise SecurityError("provedor OIDC não configurado.")
    aud = audiencia if audiencia is not None else prov.get("audiencia")
    iss = str(emissor or prov.get("issuer") or "").strip() or None
    claims = jwt_verificar_jwks(
        token,
        str(prov["jwks_uri"]),
        leeway_segundos=leeway_segundos,
        emissor=iss,
        audiencia=aud,
        cache_ttl_segundos=float(prov.get("cache_ttl_jwks_segundos", 300.0)),
        timeout_segundos=float(prov.get("timeout_segundos", 2.0)),
    )
    papeis_raw = claims.get("roles")
    if papeis_raw is None:
        papeis_raw = claims.get("papeis")
    if isinstance(papeis_raw, (list, tuple, set)):
        papeis = [str(x) for x in papeis_raw]
    elif papeis_raw is None:
        papeis = []
    else:
        papeis = [str(papeis_raw)]
    identidade = {
        "id_usuario_externo": str(claims.get("sub") or ""),
        "email": str(claims.get("email") or ""),
        "nome": str(claims.get("name") or claims.get("nome") or ""),
        "papeis": papeis,
    }
    return {
        "ok": True,
        "provedor": str(prov["nome"]),
        "claims": claims,
        "identidade": identidade,
    }
