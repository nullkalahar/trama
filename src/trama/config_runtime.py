"""Runtime de configuração e segredos (v1.1)."""

from __future__ import annotations

import json
import os
from typing import Any


class ConfigError(RuntimeError):
    """Erro de configuração/segredos."""


def _parse_env_value(value: str) -> object:
    lowered = value.strip().lower()
    if lowered in {"verdadeiro", "true"}:
        return True
    if lowered in {"falso", "false"}:
        return False
    if lowered in {"nulo", "null"}:
        return None

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _validar_tipo(nome: str, valor: object, tipo_esperado: str) -> None:
    t = tipo_esperado.strip().lower()
    if t == "texto" and isinstance(valor, str):
        return
    if t == "inteiro" and isinstance(valor, int) and not isinstance(valor, bool):
        return
    if t == "real" and isinstance(valor, float):
        return
    if t == "numero" and isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return
    if t == "logico" and isinstance(valor, bool):
        return
    if t == "mapa" and isinstance(valor, dict):
        return
    if t == "lista" and isinstance(valor, list):
        return
    if t == "nulo" and valor is None:
        return
    raise ConfigError(f"Campo '{nome}' inválido: esperado tipo '{tipo_esperado}', recebido '{type(valor).__name__}'.")


def config_validar(
    config: dict[str, object],
    obrigatorios: list[str] | None = None,
    schema: dict[str, str] | None = None,
) -> dict[str, object]:
    if not isinstance(config, dict):
        raise ConfigError("config_validar espera mapa no primeiro argumento.")

    faltando: list[str] = []
    for campo in list(obrigatorios or []):
        if campo not in config or config.get(campo) is None:
            faltando.append(str(campo))
    if faltando:
        raise ConfigError(f"Configuração inválida: campos obrigatórios ausentes: {', '.join(sorted(faltando))}.")

    for campo, tipo in dict(schema or {}).items():
        if campo in config:
            _validar_tipo(campo, config[campo], str(tipo))

    return {"ok": True, "campos": sorted(config.keys())}


def config_carregar_ambiente(
    padrao: dict[str, object],
    prefixo: str = "TRAMA_",
    obrigatorios: list[str] | None = None,
    schema: dict[str, str] | None = None,
) -> dict[str, object]:
    if not isinstance(padrao, dict):
        raise ConfigError("config_carregar_ambiente espera mapa no primeiro argumento.")

    cfg = dict(padrao)
    for key, value in os.environ.items():
        if not key.startswith(prefixo):
            continue
        field = key[len(prefixo) :].lower()
        cfg[field] = _parse_env_value(value)

    _ = config_validar(cfg, obrigatorios=obrigatorios, schema=schema)
    return cfg


def segredo_obter(
    nome: str,
    padrao: object | None = None,
    obrigatorio: bool = False,
    permitir_vazio: bool = False,
) -> object:
    if not isinstance(nome, str) or not nome:
        raise ConfigError("segredo_obter exige nome não vazio.")
    valor = os.getenv(nome)
    if valor is None:
        if obrigatorio:
            raise ConfigError(f"Segredo obrigatório ausente: {nome}")
        return padrao
    if valor == "" and not permitir_vazio:
        raise ConfigError(f"Segredo '{nome}' vazio não é permitido.")
    return valor


def segredo_mascarar(valor: object, visivel: int = 2) -> str:
    texto = str(valor)
    if visivel < 0:
        visivel = 0
    if len(texto) <= visivel:
        return "*" * len(texto)
    return ("*" * (len(texto) - visivel)) + texto[-visivel:]
