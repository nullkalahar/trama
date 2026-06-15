"""Runtime de jobs e webhooks (v2.1.24): fachada com backend plugavel."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import hmac
import json
import threading
import time
from typing import Callable, Protocol
import urllib.error
import urllib.request
import uuid

from . import db_runtime
from . import observability_runtime


class JobsError(RuntimeError):
    """Erro do runtime de jobs."""


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
    handler_ref: str | None = None
    available_at: float = 0.0
    lease_expires_at: float | None = None


class JobsBackend(Protocol):
    """Contrato de backend para filas de jobs."""

    async def enqueue(
        self,
        handler: object,
        payload: object,
        retries: int = 3,
        timeout_seconds: float = 30.0,
        idempotency_key: str | None = None,
    ) -> dict[str, object]: ...

    async def process_all(self) -> dict[str, object]: ...

    def status(self) -> dict[str, object]: ...


def _agora() -> float:
    return time.time()


def _backoff_tentativa(tentativa: int) -> float:
    return min(0.25 * (2 ** max(0, tentativa - 1)), 2.0)


def _handler_ref(handler: object) -> str:
    if isinstance(handler, str):
        nome = handler.strip()
        if not nome:
            raise JobsError("handler de job invalido.")
        return nome
    nome = (
        getattr(handler, "__name__", "")
        or getattr(handler, "__qualname__", "")
        or getattr(handler, "name", "")
    )
    nome = str(nome or "").strip()
    if not nome:
        raise JobsError("handler de job invalido.")
    return nome


def _payload_json(payload: object) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    except Exception as exc:  # noqa: BLE001
        raise JobsError(f"payload de job nao serializavel: {exc}") from exc


def _payload_parse(raw: object) -> object:
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _para_float(valor: object | None, padrao: float | None = None) -> float | None:
    if valor in {None, ""}:
        return padrao
    return float(valor)


def _para_int(valor: object | None, padrao: int = 0) -> int:
    if valor in {None, ""}:
        return int(padrao)
    return int(valor)


def _snapshot_vazio(nome_fila: str, backend: str) -> dict[str, object]:
    return {
        "fila": nome_fila,
        "backend": backend,
        "pendentes": 0,
        "processando": 0,
        "concluidos": 0,
        "falhos": 0,
        "dlq": 0,
    }


class _MemoryJobsBackend:
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
        self.failed: list[Job] = []
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
            observability_runtime.registrar_runtime_metrica("jobs", "idempotente_ignorado", labels={"fila": self.name})
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
        observability_runtime.registrar_runtime_metrica("jobs", "enfileirado", labels={"fila": self.name, "backend": "memoria"})
        return {"enfileirado": True, "id": job.id, "backend": "memoria"}

    async def process_all(self) -> dict[str, object]:
        processed = 0
        while self.pending:
            job = self.pending.pop(0)
            processed += 1
            await self._process_one(job)
        observability_runtime.registrar_runtime_metrica(
            "jobs", "processados", valor=float(processed), labels={"fila": self.name, "backend": "memoria"}
        )
        out = self.status()
        out["processados"] = processed
        return out

    async def _process_one(self, job: Job) -> None:
        if self.invoke_callable_sync is None:
            job.status = "falhou"
            job.last_error = "fila sem invocador de handler"
            self.dlq.append(job)
            observability_runtime.registrar_runtime_metrica(
                "jobs", "falha_sem_invocador", labels={"fila": self.name, "backend": "memoria"}
            )
            return
        while job.attempts <= job.retries:
            job.attempts += 1
            try:
                coro = asyncio.to_thread(self.invoke_callable_sync, job.handler, [job.payload])
                _ = await asyncio.wait_for(coro, timeout=job.timeout_seconds)
                job.status = "concluido"
                self.done.append(job)
                observability_runtime.registrar_runtime_metrica(
                    "jobs", "concluido", labels={"fila": self.name, "backend": "memoria"}
                )
                return
            except Exception as exc:  # noqa: BLE001
                job.last_error = str(exc)
                if job.attempts > job.retries:
                    job.status = "dlq"
                    self.dlq.append(job)
                    observability_runtime.registrar_runtime_metrica(
                        "jobs", "dlq", labels={"fila": self.name, "backend": "memoria"}
                    )
                    return
                job.status = "falhou"
                self.failed.append(job)
                observability_runtime.registrar_runtime_metrica(
                    "jobs", "retry", labels={"fila": self.name, "backend": "memoria", "tentativa": job.attempts}
                )
                await asyncio.sleep(_backoff_tentativa(job.attempts))

    async def list_dlq(self, limite: int = 20) -> list[dict[str, object]]:
        itens = self.dlq[: max(0, int(limite))]
        return [
            {
                "id": job.id,
                "handler_ref": job.handler_ref or _handler_ref(job.handler),
                "payload": job.payload,
                "status": job.status,
                "tentativas": job.attempts,
                "tentativas_maximas": job.retries,
                "ultimo_erro": job.last_error,
            }
            for job in itens
        ]

    async def get_job(self, job_id: str) -> dict[str, object] | None:
        for job in self.pending + self.done + self.dlq + self.failed:
            if job.id == job_id:
                return {
                    "id": job.id,
                    "handler_ref": job.handler_ref or _handler_ref(job.handler),
                    "payload": job.payload,
                    "status": job.status,
                    "tentativas": job.attempts,
                    "tentativas_maximas": job.retries,
                    "ultimo_erro": job.last_error,
                }
        return None

    async def reprocess_dlq(self, limite: int = 100) -> dict[str, object]:
        itens = self.dlq[: max(0, int(limite))]
        self.dlq = self.dlq[len(itens) :]
        for job in itens:
            job.status = "pendente"
            job.last_error = None
            self.pending.append(job)
        observability_runtime.registrar_runtime_metrica(
            "jobs", "reprocessado_dlq", valor=float(len(itens)), labels={"fila": self.name, "backend": "memoria"}
        )
        out = self.status()
        out["reprocessados"] = len(itens)
        return out

    def status(self) -> dict[str, object]:
        return {
            "fila": self.name,
            "backend": "memoria",
            "pendentes": len(self.pending),
            "processando": 0,
            "concluidos": len(self.done),
            "falhos": len(self.failed),
            "dlq": len(self.dlq),
        }


class _SqlJobsBackend:
    def __init__(
        self,
        name: str,
        invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
        dsn: str | None = None,
        lote_processamento: int = 100,
        lease_segundos: float = 30.0,
        handlers_registrados: dict[str, object] | None = None,
    ) -> None:
        self.name = name
        self.invoke_callable_sync = invoke_callable_sync
        self.dsn = str(dsn or "").strip()
        if not self.dsn:
            raise JobsError("backend sql requer opcao_backend com dsn.")
        self.lote_processamento = max(1, int(lote_processamento))
        self.lease_segundos = max(1.0, float(lease_segundos))
        self._conn: db_runtime.DbConnection | None = None
        self._init_lock = asyncio.Lock()
        self._handlers: dict[str, object] = dict(handlers_registrados or {})
        self._snapshot = _snapshot_vazio(self.name, "sql")

    async def enqueue(
        self,
        handler: object,
        payload: object,
        retries: int = 3,
        timeout_seconds: float = 30.0,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        conn = await self._ensure_conn()
        handler_ref = _handler_ref(handler)
        self._handlers[handler_ref] = handler
        payload_json = _payload_json(payload)
        job_id = uuid.uuid4().hex
        agora = _agora()
        retries_norm = max(0, int(retries))
        timeout_norm = max(0.01, float(timeout_seconds))

        if idempotency_key:
            existente = await db_runtime.consultar(
                conn,
                (
                    "SELECT id, status FROM trama_jobs "
                    "WHERE fila = ? AND idempotency_key = ? "
                    "ORDER BY created_at DESC LIMIT 1"
                ),
                [self.name, idempotency_key],
            )
            if existente:
                observability_runtime.registrar_runtime_metrica(
                    "jobs", "idempotente_ignorado", labels={"fila": self.name, "backend": "sql"}
                )
                await self._refresh_snapshot()
                return {
                    "enfileirado": False,
                    "idempotente": True,
                    "id": existente[0]["id"],
                    "status": existente[0]["status"],
                    "backend": "sql",
                }

        try:
            await db_runtime.executar(
                conn,
                (
                    "INSERT INTO trama_jobs ("
                    "id, fila, handler_ref, payload_json, status, attempts, retries, timeout_seconds, "
                    "idempotency_key, created_at, updated_at, available_at, lease_expires_at, last_error, completed_at"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                [
                    job_id,
                    self.name,
                    handler_ref,
                    payload_json,
                    "pendente",
                    0,
                    retries_norm,
                    timeout_norm,
                    idempotency_key,
                    agora,
                    agora,
                    agora,
                    None,
                    None,
                    None,
                ],
            )
        except Exception:
            if idempotency_key:
                existente = await db_runtime.consultar(
                    conn,
                    (
                        "SELECT id, status FROM trama_jobs "
                        "WHERE fila = ? AND idempotency_key = ? "
                        "ORDER BY created_at DESC LIMIT 1"
                    ),
                    [self.name, idempotency_key],
                )
                if existente:
                    observability_runtime.registrar_runtime_metrica(
                        "jobs", "idempotente_ignorado", labels={"fila": self.name, "backend": "sql"}
                    )
                    await self._refresh_snapshot()
                    return {
                        "enfileirado": False,
                        "idempotente": True,
                        "id": existente[0]["id"],
                        "status": existente[0]["status"],
                        "backend": "sql",
                    }
            raise

        observability_runtime.registrar_runtime_metrica("jobs", "enfileirado", labels={"fila": self.name, "backend": "sql"})
        await self._refresh_snapshot()
        return {"enfileirado": True, "id": job_id, "backend": "sql"}

    def handlers_registrar(self, handlers: dict[str, object]) -> dict[str, object]:
        adicionados = 0
        for nome, handler in dict(handlers).items():
            nome_norm = str(nome).strip()
            if not nome_norm:
                continue
            self._handlers[nome_norm] = handler
            adicionados += 1
        return {"ok": True, "backend": "sql", "fila": self.name, "handlers_registrados": adicionados}

    async def process_all(self) -> dict[str, object]:
        conn = await self._ensure_conn()
        processed = 0
        while processed < self.lote_processamento:
            claimed = await self._claim_next(conn)
            if claimed is None:
                break
            processed += 1
            await self._process_claimed(conn, claimed)
        observability_runtime.registrar_runtime_metrica(
            "jobs", "processados", valor=float(processed), labels={"fila": self.name, "backend": "sql"}
        )
        out = await self._refresh_snapshot()
        out["processados"] = processed
        return out

    async def list_dlq(self, limite: int = 20) -> list[dict[str, object]]:
        conn = await self._ensure_conn()
        linhas = await db_runtime.consultar(
            conn,
            (
                "SELECT id, fila, handler_ref, payload_json, status, attempts, retries, timeout_seconds, "
                "idempotency_key, last_error, available_at, lease_expires_at, created_at, updated_at, completed_at "
                "FROM trama_jobs WHERE fila = ? AND status = ? "
                "ORDER BY updated_at ASC LIMIT ?"
            ),
            [self.name, "dlq", max(0, int(limite))],
        )
        return [self._row_to_publico(row) for row in linhas]

    async def list_jobs(self, limite: int = 50, status: str | None = None) -> list[dict[str, object]]:
        conn = await self._ensure_conn()
        params: list[object] = [self.name]
        sql = (
            "SELECT id, fila, handler_ref, payload_json, status, attempts, retries, timeout_seconds, "
            "idempotency_key, last_error, available_at, lease_expires_at, created_at, updated_at, completed_at "
            "FROM trama_jobs WHERE fila = ?"
        )
        if status:
            sql += " AND status = ?"
            params.append(str(status))
        sql += " ORDER BY created_at ASC LIMIT ?"
        params.append(max(0, int(limite)))
        linhas = await db_runtime.consultar(conn, sql, params)
        return [self._row_to_publico(row) for row in linhas]

    async def refresh_status(self) -> dict[str, object]:
        return await self._refresh_snapshot()

    async def get_job(self, job_id: str) -> dict[str, object] | None:
        conn = await self._ensure_conn()
        linhas = await db_runtime.consultar(
            conn,
            (
                "SELECT id, fila, handler_ref, payload_json, status, attempts, retries, timeout_seconds, "
                "idempotency_key, last_error, available_at, lease_expires_at, created_at, updated_at, completed_at "
                "FROM trama_jobs WHERE fila = ? AND id = ? LIMIT 1"
            ),
            [self.name, job_id],
        )
        if not linhas:
            return None
        return self._row_to_publico(linhas[0])

    async def reprocess_dlq(self, limite: int = 100) -> dict[str, object]:
        conn = await self._ensure_conn()
        limite_norm = max(0, int(limite))
        if limite_norm == 0:
            out = await self._refresh_snapshot()
            out["reprocessados"] = 0
            return out

        tx = await db_runtime.transacao_iniciar(conn)
        reprocessados = 0
        agora = _agora()
        try:
            itens = await db_runtime.tx_consultar(
                tx,
                (
                    "SELECT id FROM trama_jobs "
                    "WHERE fila = ? AND status = ? "
                    "ORDER BY updated_at ASC LIMIT ?"
                ),
                [self.name, "dlq", limite_norm],
            )
            for item in itens:
                out = await db_runtime.tx_executar(
                    tx,
                    (
                        "UPDATE trama_jobs SET status = ?, available_at = ?, lease_expires_at = ?, "
                        "last_error = ?, updated_at = ? WHERE id = ? AND fila = ?"
                    ),
                    ["pendente", agora, None, None, agora, item["id"], self.name],
                )
                reprocessados += int(out.get("rows_affected", 0))
            await db_runtime.transacao_commit(tx)
        except Exception:
            await db_runtime.transacao_rollback(tx)
            raise

        observability_runtime.registrar_runtime_metrica(
            "jobs", "reprocessado_dlq", valor=float(reprocessados), labels={"fila": self.name, "backend": "sql"}
        )
        out = await self._refresh_snapshot()
        out["reprocessados"] = reprocessados
        return out

    def status(self) -> dict[str, object]:
        return dict(self._snapshot)

    async def _ensure_conn(self) -> db_runtime.DbConnection:
        if self._conn is not None:
            return self._conn
        async with self._init_lock:
            if self._conn is None:
                self._conn = await db_runtime.conectar(self.dsn)
                await self._ensure_schema(self._conn)
                await self._refresh_snapshot()
        return self._conn

    async def _ensure_schema(self, conn: db_runtime.DbConnection) -> None:
        await db_runtime.executar(
            conn,
            (
                "CREATE TABLE IF NOT EXISTS trama_jobs ("
                "id TEXT PRIMARY KEY, "
                "fila TEXT NOT NULL, "
                "handler_ref TEXT NOT NULL, "
                "payload_json TEXT NOT NULL, "
                "status TEXT NOT NULL, "
                "attempts INTEGER NOT NULL DEFAULT 0, "
                "retries INTEGER NOT NULL DEFAULT 3, "
                "timeout_seconds REAL NOT NULL DEFAULT 30.0, "
                "idempotency_key TEXT NULL, "
                "created_at REAL NOT NULL, "
                "updated_at REAL NOT NULL, "
                "available_at REAL NOT NULL, "
                "lease_expires_at REAL NULL, "
                "last_error TEXT NULL, "
                "completed_at REAL NULL"
                ")"
            ),
        )
        await db_runtime.executar(
            conn,
            "CREATE INDEX IF NOT EXISTS idx_trama_jobs_fila_status_disp ON trama_jobs (fila, status, available_at)",
        )
        await db_runtime.executar(
            conn,
            "CREATE INDEX IF NOT EXISTS idx_trama_jobs_fila_lease ON trama_jobs (fila, lease_expires_at)",
        )
        await db_runtime.executar(
            conn,
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_trama_jobs_fila_idempotencia ON trama_jobs (fila, idempotency_key)",
        )

    async def _claim_next(self, conn: db_runtime.DbConnection) -> dict[str, object] | None:
        agora = _agora()
        lease_expira = agora + self.lease_segundos
        tx = await db_runtime.transacao_iniciar(conn)
        try:
            rows = await db_runtime.tx_consultar(
                tx,
                (
                    "SELECT id, fila, handler_ref, payload_json, status, attempts, retries, timeout_seconds, "
                    "idempotency_key, last_error, available_at, lease_expires_at "
                    "FROM trama_jobs "
                    "WHERE fila = ? "
                    "AND status IN (?, ?) "
                    "AND available_at <= ? "
                    "AND (lease_expires_at IS NULL OR lease_expires_at <= ?) "
                    "ORDER BY created_at ASC LIMIT 1"
                ),
                [self.name, "pendente", "falhou", agora, agora],
            )
            if not rows:
                await db_runtime.transacao_commit(tx)
                return None
            row = rows[0]
            nova_tentativa = int(row["attempts"]) + 1
            out = await db_runtime.tx_executar(
                tx,
                (
                    "UPDATE trama_jobs SET status = ?, attempts = ?, updated_at = ?, lease_expires_at = ? "
                    "WHERE id = ? AND fila = ? AND status IN (?, ?) "
                    "AND (lease_expires_at IS NULL OR lease_expires_at <= ?)"
                ),
                [
                    "processando",
                    nova_tentativa,
                    agora,
                    lease_expira,
                    row["id"],
                    self.name,
                    "pendente",
                    "falhou",
                    agora,
                ],
            )
            if int(out.get("rows_affected", 0)) != 1:
                await db_runtime.transacao_rollback(tx)
                return None
            await db_runtime.transacao_commit(tx)
            row["attempts"] = nova_tentativa
            row["status"] = "processando"
            row["lease_expires_at"] = lease_expira
            observability_runtime.registrar_runtime_metrica(
                "jobs",
                "lease_adquirido",
                labels={"fila": self.name, "backend": "sql", "job_id": row["id"]},
            )
            return row
        except Exception:
            await db_runtime.transacao_rollback(tx)
            raise

    async def _process_claimed(self, conn: db_runtime.DbConnection, row: dict[str, object]) -> None:
        handler_ref = str(row["handler_ref"])
        payload = _payload_parse(row["payload_json"])
        handler = self._handlers.get(handler_ref)
        attempts = int(row["attempts"])
        retries = int(row["retries"])
        timeout_seconds = float(row["timeout_seconds"])
        job_id = str(row["id"])
        if self.invoke_callable_sync is None:
            await self._finalizar_falha(
                conn,
                job_id=job_id,
                attempts=attempts,
                retries=retries,
                mensagem="fila sem invocador de handler",
            )
            observability_runtime.registrar_runtime_metrica(
                "jobs", "falha_sem_invocador", labels={"fila": self.name, "backend": "sql"}
            )
            return
        if handler is None:
            await self._finalizar_falha(
                conn,
                job_id=job_id,
                attempts=attempts,
                retries=retries,
                mensagem=f"handler nao registrado: {handler_ref}",
            )
            observability_runtime.registrar_runtime_metrica(
                "jobs", "falha_handler_nao_registrado", labels={"fila": self.name, "backend": "sql"}
            )
            return

        try:
            coro = asyncio.to_thread(self.invoke_callable_sync, handler, [payload])
            _ = await asyncio.wait_for(coro, timeout=timeout_seconds)
            await db_runtime.executar(
                conn,
                (
                    "UPDATE trama_jobs SET status = ?, last_error = ?, lease_expires_at = ?, "
                    "completed_at = ?, updated_at = ? WHERE id = ? AND fila = ?"
                ),
                ["concluido", None, None, _agora(), _agora(), job_id, self.name],
            )
            observability_runtime.registrar_runtime_metrica(
                "jobs", "concluido", labels={"fila": self.name, "backend": "sql"}
            )
        except Exception as exc:  # noqa: BLE001
            await self._finalizar_falha(
                conn,
                job_id=job_id,
                attempts=attempts,
                retries=retries,
                mensagem=str(exc),
            )

    async def _finalizar_falha(
        self,
        conn: db_runtime.DbConnection,
        *,
        job_id: str,
        attempts: int,
        retries: int,
        mensagem: str,
    ) -> None:
        agora = _agora()
        if attempts > retries:
            await db_runtime.executar(
                conn,
                (
                    "UPDATE trama_jobs SET status = ?, last_error = ?, lease_expires_at = ?, "
                    "updated_at = ? WHERE id = ? AND fila = ?"
                ),
                ["dlq", mensagem, None, agora, job_id, self.name],
            )
            observability_runtime.registrar_runtime_metrica(
                "jobs", "dlq", labels={"fila": self.name, "backend": "sql"}
            )
            return

        disponivel_em = agora + _backoff_tentativa(attempts)
        await db_runtime.executar(
            conn,
            (
                "UPDATE trama_jobs SET status = ?, last_error = ?, lease_expires_at = ?, "
                "available_at = ?, updated_at = ? WHERE id = ? AND fila = ?"
            ),
            ["falhou", mensagem, None, disponivel_em, agora, job_id, self.name],
        )
        observability_runtime.registrar_runtime_metrica(
            "jobs", "retry", labels={"fila": self.name, "backend": "sql", "tentativa": attempts}
        )

    async def _refresh_snapshot(self) -> dict[str, object]:
        conn = await self._ensure_conn_no_schema_recursion()
        rows = await db_runtime.consultar(
            conn,
            (
                "SELECT status, COUNT(*) AS total "
                "FROM trama_jobs WHERE fila = ? GROUP BY status"
            ),
            [self.name],
        )
        snap = _snapshot_vazio(self.name, "sql")
        for row in rows:
            status = str(row["status"])
            total = int(row["total"])
            if status == "pendente":
                snap["pendentes"] = total
            elif status == "processando":
                snap["processando"] = total
            elif status == "concluido":
                snap["concluidos"] = total
            elif status == "falhou":
                snap["falhos"] = total
            elif status == "dlq":
                snap["dlq"] = total
        self._snapshot = snap
        return dict(snap)

    async def _ensure_conn_no_schema_recursion(self) -> db_runtime.DbConnection:
        if self._conn is None:
            self._conn = await db_runtime.conectar(self.dsn)
            await self._ensure_schema(self._conn)
        return self._conn

    def _row_to_publico(self, row: dict[str, object]) -> dict[str, object]:
        return {
            "id": row["id"],
            "fila": row["fila"],
            "handler_ref": row["handler_ref"],
            "payload": _payload_parse(row["payload_json"]),
            "status": row["status"],
            "tentativas": int(row["attempts"]),
            "tentativas_maximas": int(row["retries"]),
            "timeout_segundos": float(row["timeout_seconds"]),
            "chave_idempotencia": row["idempotency_key"],
            "ultimo_erro": row["last_error"],
            "disponivel_em": row["available_at"],
            "lease_expira_em": row["lease_expires_at"],
            "criado_em": row["created_at"],
            "atualizado_em": row["updated_at"],
            "concluido_em": row["completed_at"],
            "backend": "sql",
        }


class _RedisJobsBackend:
    def __init__(
        self,
        name: str,
        invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
        redis_url: str | None = None,
        chave_prefixo: str = "trama:jobs",
        lote_processamento: int = 100,
        lease_segundos: float = 30.0,
        handlers_registrados: dict[str, object] | None = None,
    ) -> None:
        self.name = name
        self.invoke_callable_sync = invoke_callable_sync
        self.redis_url = str(redis_url or "").strip()
        if not self.redis_url:
            raise JobsError("backend redis requer opcao_backend com redis_url.")
        self.chave_prefixo = str(chave_prefixo or "trama:jobs").strip() or "trama:jobs"
        self.lote_processamento = max(1, int(lote_processamento))
        self.lease_segundos = max(1.0, float(lease_segundos))
        self._handlers: dict[str, object] = dict(handlers_registrados or {})
        self._redis = None
        self._snapshot = _snapshot_vazio(self.name, "redis")
        self._init_backend()

    def _init_backend(self) -> None:
        try:
            redis_mod = __import__("redis")
            self._redis = redis_mod.Redis.from_url(self.redis_url, decode_responses=True)
            self._redis.ping()
        except Exception as exc:  # noqa: BLE001
            raise JobsError(f"falha_redis_jobs: {exc}") from exc

    def _key(self, nome: str) -> str:
        return f"{self.chave_prefixo}:{self.name}:{nome}"

    def _job_key(self, job_id: str) -> str:
        return self._key(f"job:{job_id}")

    def handlers_registrar(self, handlers: dict[str, object]) -> dict[str, object]:
        adicionados = 0
        for nome, handler in dict(handlers).items():
            nome_norm = str(nome).strip()
            if not nome_norm:
                continue
            self._handlers[nome_norm] = handler
            adicionados += 1
        return {"ok": True, "backend": "redis", "fila": self.name, "handlers_registrados": adicionados}

    async def enqueue(
        self,
        handler: object,
        payload: object,
        retries: int = 3,
        timeout_seconds: float = 30.0,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        handler_ref = _handler_ref(handler)
        self._handlers[handler_ref] = handler
        payload_json = _payload_json(payload)
        job_id = uuid.uuid4().hex
        agora = _agora()
        if idempotency_key:
            existente = self._redis.get(self._key(f"idem:{idempotency_key}"))
            if existente:
                observability_runtime.registrar_runtime_metrica(
                    "jobs", "idempotente_ignorado", labels={"fila": self.name, "backend": "redis"}
                )
                return {"enfileirado": False, "idempotente": True, "id": existente, "backend": "redis"}
        dados = {
            "id": job_id,
            "fila": self.name,
            "handler_ref": handler_ref,
            "payload_json": payload_json,
            "status": "pendente",
            "attempts": "0",
            "retries": str(max(0, int(retries))),
            "timeout_seconds": str(max(0.01, float(timeout_seconds))),
            "idempotency_key": str(idempotency_key or ""),
            "created_at": str(agora),
            "updated_at": str(agora),
            "available_at": str(agora),
            "lease_expires_at": "",
            "last_error": "",
            "completed_at": "",
        }
        self._redis.hset(self._job_key(job_id), mapping=dados)
        self._redis.sadd(self._key("jobs"), job_id)
        self._redis.rpush(self._key("pendentes"), job_id)
        if idempotency_key:
            self._redis.set(self._key(f"idem:{idempotency_key}"), job_id)
        observability_runtime.registrar_runtime_metrica("jobs", "enfileirado", labels={"fila": self.name, "backend": "redis"})
        await self.refresh_status()
        return {"enfileirado": True, "id": job_id, "backend": "redis"}

    async def process_all(self) -> dict[str, object]:
        processados = 0
        while processados < self.lote_processamento:
            self._promover_agendados()
            job_id = self._redis.rpoplpush(self._key("pendentes"), self._key("processando"))
            if not job_id:
                break
            processados += 1
            await self._process_one(str(job_id))
        observability_runtime.registrar_runtime_metrica(
            "jobs", "processados", valor=float(processados), labels={"fila": self.name, "backend": "redis"}
        )
        out = await self.refresh_status()
        out["processados"] = processados
        return out

    def _promover_agendados(self) -> int:
        agora = _agora()
        ids = list(self._redis.zrangebyscore(self._key("agendados"), 0, agora))
        promovidos = 0
        for job_id in ids:
            self._redis.zrem(self._key("agendados"), job_id)
            self._redis.rpush(self._key("pendentes"), job_id)
            self._redis.hset(self._job_key(str(job_id)), mapping={"status": "pendente", "updated_at": str(agora)})
            promovidos += 1
        return promovidos

    async def _process_one(self, job_id: str) -> None:
        agora = _agora()
        dados = self._redis.hgetall(self._job_key(job_id))
        if not dados:
            self._redis.lrem(self._key("processando"), 1, job_id)
            return
        attempts = _para_int(dados.get("attempts"), 0) + 1
        retries = _para_int(dados.get("retries"), 0)
        timeout_seconds = float(dados.get("timeout_seconds", "30.0") or 30.0)
        handler_ref = str(dados.get("handler_ref", ""))
        self._redis.hset(
            self._job_key(job_id),
            mapping={
                "status": "processando",
                "attempts": str(attempts),
                "updated_at": str(agora),
                "lease_expires_at": str(agora + self.lease_segundos),
            },
        )
        handler = self._handlers.get(handler_ref)
        if self.invoke_callable_sync is None:
            await self._finalizar_falha(job_id, attempts, retries, "fila sem invocador de handler")
            observability_runtime.registrar_runtime_metrica(
                "jobs", "falha_sem_invocador", labels={"fila": self.name, "backend": "redis"}
            )
            return
        if handler is None:
            await self._finalizar_falha(job_id, attempts, retries, f"handler nao registrado: {handler_ref}")
            observability_runtime.registrar_runtime_metrica(
                "jobs", "falha_handler_nao_registrado", labels={"fila": self.name, "backend": "redis"}
            )
            return
        try:
            payload = _payload_parse(dados.get("payload_json", "{}"))
            coro = asyncio.to_thread(self.invoke_callable_sync, handler, [payload])
            _ = await asyncio.wait_for(coro, timeout=timeout_seconds)
            agora_fim = _agora()
            self._redis.hset(
                self._job_key(job_id),
                mapping={
                    "status": "concluido",
                    "lease_expires_at": "",
                    "last_error": "",
                    "updated_at": str(agora_fim),
                    "completed_at": str(agora_fim),
                },
            )
            self._redis.lrem(self._key("processando"), 1, job_id)
            self._redis.incr(self._key("cont:concluidos"))
            observability_runtime.registrar_runtime_metrica(
                "jobs", "concluido", labels={"fila": self.name, "backend": "redis"}
            )
        except Exception as exc:  # noqa: BLE001
            await self._finalizar_falha(job_id, attempts, retries, str(exc))

    async def _finalizar_falha(self, job_id: str, attempts: int, retries: int, mensagem: str) -> None:
        agora = _agora()
        self._redis.lrem(self._key("processando"), 1, job_id)
        if attempts > retries:
            self._redis.hset(
                self._job_key(job_id),
                mapping={"status": "dlq", "last_error": mensagem, "updated_at": str(agora), "lease_expires_at": ""},
            )
            self._redis.rpush(self._key("dlq"), job_id)
            observability_runtime.registrar_runtime_metrica(
                "jobs", "dlq", labels={"fila": self.name, "backend": "redis"}
            )
            return
        disponivel_em = agora + _backoff_tentativa(attempts)
        self._redis.hset(
            self._job_key(job_id),
            mapping={
                "status": "falhou",
                "last_error": mensagem,
                "updated_at": str(agora),
                "lease_expires_at": "",
                "available_at": str(disponivel_em),
            },
        )
        self._redis.zadd(self._key("agendados"), {job_id: disponivel_em})
        observability_runtime.registrar_runtime_metrica(
            "jobs", "retry", labels={"fila": self.name, "backend": "redis", "tentativa": attempts}
        )

    async def list_dlq(self, limite: int = 20) -> list[dict[str, object]]:
        ids = list(self._redis.lrange(self._key("dlq"), 0, max(0, int(limite)) - 1))
        return [self._job_publico(str(job_id)) for job_id in ids]

    async def list_jobs(self, limite: int = 50, status: str | None = None) -> list[dict[str, object]]:
        ids = sorted(str(x) for x in list(self._redis.smembers(self._key("jobs"))))
        itens: list[dict[str, object]] = []
        for job_id in ids:
            item = self._job_publico(job_id)
            if status and str(item.get("status")) != str(status):
                continue
            itens.append(item)
            if len(itens) >= max(0, int(limite)):
                break
        return itens

    async def get_job(self, job_id: str) -> dict[str, object] | None:
        if not self._redis.exists(self._job_key(job_id)):
            return None
        return self._job_publico(job_id)

    async def reprocess_dlq(self, limite: int = 100) -> dict[str, object]:
        reprocessados = 0
        agora = _agora()
        for _ in range(max(0, int(limite))):
            job_id = self._redis.lpop(self._key("dlq"))
            if not job_id:
                break
            self._redis.hset(
                self._job_key(str(job_id)),
                mapping={"status": "pendente", "last_error": "", "updated_at": str(agora), "available_at": str(agora)},
            )
            self._redis.rpush(self._key("pendentes"), job_id)
            reprocessados += 1
        observability_runtime.registrar_runtime_metrica(
            "jobs", "reprocessado_dlq", valor=float(reprocessados), labels={"fila": self.name, "backend": "redis"}
        )
        out = await self.refresh_status()
        out["reprocessados"] = reprocessados
        return out

    def status(self) -> dict[str, object]:
        return dict(self._snapshot)

    async def refresh_status(self) -> dict[str, object]:
        self._promover_agendados()
        self._snapshot = {
            "fila": self.name,
            "backend": "redis",
            "pendentes": int(self._redis.llen(self._key("pendentes"))),
            "processando": int(self._redis.llen(self._key("processando"))),
            "concluidos": _para_int(self._redis.get(self._key("cont:concluidos")), 0),
            "falhos": int(self._redis.zcard(self._key("agendados"))),
            "dlq": int(self._redis.llen(self._key("dlq"))),
        }
        return dict(self._snapshot)

    def _job_publico(self, job_id: str) -> dict[str, object]:
        row = self._redis.hgetall(self._job_key(job_id))
        return {
            "id": job_id,
            "fila": row.get("fila", self.name),
            "handler_ref": row.get("handler_ref", ""),
            "payload": _payload_parse(row.get("payload_json", "{}")),
            "status": row.get("status", ""),
            "tentativas": _para_int(row.get("attempts"), 0),
            "tentativas_maximas": _para_int(row.get("retries"), 0),
            "timeout_segundos": float(row.get("timeout_seconds", "30.0") or 30.0),
            "chave_idempotencia": row.get("idempotency_key") or None,
            "ultimo_erro": row.get("last_error") or None,
            "disponivel_em": _para_float(row.get("available_at"), 0.0),
            "lease_expira_em": _para_float(row.get("lease_expires_at"), None),
            "criado_em": _para_float(row.get("created_at"), 0.0),
            "atualizado_em": _para_float(row.get("updated_at"), 0.0),
            "concluido_em": _para_float(row.get("completed_at"), None),
            "backend": "redis",
        }


def _factory_memoria(
    *,
    name: str,
    invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
    **kwargs: object,
) -> JobsBackend:
    _ = kwargs
    return _MemoryJobsBackend(name=name, invoke_callable_sync=invoke_callable_sync)


def _factory_sql(
    *,
    name: str,
    invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
    **kwargs: object,
) -> JobsBackend:
    return _SqlJobsBackend(name=name, invoke_callable_sync=invoke_callable_sync, **kwargs)


def _factory_redis(
    *,
    name: str,
    invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
    **kwargs: object,
) -> JobsBackend:
    return _RedisJobsBackend(name=name, invoke_callable_sync=invoke_callable_sync, **kwargs)


_BACKEND_LOCK = threading.RLock()
_BACKEND_FACTORIES: dict[str, Callable[..., JobsBackend]] = {
    "memoria": _factory_memoria,
    "sql": _factory_sql,
    "redis": _factory_redis,
}


def jobs_backend_registrar(nome: str, fabrica: Callable[..., JobsBackend]) -> dict[str, object]:
    backend = str(nome or "").strip().lower()
    if not backend:
        raise JobsError("nome do backend de jobs e obrigatorio.")
    with _BACKEND_LOCK:
        _BACKEND_FACTORIES[backend] = fabrica
    return {"ok": True, "backend": backend}


def jobs_backend_remover(nome: str) -> bool:
    backend = str(nome or "").strip().lower()
    if backend in {"", "memoria", "sql", "redis"}:
        return False
    with _BACKEND_LOCK:
        return _BACKEND_FACTORIES.pop(backend, None) is not None


def jobs_backends_listar() -> list[str]:
    with _BACKEND_LOCK:
        return sorted(_BACKEND_FACTORIES.keys())


def jobs_backend_criar(
    nome: str = "memoria",
    *,
    name: str,
    invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
    opcoes: dict[str, object] | None = None,
) -> JobsBackend:
    backend = str(nome or "memoria").strip().lower() or "memoria"
    with _BACKEND_LOCK:
        factory = _BACKEND_FACTORIES.get(backend)
    if factory is None:
        raise JobsError(f"backend de jobs desconhecido: {backend}")
    obj = factory(
        name=name,
        invoke_callable_sync=invoke_callable_sync,
        **dict(opcoes or {}),
    )
    return obj


class JobQueue:
    def __init__(
        self,
        name: str,
        invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
        *,
        backend: str = "memoria",
        backend_instancia: JobsBackend | None = None,
        backend_opcoes: dict[str, object] | None = None,
    ) -> None:
        self.name = str(name)
        self.invoke_callable_sync = invoke_callable_sync
        self.backend = str(backend or "memoria").strip().lower() or "memoria"
        self._impl = (
            backend_instancia
            if backend_instancia is not None
            else jobs_backend_criar(
                self.backend,
                name=self.name,
                invoke_callable_sync=self.invoke_callable_sync,
                opcoes=backend_opcoes,
            )
        )

    @property
    def pending(self) -> list[Job]:
        raw = getattr(self._impl, "pending", [])
        return list(raw) if isinstance(raw, list) else []

    @property
    def done(self) -> list[Job]:
        raw = getattr(self._impl, "done", [])
        return list(raw) if isinstance(raw, list) else []

    @property
    def dlq(self) -> list[Job]:
        raw = getattr(self._impl, "dlq", [])
        return list(raw) if isinstance(raw, list) else []

    async def enqueue(
        self,
        handler: object,
        payload: object,
        retries: int = 3,
        timeout_seconds: float = 30.0,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        return await self._impl.enqueue(
            handler=handler,
            payload=payload,
            retries=retries,
            timeout_seconds=timeout_seconds,
            idempotency_key=idempotency_key,
        )

    async def process_all(self) -> dict[str, object]:
        out = await self._impl.process_all()
        if "backend" not in out:
            out["backend"] = self.backend
        return out

    def status(self) -> dict[str, object]:
        out = dict(self._impl.status())
        out.setdefault("backend", self.backend)
        return out

    async def refresh_status(self) -> dict[str, object]:
        metodo = getattr(self._impl, "refresh_status", None)
        if metodo is None:
            return self.status()
        out = await metodo()
        out.setdefault("backend", self.backend)
        return out

    async def list_dlq(self, limite: int = 20) -> list[dict[str, object]]:
        metodo = getattr(self._impl, "list_dlq", None)
        if metodo is None:
            return []
        return await metodo(limite)

    async def list_jobs(self, limite: int = 50, status: str | None = None) -> list[dict[str, object]]:
        metodo = getattr(self._impl, "list_jobs", None)
        if metodo is None:
            itens: list[dict[str, object]] = []
            for job in self.pending[: max(0, int(limite))]:
                itens.append(
                    {
                        "id": job.id,
                        "fila": self.name,
                        "handler_ref": job.handler_ref or _handler_ref(job.handler),
                        "payload": job.payload,
                        "status": job.status,
                        "tentativas": job.attempts,
                        "tentativas_maximas": job.retries,
                        "timeout_segundos": job.timeout_seconds,
                        "chave_idempotencia": job.idempotency_key,
                        "ultimo_erro": job.last_error,
                        "backend": self.backend,
                    }
                )
            return itens
        return await metodo(limite, status)

    async def get_job(self, job_id: str) -> dict[str, object] | None:
        metodo = getattr(self._impl, "get_job", None)
        if metodo is None:
            return None
        return await metodo(job_id)

    async def reprocess_dlq(self, limite: int = 100) -> dict[str, object]:
        metodo = getattr(self._impl, "reprocess_dlq", None)
        if metodo is None:
            out = self.status()
            out["reprocessados"] = 0
            return out
        out = await metodo(limite)
        out.setdefault("backend", self.backend)
        return out

    def handlers_registrar(self, handlers: dict[str, object]) -> dict[str, object]:
        metodo = getattr(self._impl, "handlers_registrar", None)
        if metodo is None:
            return {"ok": False, "backend": self.backend, "fila": self.name, "handlers_registrados": 0}
        return metodo(handlers)


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
                    observability_runtime.registrar_runtime_metrica("webhook", "sucesso", labels={"status": status})
                    return {"ok": True, "status": status, "tentativa": i + 1, "resposta": body}
                last_error = f"status {status}"
        except urllib.error.HTTPError as exc:
            last_error = f"status {exc.code}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        observability_runtime.registrar_runtime_metrica("webhook", "falha_tentativa", labels={"tentativa": i + 1})
        await asyncio.sleep(min(0.25 * (2**i), 2.0))
    observability_runtime.registrar_runtime_metrica("webhook", "falha_final", labels={"tentativas": int(retries)})
    return {"ok": False, "erro": last_error, "tentativas": int(retries)}
