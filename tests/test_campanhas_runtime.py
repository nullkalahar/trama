from __future__ import annotations

import time

from trama import campanhas_runtime


def _reset_campanhas() -> None:
    campanhas_runtime._CAMPANHAS.clear()  # type: ignore[attr-defined]
    campanhas_runtime._AUDITORIA.clear()  # type: ignore[attr-defined]


def test_admin_auditoria_e_campanhas_push() -> None:
    _reset_campanhas()
    out_a = campanhas_runtime.auditoria_registrar("login_admin", "admin-1", {"ip": "127.0.0.1"})
    assert out_a["ok"] is True
    audit = campanhas_runtime.auditoria_listar(10)
    assert len(audit) == 1
    assert audit[0]["evento"] == "login_admin"

    out_c = campanhas_runtime.campanha_criar(
        "Boas-vindas",
        {"titulo": "Olá", "corpo": "Bem-vindo"},
        {"pais": "BR"},
    )
    assert out_c["ok"] is True
    campanha_id = str(out_c["id"])

    out_s = campanhas_runtime.campanha_agendar(campanha_id, time.time() + 60.0)
    assert out_s["ok"] is True

    out_e = campanhas_runtime.campanha_executar(campanha_id, ["u1", "u2", "u3"])
    assert out_e["ok"] is True
    assert out_e["execucao"]["enviados"] == 3

    st = campanhas_runtime.campanha_status(campanha_id)
    assert st["ok"] is True
    assert st["campanha"]["status"] == "concluida"

