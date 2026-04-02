from __future__ import annotations

import asyncio
from pathlib import Path

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


def test_v201_orm_relacoes_paginacao_sqlite(tmp_path: Path) -> None:
    db_file = tmp_path / "v201_rel.db"
    conn = asyncio.run(db_runtime.conectar(f"sqlite:///{db_file}"))
    try:
        asyncio.run(
            db_runtime.executar(
                conn,
                "CREATE TABLE autores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL)",
            )
        )
        asyncio.run(
            db_runtime.executar(
                conn,
                "CREATE TABLE posts (id INTEGER PRIMARY KEY AUTOINCREMENT, autor_id INTEGER NOT NULL, titulo TEXT NOT NULL)",
            )
        )
        asyncio.run(
            db_runtime.executar(
                conn,
                "CREATE TABLE tags (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL)",
            )
        )
        asyncio.run(
            db_runtime.executar(
                conn,
                "CREATE TABLE post_tags (post_id INTEGER NOT NULL, tag_id INTEGER NOT NULL)",
            )
        )

        autor_id = asyncio.run(db_runtime.orm_inserir(conn, "autores", {"nome": "ana"}))
        p1 = asyncio.run(db_runtime.orm_inserir(conn, "posts", {"autor_id": autor_id, "titulo": "p1"}))
        p2 = asyncio.run(db_runtime.orm_inserir(conn, "posts", {"autor_id": autor_id, "titulo": "p2"}))
        t1 = asyncio.run(db_runtime.orm_inserir(conn, "tags", {"nome": "rpg"}))
        t2 = asyncio.run(db_runtime.orm_inserir(conn, "tags", {"nome": "backend"}))
        asyncio.run(db_runtime.executar(conn, "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)", [p1, t1]))
        asyncio.run(db_runtime.executar(conn, "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)", [p1, t2]))
        asyncio.run(db_runtime.executar(conn, "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)", [p2, t2]))

        modelo = db_runtime.orm_modelo("posts")
        modelo = db_runtime.orm_relacao_um_para_um(modelo, "autor", "autores", "autor_id", modo_relacao="eager")
        modelo = db_runtime.orm_relacao_muitos_para_muitos(
            modelo,
            "tags",
            "tags",
            "post_tags",
            "post_id",
            "tag_id",
        )
        lista = asyncio.run(
            db_runtime.orm_listar(
                conn,
                modelo,
                filtros={},
                opcoes={"pagina": 1, "limite": 1, "ordenacao": "id ASC", "preload": ["tags"]},
            )
        )
        assert len(lista["itens"]) == 1
        assert lista["paginacao"]["total"] == 2
        assert lista["itens"][0]["autor"]["nome"] == "ana"
        assert len(lista["itens"][0]["tags"]) >= 1
    finally:
        asyncio.run(db_runtime.fechar(conn))


def test_v201_constraints_diff_preview_aplicar(tmp_path: Path) -> None:
    db_file = tmp_path / "v201_schema.db"
    conn = asyncio.run(db_runtime.conectar(f"sqlite:///{db_file}"))
    try:
        usuarios = db_runtime.schema_definir_tabela(
            "usuarios",
            [
                {"nome": "id", "tipo": "INTEGER", "pk": True},
                {"nome": "email", "tipo": "TEXT", "nulo": False},
                {"nome": "idade", "tipo": "INTEGER", "nulo": False, "padrao": 0},
            ],
            constraints=[
                db_runtime.schema_constraint_unica(["email"], nome="uk_usuarios_email"),
                db_runtime.schema_constraint_check("idade >= 0", nome="chk_idade"),
            ],
        )
        perfis = db_runtime.schema_definir_tabela(
            "perfis",
            [
                {"nome": "id", "tipo": "INTEGER", "pk": True},
                {"nome": "usuario_id", "tipo": "INTEGER", "nulo": False},
                {"nome": "bio", "tipo": "TEXT", "nulo": True},
            ],
            constraints=[
                db_runtime.schema_constraint_fk(
                    ["usuario_id"],
                    "usuarios",
                    ["id"],
                    nome="fk_perfis_usuario",
                    on_delete="CASCADE",
                )
            ],
        )
        esperado = db_runtime.schema_definir([usuarios, perfis])
        atual = asyncio.run(db_runtime.schema_inspecionar(conn))
        diff = db_runtime.schema_diff(atual, esperado)
        preview = db_runtime.schema_preview_plano(diff)
        assert preview["total"] >= 2
        dry = asyncio.run(db_runtime.schema_aplicar_diff(conn, diff, dry_run=True))
        assert dry["dry_run"] is True
        apply_real = asyncio.run(db_runtime.schema_aplicar_diff(conn, diff, dry_run=False))
        assert apply_real["ok"] is True
        atual2 = asyncio.run(db_runtime.schema_inspecionar(conn))
        nomes = [t["nome"] for t in atual2["tabelas"]]
        assert "usuarios" in nomes
        assert "perfis" in nomes
    finally:
        asyncio.run(db_runtime.fechar(conn))


def test_v201_migracao_trilha_rollback_seed_ambiente(tmp_path: Path) -> None:
    db_file = tmp_path / "v201_mig.db"
    conn = asyncio.run(db_runtime.conectar(f"sqlite:///{db_file}"))
    try:
        ok = asyncio.run(
            db_runtime.migracao_aplicar_versionada_v2(
                conn,
                "201.001",
                "criar_t",
                "CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, nome TEXT);",
                "DROP TABLE IF EXISTS t;",
                ambiente="teste",
            )
        )
        assert ok["aplicada"] is True
        idem = asyncio.run(
            db_runtime.migracao_aplicar_versionada_v2(
                conn,
                "201.001",
                "criar_t",
                "CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, nome TEXT);",
                "DROP TABLE IF EXISTS t;",
                ambiente="teste",
            )
        )
        assert idem["aplicada"] is False
        trilha = asyncio.run(db_runtime.migracao_trilha_listar(conn, limite=10))
        assert len(trilha) >= 1

        seeds = asyncio.run(
            db_runtime.seed_aplicar_ambiente(
                conn,
                "teste",
                "base",
                [
                    {"nome": "002-b", "sql": "INSERT INTO t (id, nome) VALUES (2, 'b');"},
                    {"nome": "001-a", "sql": "INSERT INTO t (id, nome) VALUES (1, 'a');"},
                ],
            )
        )
        assert seeds["ok"] is True
        rows = asyncio.run(db_runtime.consultar(conn, "SELECT id, nome FROM t ORDER BY id ASC"))
        assert rows[0]["nome"] == "a"
        assert rows[1]["nome"] == "b"
    finally:
        asyncio.run(db_runtime.fechar(conn))
