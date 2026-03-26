"""Estruturas base de token para o lexer da trama."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    tipo: str
    lexema: str
    linha: int
    coluna: int
