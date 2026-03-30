from __future__ import annotations

from trama import social_runtime


def _reset_social() -> None:
    social_runtime._COMUNIDADES.clear()  # type: ignore[attr-defined]


def test_social_comunidade_canal_cargo_permissoes_e_moderacao() -> None:
    _reset_social()
    out_c = social_runtime.comunidade_criar("Guilda BR", "comunidade de testes")
    assert out_c["ok"] is True
    comunidade_id = str(out_c["id"])

    out_canal = social_runtime.canal_criar(comunidade_id, "geral", "texto")
    out_cargo = social_runtime.cargo_criar(comunidade_id, "moderador", ["mod:banir", "admin:*"])
    assert out_canal["ok"] is True
    assert out_cargo["ok"] is True

    assert social_runtime.membro_entrar(comunidade_id, "u1")["ok"] is True
    assert social_runtime.membro_atribuir_cargo(comunidade_id, "u1", str(out_cargo["id"]))["ok"] is True

    assert social_runtime.permissao_tem(comunidade_id, "u1", "mod:banir") is True
    assert social_runtime.permissao_tem(comunidade_id, "u1", "qualquer:coisa") is True

    assert social_runtime.moderacao_acao(comunidade_id, "mutar", "u1", "admin-1", "spam")["ok"] is True
    mods = social_runtime.moderacao_listar(comunidade_id)
    assert len(mods) >= 1
    assert mods[-1]["acao"] == "mutar"

