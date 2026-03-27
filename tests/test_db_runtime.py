from __future__ import annotations

import asyncio

import pytest

from trama import db_runtime


def test_to_pg_placeholders_respeita_strings() -> None:
    sql = "SELECT * FROM t WHERE a = ? AND b = '?' AND c = ?"
    out = db_runtime._to_pg_placeholders(sql)
    assert out == "SELECT * FROM t WHERE a = $1 AND b = '?' AND c = $2"


def test_split_sql_statements() -> None:
    script = "CREATE TABLE x (a TEXT); INSERT INTO x (a) VALUES ('a;b');"
    parts = db_runtime._split_sql_statements(script)
    assert parts == [
        "CREATE TABLE x (a TEXT)",
        "INSERT INTO x (a) VALUES ('a;b')",
    ]


def test_conectar_postgres_sem_asyncpg_disponivel(monkeypatch) -> None:
    monkeypatch.setattr(db_runtime, "asyncpg", None)
    with pytest.raises(db_runtime.DbError, match="asyncpg"):
        asyncio.run(db_runtime.conectar("postgresql://u:p@localhost:5432/db"))


def test_conectar_postgres_com_asyncpg_fake(monkeypatch) -> None:
    class FakeTx:
        def __init__(self) -> None:
            self.started = False
            self.committed = False
            self.rolled = False

        async def start(self) -> None:
            self.started = True

        async def commit(self) -> None:
            self.committed = True

        async def rollback(self) -> None:
            self.rolled = True

    class FakeConn:
        def __init__(self) -> None:
            self.executed: list[tuple[str, tuple[object, ...]]] = []

        async def execute(self, sql: str, *params: object) -> str:
            self.executed.append((sql, params))
            return "UPDATE 1"

        async def fetch(self, sql: str, *params: object):
            self.executed.append((sql, params))
            return [{"id": 1, "nome": "x"}]

        def transaction(self) -> FakeTx:
            return FakeTx()

    class FakePool:
        def __init__(self) -> None:
            self.conn = FakeConn()
            self.closed = False

        async def acquire(self):
            return self.conn

        async def release(self, _conn) -> None:
            return None

        async def close(self) -> None:
            self.closed = True

    class FakeAsyncpg:
        @staticmethod
        async def create_pool(**_kwargs):
            return FakePool()

    monkeypatch.setattr(db_runtime, "asyncpg", FakeAsyncpg)

    conn = asyncio.run(db_runtime.conectar("postgresql://u:p@localhost:5432/db"))
    assert conn.backend == "postgres"

    out_exec = asyncio.run(db_runtime.executar(conn, "UPDATE t SET a = ? WHERE id = ?", [10, 1]))
    assert out_exec["rows_affected"] == 1

    out_query = asyncio.run(db_runtime.consultar(conn, "SELECT * FROM t WHERE id = ?", [1]))
    assert out_query[0]["id"] == 1

    tx = asyncio.run(db_runtime.transacao_iniciar(conn))
    asyncio.run(db_runtime.tx_executar(tx, "UPDATE t SET a = ? WHERE id = ?", [22, 1]))
    asyncio.run(db_runtime.transacao_commit(tx))

    asyncio.run(db_runtime.fechar(conn))
