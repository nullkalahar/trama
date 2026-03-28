from __future__ import annotations

import asyncio

from trama import resiliencia_runtime


def test_resiliencia_retry_ate_sucesso() -> None:
    resiliencia_runtime.circuito_reset("svc-a")
    contador = {"n": 0}

    async def operacao():
        contador["n"] += 1
        if contador["n"] < 3:
            raise RuntimeError("falha transitória")
        return "ok"

    out = asyncio.run(
        resiliencia_runtime.executar(
            "svc-a",
            operacao,
            tentativas=5,
            base_backoff_segundos=0.001,
            jitter_segundos=0.0,
        )
    )
    assert out == "ok"
    assert contador["n"] == 3


def test_resiliencia_circuito_abre() -> None:
    resiliencia_runtime.circuito_reset("svc-b")

    async def sempre_falha():
        raise RuntimeError("indisponível")

    try:
        asyncio.run(
            resiliencia_runtime.executar(
                "svc-b",
                sempre_falha,
                tentativas=1,
                max_falhas=1,
                reset_timeout_segundos=0.2,
            )
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("esperava RuntimeError")

    status = resiliencia_runtime.circuito_status("svc-b")
    assert status["estado"] == "aberto"

    try:
        asyncio.run(
            resiliencia_runtime.executar(
                "svc-b",
                sempre_falha,
                tentativas=1,
                max_falhas=1,
                reset_timeout_segundos=0.2,
            )
        )
    except resiliencia_runtime.CircuitoAbertoError:
        pass
    else:
        raise AssertionError("esperava CircuitoAbertoError")


def test_resiliencia_timeout() -> None:
    resiliencia_runtime.circuito_reset("svc-c")

    async def lenta():
        await asyncio.sleep(0.05)
        return 1

    try:
        asyncio.run(
            resiliencia_runtime.executar(
                "svc-c",
                lenta,
                tentativas=1,
                timeout_segundos=0.001,
            )
        )
    except asyncio.TimeoutError:
        pass
    else:
        raise AssertionError("esperava TimeoutError")
