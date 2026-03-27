"""Builtins padrão da linguagem trama."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Callable
from pathlib import Path


def make_builtins(print_fn: Callable[[str], None] | None = None) -> dict[str, Callable[..., object]]:
    out = print_fn or print

    def _to_coroutine(awaitable: object):
        if inspect.iscoroutine(awaitable):
            return awaitable

        if inspect.isawaitable(awaitable):
            async def _wrapper():
                return await awaitable  # type: ignore[misc]

            return _wrapper()

        raise TypeError("valor não aguardável")

    def exibir(*args: object) -> None:
        out(" ".join(str(a) for a in args))
        return None

    def json_parse(payload: str) -> object:
        if not isinstance(payload, str):
            raise TypeError("json_parse espera texto")
        return json.loads(payload)

    def json_stringify(value: object) -> str:
        return json.dumps(value, ensure_ascii=False)

    def criar_tarefa(awaitable: object) -> object:
        return asyncio.create_task(_to_coroutine(awaitable))

    def cancelar_tarefa(task: object) -> None:
        task.cancel()  # type: ignore[attr-defined]
        return None

    async def dormir(segundos: float) -> None:
        await asyncio.sleep(segundos)
        return None

    async def com_timeout(awaitable: object, segundos: float) -> object:
        return await asyncio.wait_for(_to_coroutine(awaitable), timeout=segundos)

    async def ler_texto_async(caminho: str) -> str:
        path = Path(caminho)
        return await asyncio.to_thread(path.read_text, encoding="utf-8")

    async def escrever_texto_async(caminho: str, conteudo: str) -> None:
        path = Path(caminho)
        await asyncio.to_thread(path.write_text, conteudo, encoding="utf-8")
        return None

    return {
        "exibir": exibir,
        "json_parse": json_parse,
        "json_stringify": json_stringify,
        "criar_tarefa": criar_tarefa,
        "cancelar_tarefa": cancelar_tarefa,
        "dormir": dormir,
        "com_timeout": com_timeout,
        "ler_texto_async": ler_texto_async,
        "escrever_texto_async": escrever_texto_async,
    }
