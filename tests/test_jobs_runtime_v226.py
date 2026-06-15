from __future__ import annotations

import asyncio
import sys
import types

import pytest

from trama.jobs_runtime import JobQueue, jobs_backends_listar


class _FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.lists: dict[str, list[str]] = {}
        self.sets: dict[str, set[str]] = {}
        self.zsets: dict[str, dict[str, float]] = {}

    @classmethod
    def from_url(cls, _url: str, decode_responses: bool = True):  # noqa: FBT001
        _ = decode_responses
        return cls()

    def ping(self) -> bool:
        return True

    def get(self, key: str):
        return self.kv.get(key)

    def set(self, key: str, value: str) -> bool:
        self.kv[key] = str(value)
        return True

    def incr(self, key: str) -> int:
        cur = int(self.kv.get(key, "0"))
        cur += 1
        self.kv[key] = str(cur)
        return cur

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        cur = dict(self.hashes.get(key, {}))
        for k, v in mapping.items():
            cur[str(k)] = str(v)
        self.hashes[key] = cur
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def sadd(self, key: str, *values: str) -> int:
        cur = self.sets.setdefault(key, set())
        for v in values:
            cur.add(str(v))
        return len(values)

    def smembers(self, key: str) -> set[str]:
        return set(self.sets.get(key, set()))

    def exists(self, key: str) -> int:
        return int(key in self.kv or key in self.hashes or key in self.lists or key in self.sets or key in self.zsets)

    def rpush(self, key: str, *values: str) -> int:
        cur = self.lists.setdefault(key, [])
        for v in values:
            cur.append(str(v))
        return len(cur)

    def lpop(self, key: str):
        cur = self.lists.setdefault(key, [])
        if not cur:
            return None
        return cur.pop(0)

    def lrange(self, key: str, start: int, stop: int) -> list[str]:
        cur = self.lists.setdefault(key, [])
        if stop < 0:
            stop = len(cur) - 1
        return list(cur[start : stop + 1])

    def llen(self, key: str) -> int:
        return len(self.lists.get(key, []))

    def lrem(self, key: str, count: int, value: str) -> int:
        cur = self.lists.setdefault(key, [])
        removidos = 0
        out: list[str] = []
        alvo = str(value)
        for item in cur:
            if item == alvo and removidos < max(0, int(count)):
                removidos += 1
                continue
            out.append(item)
        self.lists[key] = out
        return removidos

    def rpoplpush(self, source: str, destination: str):
        src = self.lists.setdefault(source, [])
        if not src:
            return None
        item = src.pop()
        self.lists.setdefault(destination, []).insert(0, item)
        return item

    def zadd(self, key: str, mapping: dict[str, float]) -> int:
        cur = self.zsets.setdefault(key, {})
        for k, v in mapping.items():
            cur[str(k)] = float(v)
        return len(mapping)

    def zrangebyscore(self, key: str, min_score: float, max_score: float) -> list[str]:
        cur = self.zsets.get(key, {})
        return [k for k, v in sorted(cur.items(), key=lambda item: item[1]) if float(min_score) <= float(v) <= float(max_score)]

    def zrem(self, key: str, member: str) -> int:
        cur = self.zsets.setdefault(key, {})
        return int(cur.pop(str(member), None) is not None)

    def zcard(self, key: str) -> int:
        return len(self.zsets.get(key, {}))


def _instalar_redis_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_mod = types.SimpleNamespace(Redis=_FakeRedis)
    monkeypatch.setitem(sys.modules, "redis", fake_mod)


def test_v226_backend_redis_disponivel(monkeypatch: pytest.MonkeyPatch) -> None:
    _instalar_redis_fake(monkeypatch)
    assert "redis" in jobs_backends_listar()


def test_v226_fila_redis_processa_e_reprocessa_dlq(monkeypatch: pytest.MonkeyPatch) -> None:
    _instalar_redis_fake(monkeypatch)
    chamadas = {"n": 0}

    def invoke(fn, args):
        return fn(*args)

    def job_ok(payload):
        chamadas["n"] += 1
        return payload["ok"]

    def job_falha(payload):
        chamadas["n"] += 1
        raise RuntimeError(f"erro:{payload['id']}")

    async def run():
        fila_ok = JobQueue(
            "v226_ok",
            invoke_callable_sync=invoke,
            backend="redis",
            backend_opcoes={"redis_url": "redis://fake/0"},
        )
        a = await fila_ok.enqueue(job_ok, {"ok": True}, retries=1, idempotency_key="ok-1")
        b = await fila_ok.enqueue(job_ok, {"ok": True}, retries=1, idempotency_key="ok-1")
        out_ok = await fila_ok.process_all()
        st_ok = await fila_ok.refresh_status()

        fila_dlq = JobQueue(
            "v226_dlq",
            invoke_callable_sync=invoke,
            backend="redis",
            backend_opcoes={"redis_url": "redis://fake/0"},
        )
        await fila_dlq.enqueue(job_falha, {"id": 7}, retries=0, idempotency_key="dlq-7")
        out_dlq = await fila_dlq.process_all()
        itens_dlq = await fila_dlq.list_dlq(10)
        rep = await fila_dlq.reprocess_dlq(10)
        out_dlq_2 = await fila_dlq.process_all()
        return a, b, out_ok, st_ok, out_dlq, itens_dlq, rep, out_dlq_2

    a, b, out_ok, st_ok, out_dlq, itens_dlq, rep, out_dlq_2 = asyncio.run(run())
    assert a["enfileirado"] is True
    assert b["idempotente"] is True
    assert out_ok["backend"] == "redis"
    assert out_ok["concluidos"] == 1
    assert st_ok["concluidos"] == 1
    assert out_dlq["dlq"] == 1
    assert itens_dlq[0]["status"] == "dlq"
    assert rep["reprocessados"] == 1
    assert out_dlq_2["dlq"] == 1
    assert chamadas["n"] >= 3
