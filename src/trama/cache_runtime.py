"""Runtime de cache em memória com TTL e invalidação por padrão (v1.1)."""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import threading
import time
from typing import Any

from . import observability_runtime

@dataclass
class _Entry:
    value: object
    created_at: float
    expire_at: float | None


_LOCK = threading.RLock()
_STORES: dict[str, dict[str, _Entry]] = {}
_STATS: dict[str, dict[str, int]] = {}


def _ns(namespace: str | None) -> str:
    return (namespace or "padrao").strip() or "padrao"


def _ensure_namespace(namespace: str) -> None:
    if namespace not in _STORES:
        _STORES[namespace] = {}
    if namespace not in _STATS:
        _STATS[namespace] = {"hits": 0, "misses": 0, "expirados": 0}


def _is_expired(entry: _Entry, now: float) -> bool:
    return entry.expire_at is not None and entry.expire_at <= now


def cache_definir(
    chave: str,
    valor: object,
    ttl_segundos: float | None = None,
    namespace: str = "padrao",
) -> object:
    ns = _ns(namespace)
    if not isinstance(chave, str) or not chave:
        raise ValueError("cache_definir exige chave texto não vazia.")
    expire_at = None if ttl_segundos is None else (time.monotonic() + float(ttl_segundos))
    with _LOCK:
        _ensure_namespace(ns)
        _STORES[ns][chave] = _Entry(value=valor, created_at=time.monotonic(), expire_at=expire_at)
    observability_runtime.registrar_runtime_metrica("cache", "definir", labels={"namespace": ns})
    return valor


def cache_obter(
    chave: str,
    padrao: object | None = None,
    namespace: str = "padrao",
) -> object:
    ns = _ns(namespace)
    now = time.monotonic()
    with _LOCK:
        _ensure_namespace(ns)
        entry = _STORES[ns].get(chave)
        if entry is None:
            _STATS[ns]["misses"] += 1
            observability_runtime.registrar_runtime_metrica("cache", "miss", labels={"namespace": ns})
            return padrao
        if _is_expired(entry, now):
            _STATS[ns]["expirados"] += 1
            _STATS[ns]["misses"] += 1
            _STORES[ns].pop(chave, None)
            observability_runtime.registrar_runtime_metrica("cache", "expirado", labels={"namespace": ns})
            return padrao
        _STATS[ns]["hits"] += 1
        observability_runtime.registrar_runtime_metrica("cache", "hit", labels={"namespace": ns})
        return entry.value


def cache_existe(chave: str, namespace: str = "padrao") -> bool:
    sentinel = object()
    return cache_obter(chave, sentinel, namespace=namespace) is not sentinel


def cache_remover(chave: str, namespace: str = "padrao") -> bool:
    ns = _ns(namespace)
    with _LOCK:
        _ensure_namespace(ns)
        removed = _STORES[ns].pop(chave, None) is not None
    observability_runtime.registrar_runtime_metrica("cache", "remover", labels={"namespace": ns, "removido": str(removed).lower()})
    return removed


def cache_invalidar_padrao(padrao: str, namespace: str = "padrao") -> int:
    ns = _ns(namespace)
    if not isinstance(padrao, str) or not padrao:
        raise ValueError("cache_invalidar_padrao exige padrão texto não vazio.")
    with _LOCK:
        _ensure_namespace(ns)
        keys = [k for k in _STORES[ns] if fnmatch.fnmatch(k, padrao)]
        for key in keys:
            _STORES[ns].pop(key, None)
        total = len(keys)
    observability_runtime.registrar_runtime_metrica("cache", "invalidar_padrao", valor=float(total), labels={"namespace": ns})
    return total


def cache_limpar(namespace: str | None = None) -> int:
    with _LOCK:
        if namespace is None:
            total = sum(len(v) for v in _STORES.values())
            _STORES.clear()
            _STATS.clear()
            return total
        ns = _ns(namespace)
        _ensure_namespace(ns)
        total = len(_STORES[ns])
        _STORES[ns].clear()
        _STATS[ns] = {"hits": 0, "misses": 0, "expirados": 0}
        return total


def cache_aquecer(
    itens: dict[str, object] | list[dict[str, object]] | list[list[object]] | list[tuple[object, ...]],
    ttl_segundos: float | None = None,
    namespace: str = "padrao",
) -> int:
    total = 0
    if isinstance(itens, dict):
        for chave, valor in itens.items():
            cache_definir(str(chave), valor, ttl_segundos=ttl_segundos, namespace=namespace)
            total += 1
        return total

    if not isinstance(itens, list):
        raise ValueError("cache_aquecer espera mapa ou lista.")

    for item in itens:
        if isinstance(item, dict):
            chave = str(item.get("chave"))
            valor = item.get("valor")
            ttl = item.get("ttl_segundos", ttl_segundos)
            cache_definir(chave, valor, ttl_segundos=None if ttl is None else float(ttl), namespace=namespace)
            total += 1
            continue
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            chave = str(item[0])
            valor = item[1]
            ttl = float(item[2]) if len(item) >= 3 and item[2] is not None else ttl_segundos
            cache_definir(chave, valor, ttl_segundos=ttl, namespace=namespace)
            total += 1
            continue
        raise ValueError("Item inválido em cache_aquecer; use mapa {'chave','valor'} ou tupla (chave, valor, ttl?).")
    return total


def cache_stats(namespace: str = "padrao") -> dict[str, Any]:
    ns = _ns(namespace)
    now = time.monotonic()
    with _LOCK:
        _ensure_namespace(ns)
        expiradas: list[str] = []
        for key, entry in _STORES[ns].items():
            if _is_expired(entry, now):
                expiradas.append(key)
        for key in expiradas:
            _STATS[ns]["expirados"] += 1
            _STORES[ns].pop(key, None)

        return {
            "namespace": ns,
            "itens": len(_STORES[ns]),
            "hits": _STATS[ns]["hits"],
            "misses": _STATS[ns]["misses"],
            "expirados": _STATS[ns]["expirados"],
        }
