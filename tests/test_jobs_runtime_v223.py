from __future__ import annotations

import asyncio

from trama.jobs_runtime import JobQueue, jobs_backends_listar


def test_v223_backend_memoria_disponivel_por_padrao() -> None:
    backends = jobs_backends_listar()
    assert "memoria" in backends


def test_v223_fila_status_indica_backend() -> None:
    def invoke(fn, args):
        return fn(*args)

    def job(payload):
        return payload["ok"]

    async def run():
        fila = JobQueue("v223_status", invoke_callable_sync=invoke, backend="memoria")
        await fila.enqueue(job, {"ok": True})
        await fila.process_all()
        return fila.status()

    st = asyncio.run(run())
    assert st["backend"] == "memoria"
    assert st["concluidos"] == 1
