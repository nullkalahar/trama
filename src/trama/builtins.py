"""Builtins padrão da linguagem trama."""

from __future__ import annotations

import json
from collections.abc import Callable


def make_builtins(print_fn: Callable[[str], None] | None = None) -> dict[str, Callable[..., object]]:
    out = print_fn or print

    def exibir(*args: object) -> None:
        out(" ".join(str(a) for a in args))
        return None

    def json_parse(payload: str) -> object:
        if not isinstance(payload, str):
            raise TypeError("json_parse espera texto")
        return json.loads(payload)

    def json_stringify(value: object) -> str:
        return json.dumps(value, ensure_ascii=False)

    return {
        "exibir": exibir,
        "json_parse": json_parse,
        "json_stringify": json_stringify,
    }
