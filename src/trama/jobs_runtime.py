"""Runtime de jobs e webhooks (v1.0)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import hmac
import json
import time
from typing import Any, Callable
import urllib.error
import urllib.request
import uuid


@dataclass
class Job:
    id: str
    handler: object
    payload: object
    retries: int
    timeout_seconds: float
    idempotency_key: str | None
    attempts: int = 0
    status: str = "pendente"
    last_error: str | None = None


class JobQueue:
    def __init__(
        self,
        name: str,
        invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
    ) -> None:
        self.name = name
        self.invoke_callable_sync = invoke_callable_sync
        self.pending: list[Job] = []
        self.done: list[Job] = []
        self.dlq: list[Job] = []
        self._idempotency: set[str] = set()

    async def enqueue(
        self,
        handler: object,
        payload: object,
        retries: int = 3,
        timeout_seconds: float = 30.0,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        if idempotency_key and idempotency_key in self._idempotency:
            return {"enfileirado": False, "idempotente": True}
        job = Job(
            id=uuid.uuid4().hex,
            handler=handler,
            payload=payload,
            retries=int(retries),
            timeout_seconds=float(timeout_seconds),
            idempotency_key=idempotency_key,
        )
        self.pending.append(job)
        if idempotency_key:
            self._idempotency.add(idempotency_key)
        return {"enfileirado": True, "id": job.id}

    async def process_all(self) -> dict[str, object]:
        processed = 0
        while self.pending:
            job = self.pending.pop(0)
            processed += 1
            await self._process_one(job)
        return {
            "fila": self.name,
            "processados": processed,
            "concluidos": len(self.done),
            "dlq": len(self.dlq),
        }

    async def _process_one(self, job: Job) -> None:
        if self.invoke_callable_sync is None:
            job.status = "falhou"
            job.last_error = "fila sem invocador de handler"
            self.dlq.append(job)
            return
        while job.attempts <= job.retries:
            job.attempts += 1
            try:
                coro = asyncio.to_thread(self.invoke_callable_sync, job.handler, [job.payload])
                _ = await asyncio.wait_for(coro, timeout=job.timeout_seconds)
                job.status = "concluido"
                self.done.append(job)
                return
            except Exception as exc:  # noqa: BLE001
                job.last_error = str(exc)
                if job.attempts > job.retries:
                    job.status = "dlq"
                    self.dlq.append(job)
                    return
                await asyncio.sleep(min(0.25 * (2 ** (job.attempts - 1)), 2.0))

    def status(self) -> dict[str, object]:
        return {
            "fila": self.name,
            "pendentes": len(self.pending),
            "concluidos": len(self.done),
            "dlq": len(self.dlq),
        }


async def send_webhook(
    url: str,
    payload: dict[str, object],
    secret: str | None = None,
    retries: int = 3,
    timeout_seconds: float = 10.0,
) -> dict[str, object]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if secret:
        sig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        headers["X-Trama-Signature"] = f"sha256={sig}"
    last_error: str | None = None
    for i in range(max(1, int(retries))):
        req = urllib.request.Request(url=url, method="POST", data=raw, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=float(timeout_seconds)) as response:
                status = int(response.getcode() or 0)
                body = response.read().decode("utf-8", errors="replace")
                if 200 <= status < 300:
                    return {"ok": True, "status": status, "tentativa": i + 1, "resposta": body}
                last_error = f"status {status}"
        except urllib.error.HTTPError as exc:
            last_error = f"status {exc.code}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        await asyncio.sleep(min(0.25 * (2**i), 2.0))
    return {"ok": False, "erro": last_error, "tentativas": int(retries)}
