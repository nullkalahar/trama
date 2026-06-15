from __future__ import annotations

from trama import security_runtime


def test_v222_fallback_rbac_sem_politica() -> None:
    modelo = security_runtime.rbac_criar({"editor": ["doc:editar"]})
    usuarios: dict[str, list[str]] = {}
    usuarios = security_runtime.rbac_atribuir(usuarios, "ana", "editor")
    out = security_runtime.autorizacao_avaliar(
        modelo,
        usuarios,
        "ana",
        "doc:editar",
        recurso={"tipo": "documento", "id": "d1"},
        contexto={"ambiente": "prod"},
    )
    assert out["permitido"] is True
    assert out["origem_decisao"] == "rbac"


def test_v222_politica_negar_sobrepoe_rbac() -> None:
    modelo = security_runtime.rbac_criar({"admin": ["usuario:apagar"]})
    usuarios: dict[str, list[str]] = {}
    usuarios = security_runtime.rbac_atribuir(usuarios, "bia", "admin")
    politicas = security_runtime.autorizacao_politicas_criar(
        [
            {
                "id": "bloquear_prod",
                "efeito": "negar",
                "ator": {"papeis": ["admin"]},
                "acao": "usuario:apagar",
                "contexto": {"ambiente": "producao"},
            }
        ],
        efeito_padrao="negar",
    )
    out = security_runtime.autorizacao_avaliar(
        modelo,
        usuarios,
        "bia",
        "usuario:apagar",
        recurso={"tipo": "usuario", "id": "u-10"},
        contexto={"ambiente": "producao"},
        politicas=politicas,
    )
    assert out["permitido"] is False
    assert out["origem_decisao"] == "politica_explicita"
    assert dict(out["resultado_politica"])["regra_id"] == "bloquear_prod"


def test_v222_politica_permitir_sem_rbac() -> None:
    modelo = security_runtime.rbac_criar({"viewer": ["doc:ler"]})
    usuarios: dict[str, list[str]] = {}
    politicas = security_runtime.autorizacao_politicas_criar(
        [
            {
                "id": "permitir_dono",
                "efeito": "permitir",
                "ator": {"ids": ["carlos"]},
                "acao": "doc:editar",
                "recurso": {"tipo": "documento"},
                "contexto": {"tenant": "t1"},
            }
        ],
        efeito_padrao="negar",
    )
    out = security_runtime.autorizacao_avaliar(
        modelo,
        usuarios,
        {"id": "carlos"},
        "doc:editar",
        recurso={"tipo": "documento", "id": "d-20"},
        contexto={"tenant": "t1"},
        politicas=politicas,
    )
    assert out["permitido"] is True
    assert out["origem_decisao"] == "politica_explicita"


def test_v222_politica_sem_match_retorna_efeito_padrao() -> None:
    politicas = security_runtime.autorizacao_politicas_criar([], efeito_padrao="permitir")
    out = security_runtime.autorizacao_politicas_avaliar(
        politicas,
        {"id": "u1", "papeis": ["guest"]},
        "recurso:ler",
        recurso={"tipo": "recurso", "id": "r1"},
        contexto={"tenant": "x"},
    )
    assert out["permitido"] is True
    assert out["decisao_explicita"] is False
    assert out["motivo"] == "efeito_padrao_politica"
