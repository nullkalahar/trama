from __future__ import annotations

import os

import pytest

from trama import config_runtime


def test_config_carregar_ambiente_com_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRAMA_HOST", "localhost")
    monkeypatch.setenv("TRAMA_PORTA", "8080")
    monkeypatch.setenv("TRAMA_DEBUG", "verdadeiro")
    cfg = config_runtime.config_carregar_ambiente(
        {"host": "127.0.0.1", "porta": 3000, "debug": False},
        prefixo="TRAMA_",
        obrigatorios=["host", "porta"],
        schema={"host": "texto", "porta": "inteiro", "debug": "logico"},
    )
    assert cfg["host"] == "localhost"
    assert cfg["porta"] == 8080
    assert cfg["debug"] is True


def test_config_validar_obrigatorio_falha() -> None:
    with pytest.raises(config_runtime.ConfigError, match="obrigatórios ausentes"):
        config_runtime.config_validar({"a": 1}, obrigatorios=["a", "b"])


def test_segredo_obter_e_mascarar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRAMA_TOKEN", "abcdef123456")
    token = config_runtime.segredo_obter("TRAMA_TOKEN", obrigatorio=True)
    assert token == "abcdef123456"
    assert config_runtime.segredo_mascarar(token, visivel=4).endswith("3456")
    assert "*" in config_runtime.segredo_mascarar(token, visivel=4)


def test_segredo_obrigatorio_ausente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRAMA_NAO_EXISTE", raising=False)
    with pytest.raises(config_runtime.ConfigError, match="obrigatório ausente"):
        config_runtime.segredo_obter("TRAMA_NAO_EXISTE", obrigatorio=True)


def test_segredo_vazio_rejeitado(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRAMA_VAZIO", "")
    with pytest.raises(config_runtime.ConfigError, match="vazio"):
        _ = config_runtime.segredo_obter("TRAMA_VAZIO")
    assert config_runtime.segredo_obter("TRAMA_VAZIO", permitir_vazio=True) == ""
