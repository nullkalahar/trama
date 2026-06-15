"""Módulo de RBAC."""

from __future__ import annotations


def rbac_criar(
    papeis_permissoes: dict[str, list[str]],
    heranca_papeis: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    return {
        "papeis_permissoes": {
            str(p): sorted(set(str(x) for x in perms))
            for p, perms in dict(papeis_permissoes).items()
        },
        "heranca_papeis": {
            str(p): sorted(set(str(x) for x in pais))
            for p, pais in dict(heranca_papeis or {}).items()
        },
    }


def rbac_atribuir(
    usuarios_papeis: dict[str, list[str]],
    usuario: str,
    papel: str,
) -> dict[str, list[str]]:
    out = {str(u): list(v) for u, v in dict(usuarios_papeis).items()}
    papeis = set(out.get(usuario, []))
    papeis.add(papel)
    out[usuario] = sorted(papeis)
    return out


def rbac_papeis_usuario(usuarios_papeis: dict[str, list[str]], usuario: str) -> list[str]:
    return list(dict(usuarios_papeis).get(usuario, []))


def _rbac_expandir_papeis(modelo: dict[str, object], papeis: list[str]) -> set[str]:
    heranca = dict(modelo.get("heranca_papeis", {}))
    visitados: set[str] = set()
    pilha = list(papeis)
    while pilha:
        atual = str(pilha.pop())
        if atual in visitados:
            continue
        visitados.add(atual)
        for pai in list(heranca.get(atual, [])):
            pilha.append(str(pai))
    return visitados


def rbac_tem_papel(usuarios_papeis: dict[str, list[str]], usuario: str, papel: str) -> bool:
    return papel in set(rbac_papeis_usuario(usuarios_papeis, usuario))


def rbac_tem_permissao(
    modelo: dict[str, object],
    usuarios_papeis: dict[str, list[str]],
    usuario: str,
    permissao: str,
) -> bool:
    papeis_base = rbac_papeis_usuario(usuarios_papeis, usuario)
    papeis = _rbac_expandir_papeis(modelo, papeis_base)
    papeis_permissoes = dict(modelo.get("papeis_permissoes", {}))
    for papel in papeis:
        if permissao in set(list(papeis_permissoes.get(papel, []))):
            return True
    return False


def autorizacao_avaliar(
    modelo_rbac: dict[str, object],
    usuarios_papeis: dict[str, list[str]],
    ator: str | dict[str, object],
    acao: str,
    recurso: dict[str, object] | None = None,
    contexto: dict[str, object] | None = None,
    politicas: dict[str, object] | None = None,
) -> dict[str, object]:
    ator_obj = dict(ator) if isinstance(ator, dict) else {"id": str(ator)}
    ator_id = str(ator_obj.get("id") or ator_obj.get("id_usuario") or ator_obj.get("usuario") or "")
    papeis_informados = [str(x) for x in list(ator_obj.get("papeis") or [])]
    papeis_rbac = rbac_papeis_usuario(usuarios_papeis, ator_id) if ator_id else []
    papeis = sorted(set(papeis_informados + papeis_rbac))
    permitido_rbac = rbac_tem_permissao(modelo_rbac, usuarios_papeis, ator_id, acao) if ator_id else False

    resultado_politica: dict[str, object] | None = None
    if politicas is not None:
        from .politicas import autorizacao_politicas_avaliar

        resultado_politica = autorizacao_politicas_avaliar(
            politicas,
            {"id": ator_id, "papeis": papeis},
            acao,
            recurso=recurso,
            contexto=contexto,
        )

    if resultado_politica and bool(resultado_politica.get("decisao_explicita")):
        permitido_final = bool(resultado_politica.get("permitido"))
        origem = "politica_explicita"
    else:
        permitido_final = bool(permitido_rbac)
        origem = "rbac"

    return {
        "ok": True,
        "permitido": permitido_final,
        "origem_decisao": origem,
        "ator_id": ator_id,
        "acao": str(acao),
        "papeis": papeis,
        "permitido_rbac": bool(permitido_rbac),
        "resultado_politica": dict(resultado_politica or {}),
    }
