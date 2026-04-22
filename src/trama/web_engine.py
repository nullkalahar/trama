"""Contratos e engine padrão do runtime web."""

from __future__ import annotations

from typing import Callable, Protocol


class EngineRuntimeHttp(Protocol):
    @property
    def nome(self) -> str:
        """Identificador da engine HTTP."""

    def iniciar(self) -> None:
        """Inicia a engine HTTP."""

    def parar(self) -> None:
        """Interrompe a engine HTTP."""


class EngineHttpServerLegado:
    """Engine padrão baseada em callbacks do runtime legado."""

    def __init__(self, iniciar: Callable[[], None], parar: Callable[[], None]) -> None:
        self._iniciar = iniciar
        self._parar = parar

    @property
    def nome(self) -> str:
        return "legada"

    def iniciar(self) -> None:
        self._iniciar()

    def parar(self) -> None:
        self._parar()


class EngineHttpAsgiReal:
    """Engine ASGI real com callback de ciclo de vida."""

    def __init__(self, iniciar: Callable[[], None], parar: Callable[[], None]) -> None:
        self._iniciar = iniciar
        self._parar = parar

    @property
    def nome(self) -> str:
        return "asgi"

    def iniciar(self) -> None:
        self._iniciar()

    def parar(self) -> None:
        self._parar()
