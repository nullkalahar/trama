"""Runtime de banco de dados para a linguagem trama (v0.6).

Implementação inicial de driver async + query builder/ORM e migrações/seed.
Nesta versão, o backend padrão usa SQLite como shim para desenvolvimento local.
DSN suportada:
- sqlite:///caminho/arquivo.db
- postgresql://... (mapeada para arquivo local via TRAMA_PG_SHIM_PATH)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import threading
from typing import Any


class DbError(RuntimeError):
    """Erro do runtime de banco de dados."""


@dataclass
class DbConnection:
    dsn: str
    sqlite_path: Path
    _conn: sqlite3.Connection = field(init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.sqlite_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def execute(self, sql: str, params: list[object] | tuple[object, ...] | None = None) -> dict[str, object]:
        with self._lock:
            cursor = self._conn.execute(sql, tuple(params or []))
            self._conn.commit()
            return {
                "rows_affected": int(cursor.rowcount if cursor.rowcount != -1 else 0),
                "last_row_id": int(cursor.lastrowid or 0),
            }

    def query(self, sql: str, params: list[object] | tuple[object, ...] | None = None) -> list[dict[str, object]]:
        with self._lock:
            cursor = self._conn.execute(sql, tuple(params or []))
            rows = cursor.fetchall()
        return [dict(r) for r in rows]


@dataclass
class DbTransaction:
    connection: DbConnection
    active: bool = True

    def ensure_active(self) -> None:
        if not self.active:
            raise DbError("Transação não está ativa.")


def _resolve_sqlite_path(dsn: str) -> Path:
    if dsn.startswith("sqlite:///"):
        return Path(dsn[len("sqlite:///") :]).resolve()

    if dsn.startswith("postgresql://") or dsn.startswith("postgres://"):
        shim = Path(
            Path.home().joinpath("trama_pg_shim.db")
            if "TRAMA_PG_SHIM_PATH" not in __import__("os").environ
            else __import__("os").environ["TRAMA_PG_SHIM_PATH"]
        )
        return shim.resolve()

    raise DbError(f"DSN não suportada: {dsn}")


async def conectar(dsn: str) -> DbConnection:
    path = _resolve_sqlite_path(dsn)
    return await asyncio.to_thread(DbConnection, dsn, path)


async def fechar(conn: DbConnection) -> None:
    await asyncio.to_thread(conn.close)


async def executar(
    conn: DbConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> dict[str, object]:
    return await asyncio.to_thread(conn.execute, sql, params)


async def consultar(
    conn: DbConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> list[dict[str, object]]:
    return await asyncio.to_thread(conn.query, sql, params)


async def transacao_iniciar(conn: DbConnection) -> DbTransaction:
    def _begin() -> DbTransaction:
        with conn._lock:
            conn._conn.execute("BEGIN")
        return DbTransaction(connection=conn, active=True)

    return await asyncio.to_thread(_begin)


async def transacao_commit(tx: DbTransaction) -> None:
    def _commit() -> None:
        tx.ensure_active()
        with tx.connection._lock:
            tx.connection._conn.commit()
        tx.active = False

    await asyncio.to_thread(_commit)


async def transacao_rollback(tx: DbTransaction) -> None:
    def _rollback() -> None:
        tx.ensure_active()
        with tx.connection._lock:
            tx.connection._conn.rollback()
        tx.active = False

    await asyncio.to_thread(_rollback)


async def tx_executar(
    tx: DbTransaction,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> dict[str, object]:
    def _exec() -> dict[str, object]:
        tx.ensure_active()
        with tx.connection._lock:
            cursor = tx.connection._conn.execute(sql, tuple(params or []))
            return {
                "rows_affected": int(cursor.rowcount if cursor.rowcount != -1 else 0),
                "last_row_id": int(cursor.lastrowid or 0),
            }

    return await asyncio.to_thread(_exec)


async def tx_consultar(
    tx: DbTransaction,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> list[dict[str, object]]:
    def _query() -> list[dict[str, object]]:
        tx.ensure_active()
        with tx.connection._lock:
            cursor = tx.connection._conn.execute(sql, tuple(params or []))
            rows = cursor.fetchall()
        return [dict(r) for r in rows]

    return await asyncio.to_thread(_query)


def qb_select(tabela: str, colunas: list[str] | None = None) -> dict[str, object]:
    return {
        "tabela": tabela,
        "colunas": list(colunas or ["*"]),
        "where": [],
        "params": [],
        "order_by": None,
        "limit": None,
    }


def qb_where_eq(query: dict[str, object], campo: str, valor: object) -> dict[str, object]:
    q = dict(query)
    where = list(q.get("where", []))
    where.append(f"{campo} = ?")
    q["where"] = where
    params = list(q.get("params", []))
    params.append(valor)
    q["params"] = params
    return q


def qb_order_by(query: dict[str, object], campo: str, direcao: str = "ASC") -> dict[str, object]:
    q = dict(query)
    q["order_by"] = f"{campo} {direcao.upper()}"
    return q


def qb_limite(query: dict[str, object], limite: int) -> dict[str, object]:
    q = dict(query)
    q["limit"] = int(limite)
    return q


def qb_sql(query: dict[str, object]) -> dict[str, object]:
    tabela = str(query["tabela"])
    colunas = list(query.get("colunas", ["*"]))
    sql = f"SELECT {', '.join(colunas)} FROM {tabela}"

    where = list(query.get("where", []))
    if where:
        sql += " WHERE " + " AND ".join(where)

    order_by = query.get("order_by")
    if order_by:
        sql += f" ORDER BY {order_by}"

    limit = query.get("limit")
    if limit is not None:
        sql += " LIMIT ?"
        params = list(query.get("params", [])) + [int(limit)]
    else:
        params = list(query.get("params", []))

    return {"sql": sql, "params": params}


async def qb_consultar(conn: DbConnection, query: dict[str, object]) -> list[dict[str, object]]:
    compiled = qb_sql(query)
    return await consultar(conn, str(compiled["sql"]), list(compiled["params"]))


async def orm_inserir(conn: DbConnection, tabela: str, dados: dict[str, object]) -> int:
    if not dados:
        raise DbError("orm_inserir exige dados.")
    cols = list(dados.keys())
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES ({placeholders})"
    res = await executar(conn, sql, [dados[c] for c in cols])
    return int(res["last_row_id"])


async def orm_atualizar(
    conn: DbConnection,
    tabela: str,
    dados: dict[str, object],
    where: dict[str, object],
) -> int:
    if not dados:
        raise DbError("orm_atualizar exige dados.")
    if not where:
        raise DbError("orm_atualizar exige filtro where.")

    set_cols = list(dados.keys())
    where_cols = list(where.keys())
    sql = (
        f"UPDATE {tabela} SET "
        + ", ".join([f"{c} = ?" for c in set_cols])
        + " WHERE "
        + " AND ".join([f"{c} = ?" for c in where_cols])
    )
    params = [dados[c] for c in set_cols] + [where[c] for c in where_cols]
    res = await executar(conn, sql, params)
    return int(res["rows_affected"])


async def orm_buscar_por_id(conn: DbConnection, tabela: str, id_value: object) -> dict[str, object] | None:
    rows = await consultar(conn, f"SELECT * FROM {tabela} WHERE id = ? LIMIT 1", [id_value])
    return rows[0] if rows else None


def _ensure_meta_tables(conn: DbConnection) -> None:
    with conn._lock:
        conn._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _trama_migrations (
                nome TEXT PRIMARY KEY,
                aplicado_em TEXT NOT NULL
            )
            """
        )
        conn._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _trama_seeds (
                nome TEXT PRIMARY KEY,
                aplicado_em TEXT NOT NULL
            )
            """
        )
        conn._conn.commit()


async def migracao_aplicar(conn: DbConnection, nome: str, sql: str) -> dict[str, object]:
    def _apply() -> dict[str, object]:
        _ensure_meta_tables(conn)
        with conn._lock:
            row = conn._conn.execute(
                "SELECT nome FROM _trama_migrations WHERE nome = ?",
                (nome,),
            ).fetchone()
            if row is not None:
                return {"aplicada": False, "nome": nome}

            conn._conn.execute("BEGIN")
            try:
                conn._conn.executescript(sql)
                conn._conn.execute(
                    "INSERT INTO _trama_migrations (nome, aplicado_em) VALUES (?, ?)",
                    (nome, datetime.now(timezone.utc).isoformat()),
                )
                conn._conn.commit()
            except Exception:
                conn._conn.rollback()
                raise

        return {"aplicada": True, "nome": nome}

    return await asyncio.to_thread(_apply)


async def seed_aplicar(conn: DbConnection, nome: str, sql: str) -> dict[str, object]:
    def _apply() -> dict[str, object]:
        _ensure_meta_tables(conn)
        with conn._lock:
            row = conn._conn.execute(
                "SELECT nome FROM _trama_seeds WHERE nome = ?",
                (nome,),
            ).fetchone()
            if row is not None:
                return {"aplicada": False, "nome": nome}

            conn._conn.execute("BEGIN")
            try:
                conn._conn.executescript(sql)
                conn._conn.execute(
                    "INSERT INTO _trama_seeds (nome, aplicado_em) VALUES (?, ?)",
                    (nome, datetime.now(timezone.utc).isoformat()),
                )
                conn._conn.commit()
            except Exception:
                conn._conn.rollback()
                raise

        return {"aplicada": True, "nome": nome}

    return await asyncio.to_thread(_apply)
