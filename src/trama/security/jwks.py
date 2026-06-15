"""Módulo JWKS com cache e rotação."""

from __future__ import annotations

import json
import threading
import time
from typing import Any
from urllib import request

from .comum import SecurityError
from .jwt import jwt_ler_cabecalho, jwt_publica_de_jwk, jwt_verificar

_JWKS_CACHE_LOCK = threading.RLock()
_JWKS_CACHE: dict[str, dict[str, Any]] = {}


def _agora() -> float:
    return time.time()


def _http_json(url: str, timeout_segundos: float = 2.0) -> dict[str, Any]:
    req = request.Request(str(url), headers={"Accept": "application/json"})  # noqa: S310
    try:
        with request.urlopen(req, timeout=float(timeout_segundos)) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise SecurityError(f"falha ao consultar JWKS: {exc}") from exc
    try:
        data = json.loads(body)
    except Exception as exc:  # noqa: BLE001
        raise SecurityError("resposta JWKS inválida (JSON malformado).") from exc
    if not isinstance(data, dict):
        raise SecurityError("resposta JWKS inválida (objeto esperado).")
    return data


def jwks_cache_limpar(url: str | None = None) -> int:
    with _JWKS_CACHE_LOCK:
        if url is None:
            total = len(_JWKS_CACHE)
            _JWKS_CACHE.clear()
            return total
        return 1 if _JWKS_CACHE.pop(str(url), None) is not None else 0


def jwks_obter(
    url_jwks: str,
    *,
    cache_ttl_segundos: float = 300.0,
    timeout_segundos: float = 2.0,
    forcar_refresh: bool = False,
) -> dict[str, Any]:
    url = str(url_jwks or "").strip()
    if not url:
        raise SecurityError("url_jwks é obrigatória.")
    ttl = max(float(cache_ttl_segundos), 1.0)
    now = _agora()
    with _JWKS_CACHE_LOCK:
        item = _JWKS_CACHE.get(url)
        if (
            item is not None
            and not bool(forcar_refresh)
            and float(item.get("expira_em", 0.0)) > now
            and isinstance(item.get("jwks"), dict)
        ):
            return dict(item["jwks"])
    jwks = _http_json(url, timeout_segundos=timeout_segundos)
    if not isinstance(jwks.get("keys"), list):
        raise SecurityError("documento JWKS inválido: campo 'keys' ausente.")
    with _JWKS_CACHE_LOCK:
        _JWKS_CACHE[url] = {
            "jwks": dict(jwks),
            "atualizado_em": now,
            "expira_em": now + ttl,
        }
    return dict(jwks)


def jwks_chave_por_kid(
    url_jwks: str,
    kid: str,
    *,
    cache_ttl_segundos: float = 300.0,
    timeout_segundos: float = 2.0,
) -> dict[str, Any]:
    kid_s = str(kid or "").strip()
    if not kid_s:
        raise SecurityError("kid é obrigatório para seleção de chave JWKS.")
    jwks = jwks_obter(
        url_jwks,
        cache_ttl_segundos=cache_ttl_segundos,
        timeout_segundos=timeout_segundos,
        forcar_refresh=False,
    )
    for chave in list(jwks.get("keys", [])):
        if str(dict(chave).get("kid") or "") == kid_s:
            return dict(chave)
    # tentativa de rotação automática
    jwks = jwks_obter(
        url_jwks,
        cache_ttl_segundos=cache_ttl_segundos,
        timeout_segundos=timeout_segundos,
        forcar_refresh=True,
    )
    for chave in list(jwks.get("keys", [])):
        if str(dict(chave).get("kid") or "") == kid_s:
            return dict(chave)
    raise SecurityError("chave JWKS não encontrada para o kid informado.")


def jwt_verificar_jwks(
    token: str,
    url_jwks: str,
    *,
    leeway_segundos: int = 0,
    emissor: str | None = None,
    audiencia: str | list[str] | None = None,
    cache_ttl_segundos: float = 300.0,
    timeout_segundos: float = 2.0,
) -> dict[str, Any]:
    cab = jwt_ler_cabecalho(token)
    alg = str(cab.get("alg") or "").upper()
    if alg != "RS256":
        raise SecurityError("jwt_verificar_jwks suporta apenas tokens RS256.")
    kid = str(cab.get("kid") or "").strip()
    if not kid:
        raise SecurityError("token RS256 sem 'kid' não pode ser validado por JWKS.")
    jwk = jwks_chave_por_kid(
        url_jwks,
        kid,
        cache_ttl_segundos=cache_ttl_segundos,
        timeout_segundos=timeout_segundos,
    )
    chave_publica_pem = jwt_publica_de_jwk(jwk)
    return jwt_verificar(
        token,
        segredo=chave_publica_pem,
        leeway_segundos=leeway_segundos,
        emissor=emissor,
        audiencia=audiencia,
    )
