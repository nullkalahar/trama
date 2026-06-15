from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from trama.cli import main
from trama.jobs_runtime import JobQueue


def test_cli_v225_jobs_worker_status_dlq_reprocessar(tmp_path: Path) -> None:
    db_file = tmp_path / "cli_v225.db"
    dsn = f"sqlite:///{db_file}"
    handlers = tmp_path / "handlers.trm"
    handlers.write_text(
        (
            "função processar(payload)\n"
            "    retorne payload[\"ok\"]\n"
            "fim\n"
            "\n"
            "função falhar(payload)\n"
            "    lance \"erro:\" + texto(payload[\"id\"])\n"
            "fim\n"
        ),
        encoding="utf-8",
    )

    def invoke(fn, args):
        return fn(*args)

    def processar(payload):
        return payload["ok"]

    def falhar(payload):
        raise RuntimeError(f"erro:{payload['id']}")

    async def preparar() -> None:
        fila_ok = JobQueue("emails", invoke_callable_sync=invoke, backend="sql", backend_opcoes={"dsn": dsn})
        await fila_ok.enqueue(processar, {"ok": True}, retries=1, idempotency_key="ok-1")
        fila_dlq = JobQueue("falhas", invoke_callable_sync=invoke, backend="sql", backend_opcoes={"dsn": dsn})
        await fila_dlq.enqueue(falhar, {"id": 7}, retries=0, idempotency_key="dlq-7")
        await fila_dlq.process_all()

    import asyncio

    asyncio.run(preparar())

    out = StringIO()
    with redirect_stdout(out):
        code = main(
            [
                "jobs-worker-rodar",
                "--dsn",
                dsn,
                "--fila",
                "emails",
                "--arquivo",
                str(handlers),
                "--uma-vez",
                "--json",
            ]
        )
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["processados_total"] == 1
    assert payload["status_final"]["concluidos"] == 1
    assert "processar" in payload["handlers"]

    out = StringIO()
    with redirect_stdout(out):
        code = main(["jobs-fila-status", "--dsn", dsn, "--fila", "emails", "--json"])
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["concluidos"] == 1

    out = StringIO()
    with redirect_stdout(out):
        code = main(["jobs-dlq-listar", "--dsn", dsn, "--fila", "falhas", "--limite", "10", "--json"])
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["total"] == 1
    assert payload["itens"][0]["status"] == "dlq"

    out = StringIO()
    with redirect_stdout(out):
        code = main(["jobs-dlq-reprocessar", "--dsn", dsn, "--fila", "falhas", "--limite", "10", "--json"])
    assert code == 0
    payload = json.loads(out.getvalue())
    assert payload["reprocessados"] == 1
