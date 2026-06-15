from __future__ import annotations

import asyncio
from pathlib import Path

from trama.jobs_runtime import JobQueue, jobs_backends_listar


def test_v224_backend_sql_disponivel_por_padrao() -> None:
    backends = jobs_backends_listar()
    assert "sql" in backends


def test_v224_fila_sql_sucesso_idempotencia(tmp_path: Path) -> None:
    db_file = tmp_path / "jobs_ok.db"
    chamadas = {"n": 0}

    def invoke(fn, args):
        return fn(*args)

    def job(payload):
        chamadas["n"] += 1
        return payload["x"] + 1

    async def run():
        fila = JobQueue(
            "v224_ok",
            invoke_callable_sync=invoke,
            backend="sql",
            backend_opcoes={"dsn": f"sqlite:///{db_file}"},
        )
        a = await fila.enqueue(job, {"x": 1}, retries=1, idempotency_key="idem-1")
        b = await fila.enqueue(job, {"x": 1}, retries=1, idempotency_key="idem-1")
        out = await fila.process_all()
        job_publico = await fila.get_job(str(a["id"]))
        return a, b, out, fila.status(), job_publico

    a, b, out, st, job_publico = asyncio.run(run())
    assert a["enfileirado"] is True
    assert b["idempotente"] is True
    assert out["backend"] == "sql"
    assert out["concluidos"] == 1
    assert st["concluidos"] == 1
    assert chamadas["n"] == 1
    assert job_publico is not None
    assert job_publico["status"] == "concluido"
    assert job_publico["payload"] == {"x": 1}


def test_v224_fila_sql_dlq_reprocessamento(tmp_path: Path) -> None:
    db_file = tmp_path / "jobs_dlq.db"
    chamadas = {"n": 0}

    def invoke(fn, args):
        return fn(*args)

    def falhar(payload):
        chamadas["n"] += 1
        raise RuntimeError(f"erro:{payload['id']}")

    async def run():
        fila = JobQueue(
            "v224_dlq",
            invoke_callable_sync=invoke,
            backend="sql",
            backend_opcoes={"dsn": f"sqlite:///{db_file}", "lease_segundos": 1.0},
        )
        enfileirado = await fila.enqueue(falhar, {"id": 7}, retries=0, idempotency_key="job-7")
        primeira = await fila.process_all()
        dlq = await fila.list_dlq(10)
        obtido = await fila.get_job(str(enfileirado["id"]))
        reprocessado = await fila.reprocess_dlq(10)
        segunda = await fila.process_all()
        return primeira, dlq, obtido, reprocessado, segunda, fila.status()

    primeira, dlq, obtido, reprocessado, segunda, st = asyncio.run(run())
    assert primeira["dlq"] == 1
    assert dlq[0]["status"] == "dlq"
    assert dlq[0]["ultimo_erro"] == "erro:7"
    assert obtido is not None
    assert obtido["status"] == "dlq"
    assert reprocessado["reprocessados"] == 1
    assert reprocessado["pendentes"] == 1
    assert segunda["dlq"] == 1
    assert st["dlq"] == 1
    assert chamadas["n"] == 2


def test_v224_fila_sql_retry_com_estado_falho(tmp_path: Path) -> None:
    db_file = tmp_path / "jobs_retry.db"
    chamadas = {"n": 0}

    def invoke(fn, args):
        return fn(*args)

    def falhar_uma(payload):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("falha transitória")
        return payload["ok"]

    async def run():
        fila = JobQueue(
            "v224_retry",
            invoke_callable_sync=invoke,
            backend="sql",
            backend_opcoes={"dsn": f"sqlite:///{db_file}"},
        )
        info = await fila.enqueue(falhar_uma, {"ok": True}, retries=1, idempotency_key="retry-1")
        primeira = await fila.process_all()
        await asyncio.sleep(0.35)
        segunda = await fila.process_all()
        job_publico = await fila.get_job(str(info["id"]))
        return primeira, segunda, fila.status(), job_publico

    primeira, segunda, st, job_publico = asyncio.run(run())
    assert primeira["falhos"] == 1
    assert primeira["concluidos"] == 0
    assert segunda["concluidos"] == 1
    assert st["concluidos"] == 1
    assert st["falhos"] == 0
    assert job_publico is not None
    assert job_publico["status"] == "concluido"
