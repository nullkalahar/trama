from __future__ import annotations

import asyncio
from pathlib import Path

from trama.jobs_runtime import JobQueue


def test_v225_worker_externo_registra_handlers_e_processa_sql(tmp_path: Path) -> None:
    db_file = tmp_path / "jobs_worker.db"
    chamadas = {"n": 0}

    def invoke(fn, args):
        return fn(*args)

    def job(payload):
        chamadas["n"] += 1
        return payload["ok"]

    async def run() -> tuple[dict[str, object], dict[str, object]]:
        produtor = JobQueue(
            "v225_worker",
            invoke_callable_sync=invoke,
            backend="sql",
            backend_opcoes={"dsn": f"sqlite:///{db_file}"},
        )
        await produtor.enqueue(job, {"ok": True}, retries=1, idempotency_key="job-1")

        worker = JobQueue(
            "v225_worker",
            invoke_callable_sync=invoke,
            backend="sql",
            backend_opcoes={"dsn": f"sqlite:///{db_file}"},
        )
        reg = worker.handlers_registrar({"job": job})
        assert reg["handlers_registrados"] == 1
        resultado = await worker.process_all()
        status = await worker.refresh_status()
        return resultado, status

    resultado, status = asyncio.run(run())
    assert resultado["processados"] == 1
    assert status["concluidos"] == 1
    assert chamadas["n"] == 1


def test_v225_status_sql_recarrega_do_banco(tmp_path: Path) -> None:
    db_file = tmp_path / "jobs_status.db"

    def invoke(fn, args):
        return fn(*args)

    def job(payload):
        return payload["id"]

    async def run() -> dict[str, object]:
        produtor = JobQueue(
            "v225_status",
            invoke_callable_sync=invoke,
            backend="sql",
            backend_opcoes={"dsn": f"sqlite:///{db_file}"},
        )
        await produtor.enqueue(job, {"id": 1}, retries=1, idempotency_key="status-1")

        leitor = JobQueue(
            "v225_status",
            backend="sql",
            backend_opcoes={"dsn": f"sqlite:///{db_file}"},
        )
        return await leitor.refresh_status()

    status = asyncio.run(run())
    assert status["pendentes"] == 1
    assert status["concluidos"] == 0
