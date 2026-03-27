from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading

from trama.jobs_runtime import JobQueue, send_webhook


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
