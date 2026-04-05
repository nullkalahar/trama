from __future__ import annotations

import time

import pytest

from trama import security_runtime


def test_v205_refresh_rotation_reuso_e_revogacao_sessao() -> None:
    s = security_runtime.sessao_criar("u_v205", "d1", ttl_refresh_segundos=120)
    sid = str(s["id_sessao"])

    refresh_1 = security_runtime.refresh_token_emitir(
        id_usuario="u_v205",
        segredo="seg-v205",
        id_sessao=sid,
        id_dispositivo="d1",
        exp_segundos=120,
    )
    troca = security_runtime.refresh_token_trocar(refresh_1, "seg-v205", exp_segundos=120)
    assert troca["ok"] is True
    assert security_runtime.token_esta_bloqueado(refresh_1) is True

    with pytest.raises(security_runtime.SecurityError, match="refresh_reuso_detectado"):
        security_runtime.refresh_token_trocar(refresh_1, "seg-v205", exp_segundos=120)

    assert security_runtime.sessao_ativa(sid) is False


def test_v205_revogacao_por_sessao_dispositivo_e_usuario() -> None:
    s1 = security_runtime.sessao_criar("u_v205_2", "d1", ttl_refresh_segundos=120)
    s2 = security_runtime.sessao_criar("u_v205_2", "d1", ttl_refresh_segundos=120)
    s3 = security_runtime.sessao_criar("u_v205_2", "d2", ttl_refresh_segundos=120)

    out_disp = security_runtime.sessao_revogar_dispositivo("u_v205_2", "d1")
    assert out_disp["ok"] is True
    assert int(out_disp["revogadas"]) >= 2
    assert security_runtime.sessao_ativa(str(s1["id_sessao"])) is False
    assert security_runtime.sessao_ativa(str(s2["id_sessao"])) is False
    assert security_runtime.sessao_ativa(str(s3["id_sessao"])) is True

    out_usr = security_runtime.sessao_revogar_usuario("u_v205_2")
    assert out_usr["ok"] is True
    assert int(out_usr["revogadas"]) >= 1
    assert security_runtime.sessao_ativa(str(s3["id_sessao"])) is False


def test_v205_denylist_ttl_e_limpeza() -> None:
    tok = security_runtime.jwt_criar({"sub": "u_v205_deny"}, "seg-v205", exp_segundos=300)
    out = security_runtime.token_bloquear(tok, ttl_segundos=1, motivo="teste")
    assert out["ok"] is True
    assert security_runtime.token_esta_bloqueado(tok) is True

    time.sleep(1.1)
    assert security_runtime.token_esta_bloqueado(tok) is False
    assert security_runtime.token_denylist_limpar_expirados() >= 0


def test_v205_rate_limit_distribuido_memoria_multinstancia() -> None:
    grupo = f"g_v205_rl_{int(time.time() * 1000)}"
    a = security_runtime.rate_limit_distribuido_obter_instancia(grupo=grupo, id_instancia="a", backend="memoria")
    b = security_runtime.rate_limit_distribuido_obter_instancia(grupo=grupo, id_instancia="b", backend="memoria")

    r1 = a.permitir("rota:GET:/x", max_requisicoes=3, janela_segundos=10)
    r2 = b.permitir("rota:GET:/x", max_requisicoes=3, janela_segundos=10)
    r3 = a.permitir("rota:GET:/x", max_requisicoes=3, janela_segundos=10)
    r4 = b.permitir("rota:GET:/x", max_requisicoes=3, janela_segundos=10)

    assert r1["permitido"] is True
    assert r2["permitido"] is True
    assert r3["permitido"] is True
    assert r4["permitido"] is False


def test_v205_auditoria_registro_consulta() -> None:
    out = security_runtime.auditoria_seguranca_registrar(
        ator="admin-v205",
        acao="usuario_remover",
        alvo="u-11",
        resultado="sucesso",
        id_requisicao="req-1",
        id_traco="tr-1",
        origem="127.0.0.1",
        detalhes={"motivo": "abuso"},
    )
    assert out["ok"] is True
    eventos = security_runtime.auditoria_seguranca_listar(limite=10, acao="usuario_remover")
    assert len(eventos) >= 1
    assert eventos[0]["acao"] == "usuario_remover"
    assert set(["ator", "acao", "alvo", "timestamp", "resultado", "id_requisicao", "id_traco", "origem"]).issubset(
        eventos[0].keys()
    )
