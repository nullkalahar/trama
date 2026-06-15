from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

from trama.jobs_runtime import JobQueue, jobs_backend_registrar, jobs_backend_remover, jobs_backends_listar, send_webhook


def test_job_queue_retry_idempotencia() -> None:
    calls = {"n": 0}

    def invoke(fn, args):
        return fn(*args)

    def job(payload):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("falha")
        return payload["x"] * 2

    import asyncio

    async def run():
        q = JobQueue("q", invoke_callable_sync=invoke)
        a = await q.enqueue(job, {"x": 2}, retries=2, idempotency_key="k1")
        b = await q.enqueue(job, {"x": 2}, retries=2, idempotency_key="k1")
        res = await q.process_all()
        return a, b, res, q.status()

    a, b, res, st = asyncio.run(run())
    assert a["enfileirado"] is True
    assert b["idempotente"] is True
    assert res["concluidos"] == 1
    assert st["dlq"] == 0


def test_send_webhook_ok() -> None:
    received: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            received["sig"] = self.headers.get("X-Trama-Signature")
            received["body"] = json.loads(raw.decode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, format, *args):  # noqa: A003
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import asyncio

        out = asyncio.run(
            send_webhook(
                url=f"http://127.0.0.1:{port}/wh",
                payload={"ok": True},
                secret="segredo",
                retries=2,
                timeout_seconds=2.0,
            )
        )
        assert out["ok"] is True
        assert received["body"] == {"ok": True}
        assert str(received["sig"]).startswith("sha256=")
    finally:
        server.shutdown()
        server.server_close()


def test_v223_job_queue_fachada_backend_memoria_padrao() -> None:
    def invoke(fn, args):
        return fn(*args)

    def job(payload):
        return payload["x"] + 1

    import asyncio

    async def run():
        q = JobQueue("v223_memoria", invoke_callable_sync=invoke)
        await q.enqueue(job, {"x": 1}, retries=1)
        await q.process_all()
        return q.status()

    st = asyncio.run(run())
    assert st["backend"] == "memoria"
    assert st["concluidos"] == 1


def test_v223_backend_custom_plugavel() -> None:
    class BackendFake:
        def __init__(self, name: str, **kwargs):  # noqa: ANN003
            _ = kwargs
            self.name = name
            self.itens: list[object] = []

        async def enqueue(self, handler, payload, retries=3, timeout_seconds=30.0, idempotency_key=None):  # noqa: ANN001
            _ = (handler, retries, timeout_seconds, idempotency_key)
            self.itens.append(payload)
            return {"enfileirado": True, "id": f"fake-{len(self.itens)}"}

        async def process_all(self):
            qtd = len(self.itens)
            self.itens.clear()
            return {"fila": self.name, "processados": qtd, "concluidos": qtd, "dlq": 0, "backend": "fake"}

        def status(self):
            return {"fila": self.name, "pendentes": len(self.itens), "concluidos": 0, "dlq": 0, "backend": "fake"}

    def factory(name: str, **kwargs):  # noqa: ANN003
        return BackendFake(name=name, **kwargs)

    jobs_backend_registrar("fake", factory)
    try:
        assert "fake" in jobs_backends_listar()
        q = JobQueue("fila_fake", backend="fake")

        import asyncio

        async def run():
            await q.enqueue(handler=None, payload={"ok": True})
            out = await q.process_all()
            return out, q.status()

        out, st = asyncio.run(run())
        assert out["backend"] == "fake"
        assert out["concluidos"] == 1
        assert st["backend"] == "fake"
    finally:
        _ = jobs_backend_remover("fake")
