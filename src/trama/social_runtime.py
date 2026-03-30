"""Runtime social: comunidades, canais, cargos, moderação e permissões."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from . import observability_runtime

_LOCK = threading.Lock()
_COMUNIDADES: dict[str, dict[str, Any]] = {}


def _agora() -> float:
    return time.time()


def comunidade_criar(nome: str, descricao: str = "", visibilidade: str = "publica") -> dict[str, Any]:
    cid = uuid.uuid4().hex
    with _LOCK:
        _COMUNIDADES[cid] = {
            "id": cid,
            "nome": str(nome),
            "descricao": str(descricao),
            "visibilidade": str(visibilidade),
            "canais": {},
            "cargos": {},
            "membros": {},
            "moderacao": [],
            "criado_em": _agora(),
        }
    observability_runtime.registrar_runtime_metrica("social", "comunidade_criada", labels={"id": cid})
    return {"ok": True, "id": cid}


def comunidade_obter(comunidade_id: str) -> dict[str, Any]:
    with _LOCK:
        c = _COMUNIDADES.get(str(comunidade_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "COMUNIDADE_NAO_ENCONTRADA"}}
        return {"ok": True, "comunidade": c}


def comunidade_listar() -> list[dict[str, Any]]:
    with _LOCK:
        return [dict(v) for v in _COMUNIDADES.values()]


def canal_criar(comunidade_id: str, nome: str, tipo: str = "texto") -> dict[str, Any]:
    canal_id = uuid.uuid4().hex
    with _LOCK:
        c = _COMUNIDADES.get(str(comunidade_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "COMUNIDADE_NAO_ENCONTRADA"}}
        c["canais"][canal_id] = {
            "id": canal_id,
            "nome": str(nome),
            "tipo": str(tipo),
            "criado_em": _agora(),
            "permissoes": {},
        }
    observability_runtime.registrar_runtime_metrica("social", "canal_criado", labels={"comunidade_id": str(comunidade_id), "tipo": str(tipo)})
    return {"ok": True, "id": canal_id}


def cargo_criar(comunidade_id: str, nome: str, permissoes: list[str] | None = None) -> dict[str, Any]:
    cargo_id = uuid.uuid4().hex
    with _LOCK:
        c = _COMUNIDADES.get(str(comunidade_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "COMUNIDADE_NAO_ENCONTRADA"}}
        c["cargos"][cargo_id] = {
            "id": cargo_id,
            "nome": str(nome),
            "permissoes": sorted(set(str(p) for p in (permissoes or []))),
        }
    observability_runtime.registrar_runtime_metrica("social", "cargo_criado", labels={"comunidade_id": str(comunidade_id)})
    return {"ok": True, "id": cargo_id}


def membro_entrar(comunidade_id: str, usuario_id: str) -> dict[str, Any]:
    with _LOCK:
        c = _COMUNIDADES.get(str(comunidade_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "COMUNIDADE_NAO_ENCONTRADA"}}
        c["membros"].setdefault(str(usuario_id), {"cargos": [], "banido": False, "mutado": False, "entrou_em": _agora()})
    observability_runtime.registrar_runtime_metrica("social", "membro_entrou", labels={"comunidade_id": str(comunidade_id)})
    return {"ok": True}


def membro_sair(comunidade_id: str, usuario_id: str) -> dict[str, Any]:
    with _LOCK:
        c = _COMUNIDADES.get(str(comunidade_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "COMUNIDADE_NAO_ENCONTRADA"}}
        c["membros"].pop(str(usuario_id), None)
    observability_runtime.registrar_runtime_metrica("social", "membro_saiu", labels={"comunidade_id": str(comunidade_id)})
    return {"ok": True}


def membro_atribuir_cargo(comunidade_id: str, usuario_id: str, cargo_id: str) -> dict[str, Any]:
    with _LOCK:
        c = _COMUNIDADES.get(str(comunidade_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "COMUNIDADE_NAO_ENCONTRADA"}}
        m = c["membros"].get(str(usuario_id))
        if m is None:
            return {"ok": False, "erro": {"codigo": "MEMBRO_NAO_ENCONTRADO"}}
        if str(cargo_id) not in c["cargos"]:
            return {"ok": False, "erro": {"codigo": "CARGO_NAO_ENCONTRADO"}}
        cargos = set(m.get("cargos", []))
        cargos.add(str(cargo_id))
        m["cargos"] = sorted(cargos)
    return {"ok": True}


def permissao_tem(comunidade_id: str, usuario_id: str, permissao: str, canal_id: str | None = None) -> bool:
    with _LOCK:
        c = _COMUNIDADES.get(str(comunidade_id))
        if c is None:
            return False
        m = c["membros"].get(str(usuario_id))
        if m is None:
            return False
        if m.get("banido") is True:
            return False
        perms: set[str] = set()
        for cargo_id in list(m.get("cargos", [])):
            cargo = c["cargos"].get(cargo_id)
            if cargo:
                perms.update(set(cargo.get("permissoes", [])))
        if canal_id:
            canal = c["canais"].get(str(canal_id))
            if canal:
                over = canal.get("permissoes", {}).get(str(usuario_id), [])
                perms.update(set(over))
        return str(permissao) in perms or "admin:*" in perms


def moderacao_acao(comunidade_id: str, acao: str, usuario_id: str, ator_id: str, motivo: str = "") -> dict[str, Any]:
    with _LOCK:
        c = _COMUNIDADES.get(str(comunidade_id))
        if c is None:
            return {"ok": False, "erro": {"codigo": "COMUNIDADE_NAO_ENCONTRADA"}}
        if acao == "reportar":
            c["moderacao"].append({"acao": acao, "usuario_id": str(usuario_id), "ator_id": str(ator_id), "motivo": str(motivo), "ts": _agora()})
            return {"ok": True}
        m = c["membros"].get(str(usuario_id))
        if m is None:
            return {"ok": False, "erro": {"codigo": "MEMBRO_NAO_ENCONTRADO"}}
        if acao == "banir":
            m["banido"] = True
        elif acao == "mutar":
            m["mutado"] = True
        elif acao == "expulsar":
            c["membros"].pop(str(usuario_id), None)
        elif acao == "soft_delete":
            m["soft_delete"] = True
        else:
            return {"ok": False, "erro": {"codigo": "ACAO_INVALIDA"}}
        c["moderacao"].append({"acao": acao, "usuario_id": str(usuario_id), "ator_id": str(ator_id), "motivo": str(motivo), "ts": _agora()})
    observability_runtime.registrar_runtime_metrica("social", "moderacao", labels={"acao": str(acao), "comunidade_id": str(comunidade_id)})
    return {"ok": True}


def moderacao_listar(comunidade_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        c = _COMUNIDADES.get(str(comunidade_id))
        if c is None:
            return []
        return list(c.get("moderacao", []))
