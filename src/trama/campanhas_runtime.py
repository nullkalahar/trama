"""Runtime administrativo e campanhas push."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from . import observability_runtime

_LOCK = threading.Lock()
_CAMPANHAS: dict[str, dict[str, Any]] = {}
_AUDITORIA: list[dict[str, Any]] = []


def _agora() -> float:
    return time.time()


def auditoria_registrar(evento: str, ator_id: str, detalhes: dict[str, object] | None = None) -> dict[str, Any]:
    entry = {
        "id": uuid.uuid4().hex,
        "evento": str(evento),
        "ator_id": str(ator_id),
        "detalhes": dict(detalhes or {}),
        "ts": _agora(),
    }
    with _LOCK:
        _AUDITORIA.append(entry)
    observability_runtime.registrar_runtime_metrica("admin", "auditoria", labels={"evento": str(evento)})
    return {"ok": True, "id": entry["id"]}


def auditoria_listar(limite: int = 100) -> list[dict[str, Any]]:
    with _LOCK:
        return list(_AUDITORIA[-max(1, int(limite)) :])


def campanha_criar(nome: str, conteudo: dict[str, object], segmento: dict[str, object] | None = None) -> dict[str, Any]:
    cid = uuid.uuid4().hex
    obj = {
        "id": cid,
        "nome": str(nome),
        "conteudo": dict(conteudo),
        "segmento": dict(segmento or {}),
        "status": "rascunho",
        "agendada_em": None,
        "execucoes": [],
        "criado_em": _agora(),
    }
    with _LOCK:
        _CAMPANHAS[cid] = obj
    observability_runtime.registrar_runtime_metrica("campanha", "criada", labels={"id": cid})
    return {"ok": True, "id": cid}


def campanha_agendar(campanha_id: str, ts_execucao: float) -> dict[str, Any]:
    with _LOCK:
        c = _CAMPANHAS.get(str(campanha_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "CAMPANHA_NAO_ENCONTRADA"}}
        c["status"] = "agendada"
        c["agendada_em"] = float(ts_execucao)
    observability_runtime.registrar_runtime_metrica("campanha", "agendada", labels={"id": str(campanha_id)})
    return {"ok": True}


def campanha_executar(campanha_id: str, destinatarios: list[str]) -> dict[str, Any]:
    with _LOCK:
        c = _CAMPANHAS.get(str(campanha_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "CAMPANHA_NAO_ENCONTRADA"}}
        entrega = {
            "id": uuid.uuid4().hex,
            "ts": _agora(),
            "total": len(destinatarios),
            "enviados": len(destinatarios),
            "falhas": 0,
            "status": "concluida",
            "destinatarios": list(destinatarios),
        }
        c["status"] = "concluida"
        c["execucoes"].append(entrega)
    observability_runtime.registrar_runtime_metrica("campanha", "executada", valor=len(destinatarios), labels={"id": str(campanha_id)})
    return {"ok": True, "execucao": entrega}


def campanha_status(campanha_id: str) -> dict[str, Any]:
    with _LOCK:
        c = _CAMPANHAS.get(str(campanha_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "CAMPANHA_NAO_ENCONTRADA"}}
        return {"ok": True, "campanha": dict(c)}


def campanha_listar() -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(v) for v in _CAMPANHAS.values()]
