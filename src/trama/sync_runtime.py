"""Runtime de sincronização incremental e cache offline."""

from __future__ import annotations

import threading
import time
from typing import Any

from . import observability_runtime

_LOCK = threading.Lock()
_EVENTOS: dict[str, list[dict[str, Any]]] = {}
_CACHE_OFFLINE: dict[str, dict[str, dict[str, Any]]] = {}


def _agora() -> float:
    return time.time()


def sync_registrar_evento(colecao: str, entidade_id: str, operacao: str, dados: dict[str, object], origem: str = "servidor") -> dict[str, Any]:
    with _LOCK:
        eventos = _EVENTOS.setdefault(str(colecao), [])
        cursor = len(eventos) + 1
        ev = {
            "cursor": cursor,
            "colecao": str(colecao),
            "entidade_id": str(entidade_id),
            "operacao": str(operacao),
            "dados": dict(dados),
            "origem": str(origem),
            "ts": _agora(),
        }
        eventos.append(ev)
    observability_runtime.registrar_runtime_metrica("sync", "evento", labels={"colecao": str(colecao), "operacao": str(operacao)})
    return {"ok": True, "cursor": cursor}


def sync_consumir(colecao: str, cursor_desde: int = 0, limite: int = 100) -> dict[str, Any]:
    with _LOCK:
        eventos = list(_EVENTOS.get(str(colecao), []))
    itens = [e for e in eventos if int(e.get("cursor", 0)) > int(cursor_desde)]
    itens = itens[: max(1, int(limite))]
    cursor_ate = int(cursor_desde)
    if itens:
        cursor_ate = int(itens[-1]["cursor"])
    return {"ok": True, "itens": itens, "cursor_desde": int(cursor_desde), "cursor_ate": cursor_ate}


def sync_cursor_atual(colecao: str) -> int:
    with _LOCK:
        eventos = _EVENTOS.get(str(colecao), [])
        return int(eventos[-1]["cursor"]) if eventos else 0


def sync_resolver_conflito(local: dict[str, object], remoto: dict[str, object], estrategia: str = "last_write_wins") -> dict[str, Any]:
    if estrategia == "last_write_wins":
        ts_local = float(local.get("atualizado_em", 0.0) or 0.0)
        ts_remoto = float(remoto.get("atualizado_em", 0.0) or 0.0)
        vencedor = remoto if ts_remoto >= ts_local else local
        return {"ok": True, "estrategia": estrategia, "vencedor": dict(vencedor)}
    if estrategia == "local":
        return {"ok": True, "estrategia": estrategia, "vencedor": dict(local)}
    if estrategia == "remoto":
        return {"ok": True, "estrategia": estrategia, "vencedor": dict(remoto)}
    return {"ok": False, "erro": {"codigo": "ESTRATEGIA_INVALIDA"}}


def cache_offline_salvar(namespace: str, chave: str, valor: object, versao: int | None = None) -> dict[str, Any]:
    ns = str(namespace)
    with _LOCK:
        bucket = _CACHE_OFFLINE.setdefault(ns, {})
        atual = bucket.get(str(chave), {})
        v = int(versao) if versao is not None else int(atual.get("versao", 0)) + 1
        bucket[str(chave)] = {"valor": valor, "versao": v, "atualizado_em": _agora()}
    observability_runtime.registrar_runtime_metrica("sync", "cache_offline_salvar", labels={"namespace": ns})
    return {"ok": True, "versao": v}


def cache_offline_obter(namespace: str, chave: str) -> dict[str, Any]:
    ns = str(namespace)
    with _LOCK:
        bucket = _CACHE_OFFLINE.get(ns, {})
        if str(chave) not in bucket:
            return {"ok": False, "erro": {"codigo": "CHAVE_NAO_ENCONTRADA"}}
        item = dict(bucket[str(chave)])
    return {"ok": True, "item": item}


def cache_offline_listar(namespace: str) -> dict[str, Any]:
    ns = str(namespace)
    with _LOCK:
        bucket = {k: dict(v) for k, v in _CACHE_OFFLINE.get(ns, {}).items()}
    return {"ok": True, "itens": bucket}
