"""Builtins padrão da linguagem trama."""

from __future__ import annotations

from collections.abc import Callable


def make_builtins(print_fn: Callable[[str], None] | None = None) -> dict[str, Callable[..., object]]:
    out = print_fn or print

    def exibir(*args: object) -> None:
        out(" ".join(str(a) for a in args))
        return None

    return {"exibir": exibir}
