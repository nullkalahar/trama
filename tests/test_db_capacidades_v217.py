from __future__ import annotations

import asyncio

from trama import db_runtime


def test_v217_backend_capacidades_basicas() -> None:
    caps_sqlite = db_runtime.backend_capacidades("sqlite")
    caps_pg = db_runtime.backend_capacidades("postgres")
    assert caps_sqlite["dialeto_sql"] == "sqlite"
    assert caps_pg["dialeto_sql"] == "postgresql"
    assert caps_sqlite["schema_drop_column"] is False
    assert caps_pg["schema_drop_column"] is True


def test_v214_schema_definir_com_dialeto() -> None:
    schema = db_runtime.schema_definir(
        [
            db_runtime.schema_definir_tabela(
                "usuarios",
                [{"nome": "id", "tipo": "INTEGER", "pk": True}],
            )
        ],
        dialeto_sql="postgresql",
    )
    assert schema["dialeto_sql"] == "postgresql"


def test_v216_schema_inspecionar_postgres_fake(monkeypatch) -> None:
    class FakeConn:
        async def execute(self, _sql: str, *_params: object) -> str:
            return "UPDATE 0"

        async def fetch(self, sql: str, *params: object):
            if "information_schema.tables" in sql:
                return [{"table_name": "usuarios"}]
            if "information_schema.columns" in sql:
                assert params == ("usuarios", "usuarios")
                return [
                    {
                        "column_name": "id",
                        "data_type": "integer",
                        "is_nullable": "NO",
                        "column_default": "nextval('usuarios_id_seq'::regclass)",
                        "is_pk": True,
                    },
                    {
                        "column_name": "nome",
                        "data_type": "text",
                        "is_nullable": "NO",
                        "column_default": None,
                        "is_pk": False,
                    },
                ]
            return []

        def transaction(self):
            class _Tx:
                async def start(self) -> None:
                    return None

                async def commit(self) -> None:
                    return None

                async def rollback(self) -> None:
                    return None

            return _Tx()

    class FakePool:
        def __init__(self) -> None:
            self.conn = FakeConn()

        async def acquire(self):
            return self.conn

        async def release(self, _conn) -> None:
            return None

        async def close(self) -> None:
            return None

    class FakeAsyncpg:
        @staticmethod
        async def create_pool(**_kwargs):
            return FakePool()

    monkeypatch.setattr(db_runtime, "asyncpg", FakeAsyncpg)
    conn = asyncio.run(db_runtime.conectar("postgresql://u:p@localhost:5432/db"))
    try:
        schema = asyncio.run(db_runtime.schema_inspecionar(conn))
        assert schema["backend"] == "postgres"
        assert schema["dialeto_sql"] == "postgresql"
        assert schema["tabelas"][0]["nome"] == "usuarios"
        assert schema["tabelas"][0]["colunas"][0]["pk"] is True
    finally:
        asyncio.run(db_runtime.fechar(conn))
