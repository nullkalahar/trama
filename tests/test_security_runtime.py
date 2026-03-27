from __future__ import annotations

import time

import pytest

from trama import security_runtime


def test_jwt_criar_verificar() -> None:
    token = security_runtime.jwt_criar({"sub": "u1", "role": "admin"}, "segredo", exp_segundos=60)
    payload = security_runtime.jwt_verificar(token, "segredo")
    assert payload["sub"] == "u1"
    assert payload["role"] == "admin"
    assert "iat" in payload
    assert "exp" in payload


def test_jwt_expirado() -> None:
    token = security_runtime.jwt_criar({"sub": "u1"}, "segredo", exp_segundos=1)
    time.sleep(2.1)
    with pytest.raises(security_runtime.SecurityError, match="expirado"):
        security_runtime.jwt_verificar(token, "segredo")


def test_senha_hash_pbkdf2_e_verificar() -> None:
    h = security_runtime.senha_hash("senha-forte", "pbkdf2")
    assert h.startswith("pbkdf2$")
    assert security_runtime.senha_verificar("senha-forte", h) is True
    assert security_runtime.senha_verificar("senha-ruim", h) is False


def test_rbac_permissoes_com_heranca() -> None:
    modelo = security_runtime.rbac_criar(
        {
            "viewer": ["ler"],
            "editor": ["editar"],
            "admin": ["apagar"],
        },
        {"editor": ["viewer"], "admin": ["editor"]},
    )
    users: dict[str, list[str]] = {}
    users = security_runtime.rbac_atribuir(users, "ana", "admin")

    assert security_runtime.rbac_tem_papel(users, "ana", "admin") is True
    assert security_runtime.rbac_tem_permissao(modelo, users, "ana", "apagar") is True
    assert security_runtime.rbac_tem_permissao(modelo, users, "ana", "editar") is True
    assert security_runtime.rbac_tem_permissao(modelo, users, "ana", "ler") is True
