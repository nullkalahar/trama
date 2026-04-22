"""Runtime de banco de dados para a linguagem trama (v0.6+).

Suporta backends:
- SQLite: `sqlite:///caminho/arquivo.db`
- PostgreSQL nativo: `postgres://...` ou `postgresql://...` (via asyncpg)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import threading
import time

from . import observability_runtime

try:
    import asyncpg  # type: ignore
except Exception:  # pragma: no cover - dependência opcional em tempo de execução
    asyncpg = None


class DbError(RuntimeError):
    """Erro do runtime de banco de dados."""


@dataclass
class DbConnection:
    dsn: str
    backend: str
    sqlite_path: Path | None = None
    sqlite_conn: sqlite3.Connection | None = None
    sqlite_lock: threading.Lock = field(default_factory=threading.Lock)
    pg_pool: object | None = None

    def close_sqlite(self) -> None:
        if self.sqlite_conn is None:
            return
        with self.sqlite_lock:
            self.sqlite_conn.close()


@dataclass
class DbTransaction:
    connection: DbConnection
    active: bool = True
    pg_conn: object | None = None
    pg_tx: object | None = None

    def ensure_active(self) -> None:
        if not self.active:
            raise DbError("Transação não está ativa.")


def _detect_backend(dsn: str) -> str:
    if dsn.startswith("sqlite:///"):
        return "sqlite"
    if dsn.startswith("postgresql://") or dsn.startswith("postgres://"):
        return "postgres"
    raise DbError(f"DSN não suportada: {dsn}")


def backend_capacidades(backend: str) -> dict[str, object]:
    b = str(backend).strip().lower()
    if b not in {"sqlite", "postgres"}:
        raise DbError(f"Backend não suportado para capabilities: {backend}")
    caps = {
        "backend": b,
        "dialeto_sql": "sqlite" if b == "sqlite" else "postgresql",
        "transacao": True,
        "migracao_versionada": True,
        "seed_ambiente": True,
        "schema_inspecao": True,
        "schema_diff_aplicar": True,
        "json_nativo": b == "postgres",
        "retorno_insert_id": True,
    }
    if b == "sqlite":
        caps["concorrencia_escrita"] = "serializada"
        caps["schema_drop_column"] = False
    else:
        caps["concorrencia_escrita"] = "multiconexao"
        caps["schema_drop_column"] = True
    return caps


def conexao_capacidades(conn: DbConnection) -> dict[str, object]:
    return backend_capacidades(conn.backend)


def _dialeto_backend(conn: DbConnection) -> str:
    return str(backend_capacidades(conn.backend).get("dialeto_sql", conn.backend))


def _resolve_sqlite_path(dsn: str) -> Path:
    return Path(dsn[len("sqlite:///") :]).resolve()


def _parse_tag_count(tag: str) -> int:
    # Ex.: "UPDATE 3", "INSERT 0 1", "DELETE 2"
    parts = tag.strip().split()
    for token in reversed(parts):
        if token.isdigit():
            return int(token)
    return 0


def _to_pg_placeholders(sql: str) -> str:
    # Converte ? em $1, $2... respeitando aspas simples/duplas.
    out: list[str] = []
    idx = 0
    in_single = False
    in_double = False

    i = 0
    while i < len(sql):
        ch = sql[i]

        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(ch)
            i += 1
            continue

        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            i += 1
            continue

        if ch == "?" and not in_single and not in_double:
            idx += 1
            out.append(f"${idx}")
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _split_sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False

    for ch in script:
        if ch == "'" and not in_double:
            in_single = not in_single
            current.append(ch)
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            current.append(ch)
            continue

        if ch == ";" and not in_single and not in_double:
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            continue

        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)

    return statements


async def conectar(dsn: str) -> DbConnection:
    backend = _detect_backend(dsn)

    if backend == "sqlite":
        path = _resolve_sqlite_path(dsn)

        def _open() -> DbConnection:
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return DbConnection(
                dsn=dsn,
                backend="sqlite",
                sqlite_path=path,
                sqlite_conn=conn,
            )

        return await asyncio.to_thread(_open)

    if asyncpg is None:
        raise DbError(
            "Driver PostgreSQL não disponível. Instale a dependência 'asyncpg' para usar DSN postgresql://"
        )

    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=10, command_timeout=30)
    return DbConnection(dsn=dsn, backend="postgres", pg_pool=pool)


async def fechar(conn: DbConnection) -> None:
    if conn.backend == "sqlite":
        await asyncio.to_thread(conn.close_sqlite)
        return

    if conn.pg_pool is not None:
        await conn.pg_pool.close()  # type: ignore[union-attr]


async def executar(
    conn: DbConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> dict[str, object]:
    inicio = time.perf_counter()
    params_seq = tuple(params or [])

    if conn.backend == "sqlite":
        if conn.sqlite_conn is None:
            raise DbError("Conexão SQLite inválida.")

        def _exec_sqlite() -> dict[str, object]:
            with conn.sqlite_lock:
                cursor = conn.sqlite_conn.execute(sql, params_seq)
                conn.sqlite_conn.commit()
                return {
                    "rows_affected": int(cursor.rowcount if cursor.rowcount != -1 else 0),
                    "last_row_id": int(cursor.lastrowid or 0),
                }

        try:
            out = await asyncio.to_thread(_exec_sqlite)
            observability_runtime.registrar_db_metrica(
                operacao="executar",
                backend=conn.backend,
                latencia_ms=(time.perf_counter() - inicio) * 1000.0,
                sucesso=True,
            )
            return out
        except Exception:
            observability_runtime.registrar_db_metrica(
                operacao="executar",
                backend=conn.backend,
                latencia_ms=(time.perf_counter() - inicio) * 1000.0,
                sucesso=False,
            )
            raise

    if conn.pg_pool is None:
        raise DbError("Conexão PostgreSQL inválida.")

    pg_conn = await conn.pg_pool.acquire()  # type: ignore[union-attr]
    try:
        pg_sql = _to_pg_placeholders(sql)
        tag = await pg_conn.execute(pg_sql, *params_seq)
        out = {"rows_affected": _parse_tag_count(tag), "last_row_id": 0}
        observability_runtime.registrar_db_metrica(
            operacao="executar",
            backend=conn.backend,
            latencia_ms=(time.perf_counter() - inicio) * 1000.0,
            sucesso=True,
        )
        return out
    except Exception:
        observability_runtime.registrar_db_metrica(
            operacao="executar",
            backend=conn.backend,
            latencia_ms=(time.perf_counter() - inicio) * 1000.0,
            sucesso=False,
        )
        raise
    finally:
        await conn.pg_pool.release(pg_conn)  # type: ignore[union-attr]


async def consultar(
    conn: DbConnection,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> list[dict[str, object]]:
    inicio = time.perf_counter()
    params_seq = tuple(params or [])

    if conn.backend == "sqlite":
        if conn.sqlite_conn is None:
            raise DbError("Conexão SQLite inválida.")

        def _query_sqlite() -> list[dict[str, object]]:
            with conn.sqlite_lock:
                cursor = conn.sqlite_conn.execute(sql, params_seq)
                rows = cursor.fetchall()
            return [dict(r) for r in rows]

        try:
            out = await asyncio.to_thread(_query_sqlite)
            observability_runtime.registrar_db_metrica(
                operacao="consultar",
                backend=conn.backend,
                latencia_ms=(time.perf_counter() - inicio) * 1000.0,
                sucesso=True,
            )
            return out
        except Exception:
            observability_runtime.registrar_db_metrica(
                operacao="consultar",
                backend=conn.backend,
                latencia_ms=(time.perf_counter() - inicio) * 1000.0,
                sucesso=False,
            )
            raise

    if conn.pg_pool is None:
        raise DbError("Conexão PostgreSQL inválida.")

    pg_conn = await conn.pg_pool.acquire()  # type: ignore[union-attr]
    try:
        pg_sql = _to_pg_placeholders(sql)
        rows = await pg_conn.fetch(pg_sql, *params_seq)
        out = [dict(r) for r in rows]
        observability_runtime.registrar_db_metrica(
            operacao="consultar",
            backend=conn.backend,
            latencia_ms=(time.perf_counter() - inicio) * 1000.0,
            sucesso=True,
        )
        return out
    except Exception:
        observability_runtime.registrar_db_metrica(
            operacao="consultar",
            backend=conn.backend,
            latencia_ms=(time.perf_counter() - inicio) * 1000.0,
            sucesso=False,
        )
        raise
    finally:
        await conn.pg_pool.release(pg_conn)  # type: ignore[union-attr]


async def transacao_iniciar(conn: DbConnection) -> DbTransaction:
    if conn.backend == "sqlite":
        if conn.sqlite_conn is None:
            raise DbError("Conexão SQLite inválida.")

        def _begin_sqlite() -> DbTransaction:
            with conn.sqlite_lock:
                conn.sqlite_conn.execute("BEGIN")
            return DbTransaction(connection=conn, active=True)

        return await asyncio.to_thread(_begin_sqlite)

    if conn.pg_pool is None:
        raise DbError("Conexão PostgreSQL inválida.")

    pg_conn = await conn.pg_pool.acquire()  # type: ignore[union-attr]
    tx = pg_conn.transaction()
    await tx.start()
    return DbTransaction(connection=conn, active=True, pg_conn=pg_conn, pg_tx=tx)


async def transacao_commit(tx: DbTransaction) -> None:
    tx.ensure_active()

    if tx.connection.backend == "sqlite":
        if tx.connection.sqlite_conn is None:
            raise DbError("Conexão SQLite inválida.")

        def _commit_sqlite() -> None:
            with tx.connection.sqlite_lock:
                tx.connection.sqlite_conn.commit()
            tx.active = False

        await asyncio.to_thread(_commit_sqlite)
        return

    if tx.pg_tx is None or tx.pg_conn is None or tx.connection.pg_pool is None:
        raise DbError("Transação PostgreSQL inválida.")

    try:
        await tx.pg_tx.commit()
    finally:
        await tx.connection.pg_pool.release(tx.pg_conn)  # type: ignore[union-attr]
        tx.active = False


async def transacao_rollback(tx: DbTransaction) -> None:
    tx.ensure_active()

    if tx.connection.backend == "sqlite":
        if tx.connection.sqlite_conn is None:
            raise DbError("Conexão SQLite inválida.")

        def _rollback_sqlite() -> None:
            with tx.connection.sqlite_lock:
                tx.connection.sqlite_conn.rollback()
            tx.active = False

        await asyncio.to_thread(_rollback_sqlite)
        return

    if tx.pg_tx is None or tx.pg_conn is None or tx.connection.pg_pool is None:
        raise DbError("Transação PostgreSQL inválida.")

    try:
        await tx.pg_tx.rollback()
    finally:
        await tx.connection.pg_pool.release(tx.pg_conn)  # type: ignore[union-attr]
        tx.active = False


async def tx_executar(
    tx: DbTransaction,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> dict[str, object]:
    tx.ensure_active()
    inicio = time.perf_counter()
    params_seq = tuple(params or [])

    if tx.connection.backend == "sqlite":
        if tx.connection.sqlite_conn is None:
            raise DbError("Conexão SQLite inválida.")

        def _exec_sqlite() -> dict[str, object]:
            with tx.connection.sqlite_lock:
                cursor = tx.connection.sqlite_conn.execute(sql, params_seq)
                return {
                    "rows_affected": int(cursor.rowcount if cursor.rowcount != -1 else 0),
                    "last_row_id": int(cursor.lastrowid or 0),
                }

        try:
            out = await asyncio.to_thread(_exec_sqlite)
            observability_runtime.registrar_db_metrica(
                operacao="tx_executar",
                backend=tx.connection.backend,
                latencia_ms=(time.perf_counter() - inicio) * 1000.0,
                sucesso=True,
            )
            return out
        except Exception:
            observability_runtime.registrar_db_metrica(
                operacao="tx_executar",
                backend=tx.connection.backend,
                latencia_ms=(time.perf_counter() - inicio) * 1000.0,
                sucesso=False,
            )
            raise

    if tx.pg_conn is None:
        raise DbError("Transação PostgreSQL inválida.")

    pg_sql = _to_pg_placeholders(sql)
    try:
        tag = await tx.pg_conn.execute(pg_sql, *params_seq)
        out = {"rows_affected": _parse_tag_count(tag), "last_row_id": 0}
        observability_runtime.registrar_db_metrica(
            operacao="tx_executar",
            backend=tx.connection.backend,
            latencia_ms=(time.perf_counter() - inicio) * 1000.0,
            sucesso=True,
        )
        return out
    except Exception:
        observability_runtime.registrar_db_metrica(
            operacao="tx_executar",
            backend=tx.connection.backend,
            latencia_ms=(time.perf_counter() - inicio) * 1000.0,
            sucesso=False,
        )
        raise


async def tx_consultar(
    tx: DbTransaction,
    sql: str,
    params: list[object] | tuple[object, ...] | None = None,
) -> list[dict[str, object]]:
    tx.ensure_active()
    inicio = time.perf_counter()
    params_seq = tuple(params or [])

    if tx.connection.backend == "sqlite":
        if tx.connection.sqlite_conn is None:
            raise DbError("Conexão SQLite inválida.")

        def _query_sqlite() -> list[dict[str, object]]:
            with tx.connection.sqlite_lock:
                cursor = tx.connection.sqlite_conn.execute(sql, params_seq)
                rows = cursor.fetchall()
            return [dict(r) for r in rows]

        try:
            out = await asyncio.to_thread(_query_sqlite)
            observability_runtime.registrar_db_metrica(
                operacao="tx_consultar",
                backend=tx.connection.backend,
                latencia_ms=(time.perf_counter() - inicio) * 1000.0,
                sucesso=True,
            )
            return out
        except Exception:
            observability_runtime.registrar_db_metrica(
                operacao="tx_consultar",
                backend=tx.connection.backend,
                latencia_ms=(time.perf_counter() - inicio) * 1000.0,
                sucesso=False,
            )
            raise

    if tx.pg_conn is None:
        raise DbError("Transação PostgreSQL inválida.")

    pg_sql = _to_pg_placeholders(sql)
    try:
        rows = await tx.pg_conn.fetch(pg_sql, *params_seq)
        out = [dict(r) for r in rows]
        observability_runtime.registrar_db_metrica(
            operacao="tx_consultar",
            backend=tx.connection.backend,
            latencia_ms=(time.perf_counter() - inicio) * 1000.0,
            sucesso=True,
        )
        return out
    except Exception:
        observability_runtime.registrar_db_metrica(
            operacao="tx_consultar",
            backend=tx.connection.backend,
            latencia_ms=(time.perf_counter() - inicio) * 1000.0,
            sucesso=False,
        )
        raise


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

    if conn.backend == "postgres":
        sql = f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES ({placeholders}) RETURNING id"
        rows = await consultar(conn, sql, [dados[c] for c in cols])
        if not rows or "id" not in rows[0]:
            raise DbError("INSERT sem retorno de id no PostgreSQL.")
        return int(rows[0]["id"])

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


async def _ensure_meta_tables(conn: DbConnection) -> None:
    await executar(
        conn,
        """
        CREATE TABLE IF NOT EXISTS _trama_migrations (
            nome TEXT PRIMARY KEY,
            aplicado_em TEXT NOT NULL
        )
        """,
    )
    await executar(
        conn,
        """
        CREATE TABLE IF NOT EXISTS _trama_seeds (
            nome TEXT PRIMARY KEY,
            aplicado_em TEXT NOT NULL
        )
        """,
    )
    await executar(
        conn,
        """
        CREATE TABLE IF NOT EXISTS _trama_migration_versions (
            versao TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            checksum TEXT NOT NULL,
            down_sql TEXT,
            aplicado_em TEXT NOT NULL
        )
        """,
    )
    await executar(
        conn,
        """
        CREATE TABLE IF NOT EXISTS _trama_migration_lock (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            owner TEXT NOT NULL,
            acquired_em TEXT NOT NULL
        )
        """,
    )


async def migracao_aplicar(conn: DbConnection, nome: str, sql: str) -> dict[str, object]:
    await _ensure_meta_tables(conn)

    existing = await consultar(
        conn,
        "SELECT nome FROM _trama_migrations WHERE nome = ? LIMIT 1",
        [nome],
    )
    if existing:
        return {"aplicada": False, "nome": nome}

    tx = await transacao_iniciar(conn)
    try:
        for stmt in _split_sql_statements(sql):
            await tx_executar(tx, stmt)

        await tx_executar(
            tx,
            "INSERT INTO _trama_migrations (nome, aplicado_em) VALUES (?, ?)",
            [nome, datetime.now(timezone.utc).isoformat()],
        )
        await transacao_commit(tx)
    except Exception:
        if tx.active:
            await transacao_rollback(tx)
        raise

    return {"aplicada": True, "nome": nome}


async def seed_aplicar(conn: DbConnection, nome: str, sql: str) -> dict[str, object]:
    await _ensure_meta_tables(conn)

    existing = await consultar(
        conn,
        "SELECT nome FROM _trama_seeds WHERE nome = ? LIMIT 1",
        [nome],
    )
    if existing:
        return {"aplicada": False, "nome": nome}

    tx = await transacao_iniciar(conn)
    try:
        for stmt in _split_sql_statements(sql):
            await tx_executar(tx, stmt)

        await tx_executar(
            tx,
            "INSERT INTO _trama_seeds (nome, aplicado_em) VALUES (?, ?)",
            [nome, datetime.now(timezone.utc).isoformat()],
        )
        await transacao_commit(tx)
    except Exception:
        if tx.active:
            await transacao_rollback(tx)
        raise

    return {"aplicada": True, "nome": nome}


def _sql_checksum(sql: str) -> str:
    import hashlib

    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


async def migracao_aplicar_versionada(
    conn: DbConnection,
    versao: str,
    nome: str,
    up_sql: str,
    down_sql: str = "",
    dry_run: bool = False,
    lock_owner: str = "trama",
) -> dict[str, object]:
    await _ensure_meta_tables(conn)
    checksum = _sql_checksum(up_sql)
    existing = await consultar(
        conn,
        "SELECT versao, checksum FROM _trama_migration_versions WHERE versao = ? LIMIT 1",
        [versao],
    )
    if existing:
        old_checksum = str(existing[0]["checksum"])
        if old_checksum != checksum:
            raise DbError(
                f"Migração {versao} já aplicada com checksum diferente. Evolução de schema insegura."
            )
        return {"aplicada": False, "versao": versao, "nome": nome}

    lock_token = f"{lock_owner}:{datetime.now(timezone.utc).isoformat()}"
    lock_acquired = False
    try:
        try:
            await executar(
                conn,
                "INSERT INTO _trama_migration_lock (id, owner, acquired_em) VALUES (1, ?, ?)",
                [lock_token, datetime.now(timezone.utc).isoformat()],
            )
            lock_acquired = True
        except Exception as exc:  # noqa: BLE001
            raise DbError("Lock de migração indisponível: outra migração em execução.") from exc

        tx = await transacao_iniciar(conn)
        try:
            for stmt in _split_sql_statements(up_sql):
                await tx_executar(tx, stmt)
            if dry_run:
                await transacao_rollback(tx)
                return {"aplicada": False, "dry_run": True, "versao": versao, "nome": nome}
            await tx_executar(
                tx,
                "INSERT INTO _trama_migration_versions (versao, nome, checksum, down_sql, aplicado_em) VALUES (?, ?, ?, ?, ?)",
                [versao, nome, checksum, down_sql, datetime.now(timezone.utc).isoformat()],
            )
            await transacao_commit(tx)
        except Exception:
            if tx.active:
                await transacao_rollback(tx)
            raise
        return {"aplicada": True, "versao": versao, "nome": nome}
    finally:
        if lock_acquired:
            try:
                await executar(conn, "DELETE FROM _trama_migration_lock WHERE id = 1")
            except Exception:
                pass


async def migracao_status(conn: DbConnection) -> list[dict[str, object]]:
    await _ensure_meta_tables(conn)
    rows = await consultar(
        conn,
        "SELECT versao, nome, checksum, aplicado_em FROM _trama_migration_versions ORDER BY versao ASC",
    )
    return rows


async def migracao_validar_compatibilidade(
    conn: DbConnection,
    versao: str,
    up_sql: str,
) -> dict[str, object]:
    await _ensure_meta_tables(conn)
    checksum = _sql_checksum(up_sql)
    rows = await consultar(
        conn,
        "SELECT checksum FROM _trama_migration_versions WHERE versao = ? LIMIT 1",
        [versao],
    )
    if not rows:
        return {"ok": True, "aplicada": False, "versao": versao}
    old_checksum = str(rows[0]["checksum"])
    if old_checksum != checksum:
        return {
            "ok": False,
            "aplicada": True,
            "versao": versao,
            "erro": "checksum_diferente",
        }
    return {"ok": True, "aplicada": True, "versao": versao}


async def migracao_reverter_ultima(conn: DbConnection) -> dict[str, object]:
    await _ensure_meta_tables(conn)
    rows = await consultar(
        conn,
        "SELECT versao, nome, down_sql FROM _trama_migration_versions ORDER BY versao DESC LIMIT 1",
    )
    if not rows:
        return {"revertida": False, "motivo": "sem_migracoes"}
    row = rows[0]
    down_sql = str(row.get("down_sql") or "")
    if not down_sql.strip():
        raise DbError(f"Migração {row['versao']} não possui down_sql para rollback.")

    tx = await transacao_iniciar(conn)
    try:
        for stmt in _split_sql_statements(down_sql):
            await tx_executar(tx, stmt)
        await tx_executar(
            tx,
            "DELETE FROM _trama_migration_versions WHERE versao = ?",
            [row["versao"]],
        )
        await transacao_commit(tx)
    except Exception:
        if tx.active:
            await transacao_rollback(tx)
        raise
    return {"revertida": True, "versao": row["versao"], "nome": row["nome"]}


def _nome_identificador_valido(nome: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nome))


def _escapar_identificador(nome: str) -> str:
    if not _nome_identificador_valido(nome):
        raise DbError(f"Identificador inválido: {nome}")
    return nome


def orm_modelo(tabela: str, chave_primaria: str = "id") -> dict[str, object]:
    return {
        "tabela": _escapar_identificador(str(tabela)),
        "chave_primaria": _escapar_identificador(str(chave_primaria)),
        "relacoes": {},
    }


def _normalizar_modo_relacao(modo: str) -> str:
    m = str(modo).strip().lower()
    if m not in {"lazy", "eager"}:
        raise DbError("modo_relacao inválido: use 'lazy' ou 'eager'.")
    return m


def _anexar_relacao(modelo: dict[str, object], nome: str, spec: dict[str, object]) -> dict[str, object]:
    if not isinstance(modelo, dict) or "tabela" not in modelo:
        raise DbError("modelo ORM inválido.")
    out = dict(modelo)
    rels = dict(out.get("relacoes", {}))
    rels[str(nome)] = spec
    out["relacoes"] = rels
    return out


def orm_relacao_um_para_um(
    modelo: dict[str, object],
    nome_relacao: str,
    tabela_alvo: str,
    fk_local: str,
    pk_alvo: str = "id",
    modo_relacao: str = "lazy",
) -> dict[str, object]:
    return _anexar_relacao(
        modelo,
        nome_relacao,
        {
            "tipo": "um_para_um",
            "tabela_alvo": _escapar_identificador(str(tabela_alvo)),
            "fk_local": _escapar_identificador(str(fk_local)),
            "pk_alvo": _escapar_identificador(str(pk_alvo)),
            "modo": _normalizar_modo_relacao(modo_relacao),
        },
    )


def orm_relacao_um_para_muitos(
    modelo: dict[str, object],
    nome_relacao: str,
    tabela_alvo: str,
    fk_no_alvo: str,
    pk_local: str = "id",
    modo_relacao: str = "lazy",
) -> dict[str, object]:
    return _anexar_relacao(
        modelo,
        nome_relacao,
        {
            "tipo": "um_para_muitos",
            "tabela_alvo": _escapar_identificador(str(tabela_alvo)),
            "fk_no_alvo": _escapar_identificador(str(fk_no_alvo)),
            "pk_local": _escapar_identificador(str(pk_local)),
            "modo": _normalizar_modo_relacao(modo_relacao),
        },
    )


def orm_relacao_muitos_para_muitos(
    modelo: dict[str, object],
    nome_relacao: str,
    tabela_alvo: str,
    tabela_juncao: str,
    fk_local_juncao: str,
    fk_alvo_juncao: str,
    pk_local: str = "id",
    pk_alvo: str = "id",
    modo_relacao: str = "lazy",
) -> dict[str, object]:
    return _anexar_relacao(
        modelo,
        nome_relacao,
        {
            "tipo": "muitos_para_muitos",
            "tabela_alvo": _escapar_identificador(str(tabela_alvo)),
            "tabela_juncao": _escapar_identificador(str(tabela_juncao)),
            "fk_local_juncao": _escapar_identificador(str(fk_local_juncao)),
            "fk_alvo_juncao": _escapar_identificador(str(fk_alvo_juncao)),
            "pk_local": _escapar_identificador(str(pk_local)),
            "pk_alvo": _escapar_identificador(str(pk_alvo)),
            "modo": _normalizar_modo_relacao(modo_relacao),
        },
    )


def _normalizar_ordenacao(ordenacao: object, padrao_coluna: str) -> str:
    if not ordenacao:
        return f"{_escapar_identificador(padrao_coluna)} ASC"
    ordem = str(ordenacao).strip().split()
    col = _escapar_identificador(ordem[0])
    direcao = "ASC"
    if len(ordem) > 1:
        d = ordem[1].upper()
        if d not in {"ASC", "DESC"}:
            raise DbError("Direção de ordenação inválida.")
        direcao = d
    return f"{col} {direcao}"


async def orm_listar(
    conn: DbConnection,
    modelo: dict[str, object],
    filtros: dict[str, object] | None = None,
    opcoes: dict[str, object] | None = None,
) -> dict[str, object]:
    if not isinstance(modelo, dict):
        raise DbError("modelo ORM inválido.")
    tabela = _escapar_identificador(str(modelo.get("tabela", "")))
    pk = _escapar_identificador(str(modelo.get("chave_primaria", "id")))
    filtros = dict(filtros or {})
    opcoes = dict(opcoes or {})

    pagina = max(int(opcoes.get("pagina", 1)), 1)
    limite = max(min(int(opcoes.get("limite", 50)), 500), 1)
    cursor = opcoes.get("cursor")
    ordenacao = _normalizar_ordenacao(opcoes.get("ordenacao"), pk)
    preload_in = opcoes.get("preload", [])
    preload = [str(x) for x in preload_in] if isinstance(preload_in, list) else []
    incluir_lazy = bool(opcoes.get("incluir_lazy", False))

    where_parts: list[str] = []
    params: list[object] = []
    for campo, valor in filtros.items():
        col = _escapar_identificador(str(campo))
        where_parts.append(f"{col} = ?")
        params.append(valor)

    if cursor is not None:
        where_parts.append(f"{pk} > ?")
        params.append(cursor)

    where_sql = ""
    if where_parts:
        where_sql = " WHERE " + " AND ".join(where_parts)

    total_rows = await consultar(conn, f"SELECT COUNT(*) AS c FROM {tabela}{where_sql}", params)
    total = int(total_rows[0]["c"]) if total_rows else 0

    offset = (pagina - 1) * limite
    sql = f"SELECT * FROM {tabela}{where_sql} ORDER BY {ordenacao} LIMIT ? OFFSET ?"
    itens = await consultar(conn, sql, params + [limite, offset])

    relacoes = dict(modelo.get("relacoes", {}))
    if relacoes:
        for item in itens:
            for nome_rel, spec_obj in relacoes.items():
                if not isinstance(spec_obj, dict):
                    continue
                modo = str(spec_obj.get("modo", "lazy"))
                deve_carregar = (nome_rel in preload) or (modo == "eager") or incluir_lazy
                if not deve_carregar:
                    item[nome_rel] = {"carregado": False, "modo": modo}
                    continue
                item[nome_rel] = await _orm_carregar_relacao(conn, item, spec_obj)

    prox_cursor = itens[-1].get(pk) if itens else None
    return {
        "itens": itens,
        "paginacao": {
            "pagina": pagina,
            "limite": limite,
            "total": total,
            "total_paginas": max((total + limite - 1) // limite, 1) if total > 0 else 0,
            "cursor_atual": cursor,
            "proximo_cursor": prox_cursor,
        },
    }


async def _orm_carregar_relacao(
    conn: DbConnection,
    item_base: dict[str, object],
    spec: dict[str, object],
) -> object:
    tipo = str(spec.get("tipo", ""))
    if tipo == "um_para_um":
        tabela = _escapar_identificador(str(spec["tabela_alvo"]))
        fk_local = _escapar_identificador(str(spec["fk_local"]))
        pk_alvo = _escapar_identificador(str(spec.get("pk_alvo", "id")))
        valor = item_base.get(fk_local)
        if valor is None:
            return None
        rows = await consultar(conn, f"SELECT * FROM {tabela} WHERE {pk_alvo} = ? LIMIT 1", [valor])
        return rows[0] if rows else None
    if tipo == "um_para_muitos":
        tabela = _escapar_identificador(str(spec["tabela_alvo"]))
        fk_no_alvo = _escapar_identificador(str(spec["fk_no_alvo"]))
        pk_local = _escapar_identificador(str(spec.get("pk_local", "id")))
        valor = item_base.get(pk_local)
        if valor is None:
            return []
        return await consultar(conn, f"SELECT * FROM {tabela} WHERE {fk_no_alvo} = ?", [valor])
    if tipo == "muitos_para_muitos":
        tabela_alvo = _escapar_identificador(str(spec["tabela_alvo"]))
        tabela_juncao = _escapar_identificador(str(spec["tabela_juncao"]))
        fk_local_juncao = _escapar_identificador(str(spec["fk_local_juncao"]))
        fk_alvo_juncao = _escapar_identificador(str(spec["fk_alvo_juncao"]))
        pk_local = _escapar_identificador(str(spec.get("pk_local", "id")))
        pk_alvo = _escapar_identificador(str(spec.get("pk_alvo", "id")))
        valor = item_base.get(pk_local)
        if valor is None:
            return []
        sql = (
            f"SELECT a.* FROM {tabela_alvo} a "
            f"INNER JOIN {tabela_juncao} j ON a.{pk_alvo} = j.{fk_alvo_juncao} "
            f"WHERE j.{fk_local_juncao} = ?"
        )
        return await consultar(conn, sql, [valor])
    raise DbError(f"Tipo de relação ORM não suportado: {tipo}")


def schema_constraint_unica(colunas: list[str], nome: str | None = None) -> dict[str, object]:
    if not colunas:
        raise DbError("Constraint única exige ao menos uma coluna.")
    return {"tipo": "unica", "nome": nome, "colunas": [_escapar_identificador(c) for c in colunas]}


def schema_constraint_fk(
    colunas: list[str],
    tabela_referencia: str,
    colunas_referencia: list[str],
    nome: str | None = None,
    on_delete: str = "NO ACTION",
    on_update: str = "NO ACTION",
) -> dict[str, object]:
    if not colunas or not colunas_referencia or len(colunas) != len(colunas_referencia):
        raise DbError("FK inválida: colunas locais/referência incompatíveis.")
    return {
        "tipo": "fk",
        "nome": nome,
        "colunas": [_escapar_identificador(c) for c in colunas],
        "tabela_referencia": _escapar_identificador(tabela_referencia),
        "colunas_referencia": [_escapar_identificador(c) for c in colunas_referencia],
        "on_delete": str(on_delete).upper(),
        "on_update": str(on_update).upper(),
    }


def schema_constraint_check(expressao: str, nome: str | None = None) -> dict[str, object]:
    expr = str(expressao).strip()
    if not expr:
        raise DbError("CHECK inválido: expressão vazia.")
    return {"tipo": "check", "nome": nome, "expressao": expr}


def schema_definir_tabela(
    nome: str,
    colunas: list[dict[str, object]],
    constraints: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if not colunas:
        raise DbError("Tabela exige ao menos uma coluna.")
    return {
        "nome": _escapar_identificador(nome),
        "colunas": colunas,
        "constraints": list(constraints or []),
    }


def schema_definir(colunas_tabelas: list[dict[str, object]], dialeto_sql: str = "") -> dict[str, object]:
    tabelas = sorted(colunas_tabelas, key=lambda t: str(t.get("nome", "")))
    out = {"tabelas": tabelas}
    if str(dialeto_sql).strip():
        out["dialeto_sql"] = str(dialeto_sql).strip()
    return out


def _render_coluna_sql(col: dict[str, object], *, dialeto: str = "sqlite") -> str:
    nome = _escapar_identificador(str(col["nome"]))
    tipo = str(col.get("tipo", "TEXT")).upper()
    nullable = bool(col.get("nulo", True))
    pk = bool(col.get("pk", False))
    auto = bool(col.get("auto_incremento", False))
    default = col.get("padrao")
    dialeto_norm = str(dialeto).lower()

    if dialeto_norm == "postgresql" and auto and tipo in {"INTEGER", "INT"}:
        tipo = "SERIAL"

    parts = [nome, tipo]
    if pk:
        parts.append("PRIMARY KEY")
    if auto and tipo == "INTEGER" and dialeto_norm == "sqlite":
        parts.append("AUTOINCREMENT")
    if not nullable:
        parts.append("NOT NULL")
    if default is not None:
        if isinstance(default, str):
            parts.append(f"DEFAULT '{default}'")
        else:
            parts.append(f"DEFAULT {default}")
    return " ".join(parts)


def _render_constraint_sql(c: dict[str, object]) -> str:
    tipo = str(c.get("tipo", "")).lower()
    nome = c.get("nome")
    prefix = f"CONSTRAINT {_escapar_identificador(str(nome))} " if nome else ""
    if tipo == "unica":
        cols = ", ".join(_escapar_identificador(x) for x in list(c.get("colunas", [])))
        return f"{prefix}UNIQUE ({cols})"
    if tipo == "fk":
        cols = ", ".join(_escapar_identificador(x) for x in list(c.get("colunas", [])))
        ref_table = _escapar_identificador(str(c.get("tabela_referencia", "")))
        ref_cols = ", ".join(_escapar_identificador(x) for x in list(c.get("colunas_referencia", [])))
        on_delete = str(c.get("on_delete", "NO ACTION")).upper()
        on_update = str(c.get("on_update", "NO ACTION")).upper()
        return (
            f"{prefix}FOREIGN KEY ({cols}) REFERENCES {ref_table} ({ref_cols}) "
            f"ON DELETE {on_delete} ON UPDATE {on_update}"
        )
    if tipo == "check":
        expr = str(c.get("expressao", "")).strip()
        if not expr:
            raise DbError("CHECK inválido: expressão vazia.")
        return f"{prefix}CHECK ({expr})"
    raise DbError(f"Constraint não suportada: {tipo}")


async def schema_inspecionar(conn: DbConnection) -> dict[str, object]:
    if conn.backend == "sqlite":
        tables = await consultar(
            conn,
            "SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name ASC",
        )
        out_tables: list[dict[str, object]] = []
        for t in tables:
            nome = str(t["name"])
            pragma_cols = await consultar(conn, f"PRAGMA table_info({nome})")
            colunas = []
            for c in pragma_cols:
                colunas.append(
                    {
                        "nome": c["name"],
                        "tipo": c["type"],
                        "nulo": not bool(c["notnull"]),
                        "pk": bool(c["pk"]),
                        "padrao": c["dflt_value"],
                    }
                )
            out_tables.append({"nome": nome, "colunas": colunas, "sql": t.get("sql")})
        return {"backend": conn.backend, "dialeto_sql": _dialeto_backend(conn), "tabelas": out_tables}

    if conn.backend == "postgres":
        tabelas_rows = await consultar(
            conn,
            (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                "ORDER BY table_name ASC"
            ),
        )
        out_tables: list[dict[str, object]] = []
        for tr in tabelas_rows:
            nome = str(tr["table_name"])
            cols_rows = await consultar(
                conn,
                (
                    "SELECT c.column_name, c.data_type, c.is_nullable, c.column_default, "
                    "COALESCE(k.is_pk, FALSE) AS is_pk "
                    "FROM information_schema.columns c "
                    "LEFT JOIN ("
                    "  SELECT kcu.column_name, TRUE AS is_pk "
                    "  FROM information_schema.table_constraints tc "
                    "  JOIN information_schema.key_column_usage kcu "
                    "    ON tc.constraint_name = kcu.constraint_name "
                    "   AND tc.table_schema = kcu.table_schema "
                    "   AND tc.table_name = kcu.table_name "
                    "  WHERE tc.table_schema = 'public' "
                    "    AND tc.table_name = ? "
                    "    AND tc.constraint_type = 'PRIMARY KEY'"
                    ") k ON k.column_name = c.column_name "
                    "WHERE c.table_schema = 'public' AND c.table_name = ? "
                    "ORDER BY c.ordinal_position ASC"
                ),
                [nome, nome],
            )
            colunas = [
                {
                    "nome": c["column_name"],
                    "tipo": c["data_type"],
                    "nulo": str(c["is_nullable"]).upper() == "YES",
                    "pk": bool(c.get("is_pk")),
                    "padrao": c.get("column_default"),
                }
                for c in cols_rows
            ]
            out_tables.append({"nome": nome, "colunas": colunas, "sql": None})
        return {"backend": conn.backend, "dialeto_sql": _dialeto_backend(conn), "tabelas": out_tables}

    caps = backend_capacidades(conn.backend)
    raise DbError(
        f"schema_inspecionar indisponível para backend '{conn.backend}'. "
        f"Capabilities: {json.dumps(caps, ensure_ascii=False, sort_keys=True)}"
    )


def schema_diff(schema_atual: dict[str, object], schema_esperado: dict[str, object]) -> dict[str, object]:
    dialeto_atual = str(schema_atual.get("dialeto_sql", "") or "")
    dialeto_esperado = str(schema_esperado.get("dialeto_sql", "") or "")
    atual_map = {str(t["nome"]): t for t in list(schema_atual.get("tabelas", []))}
    esperado_map = {str(t["nome"]): t for t in list(schema_esperado.get("tabelas", []))}
    plano: list[dict[str, object]] = []

    for nome in sorted(esperado_map.keys()):
        dst = esperado_map[nome]
        if nome not in atual_map:
            plano.append({"acao": "criar_tabela", "tabela": nome, "definicao": dst})
            continue
        atual_cols = {str(c["nome"]): c for c in list(atual_map[nome].get("colunas", []))}
        dst_cols = {str(c["nome"]): c for c in list(dst.get("colunas", []))}
        for c_nome in sorted(dst_cols.keys()):
            if c_nome not in atual_cols:
                plano.append({"acao": "adicionar_coluna", "tabela": nome, "coluna": dst_cols[c_nome]})
    for nome in sorted(atual_map.keys()):
        if nome not in esperado_map:
            plano.append({"acao": "remover_tabela", "tabela": nome})

    return {
        "passos": plano,
        "dialeto_atual": dialeto_atual,
        "dialeto_esperado": dialeto_esperado,
        "resumo": {"total_passos": len(plano)},
    }


def schema_preview_plano(diff: dict[str, object]) -> dict[str, object]:
    passos = list(diff.get("passos", []))
    linhas: list[str] = []
    for i, p in enumerate(passos, start=1):
        linhas.append(f"{i:03d} | {p.get('acao')} | {p.get('tabela')}")
    return {"ok": True, "linhas": linhas, "total": len(passos)}


async def schema_aplicar_diff(
    conn: DbConnection,
    diff: dict[str, object],
    dry_run: bool = False,
) -> dict[str, object]:
    if not bool(conexao_capacidades(conn).get("schema_diff_aplicar", False)):
        raise DbError(f"Backend '{conn.backend}' não suporta aplicação de schema diff.")
    passos = list(diff.get("passos", []))
    executados = 0
    dialeto = _dialeto_backend(conn)
    tx = await transacao_iniciar(conn)
    try:
        for passo in passos:
            acao = str(passo.get("acao"))
            tabela = _escapar_identificador(str(passo.get("tabela", "")))
            if acao == "criar_tabela":
                definicao = dict(passo.get("definicao", {}))
                colunas = list(definicao.get("colunas", []))
                constraints = list(definicao.get("constraints", []))
                parts = [_render_coluna_sql(c, dialeto=dialeto) for c in colunas]
                parts.extend(_render_constraint_sql(c) for c in constraints)
                sql = f"CREATE TABLE IF NOT EXISTS {tabela} ({', '.join(parts)})"
                await tx_executar(tx, sql)
                executados += 1
            elif acao == "adicionar_coluna":
                col = dict(passo.get("coluna", {}))
                sql = f"ALTER TABLE {tabela} ADD COLUMN {_render_coluna_sql(col, dialeto=dialeto)}"
                await tx_executar(tx, sql)
                executados += 1
            elif acao == "remover_tabela":
                await tx_executar(tx, f"DROP TABLE IF EXISTS {tabela}")
                executados += 1
            else:
                raise DbError(f"Ação de diff não suportada: {acao}")
        if dry_run:
            await transacao_rollback(tx)
            return {"ok": True, "dry_run": True, "passos_executados": executados}
        await transacao_commit(tx)
        return {"ok": True, "dry_run": False, "passos_executados": executados}
    except Exception:
        if tx.active:
            await transacao_rollback(tx)
        raise


async def _ensure_meta_tables_v201(conn: DbConnection) -> None:
    await _ensure_meta_tables(conn)
    id_tipo = "INTEGER PRIMARY KEY AUTOINCREMENT" if conn.backend == "sqlite" else "BIGSERIAL PRIMARY KEY"
    await executar(
        conn,
        f"""
        CREATE TABLE IF NOT EXISTS _trama_migration_runs (
            id {id_tipo},
            versao TEXT,
            nome TEXT NOT NULL,
            ambiente TEXT NOT NULL DEFAULT 'dev',
            checksum TEXT,
            plano_json TEXT,
            status TEXT NOT NULL,
            erro_json TEXT,
            criado_em TEXT NOT NULL,
            finalizado_em TEXT
        )
        """,
    )
    await executar(
        conn,
        """
        CREATE TABLE IF NOT EXISTS _trama_seeds_ambiente (
            ambiente TEXT NOT NULL,
            nome TEXT NOT NULL,
            aplicado_em TEXT NOT NULL,
            PRIMARY KEY (ambiente, nome)
        )
        """,
    )


async def _registrar_trilha_migracao(
    conn: DbConnection,
    versao: str,
    nome: str,
    ambiente: str,
    checksum: str,
    plano: dict[str, object],
    status: str,
    erro: dict[str, object] | None = None,
) -> None:
    await executar(
        conn,
        (
            "INSERT INTO _trama_migration_runs "
            "(versao, nome, ambiente, checksum, plano_json, status, erro_json, criado_em, finalizado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        [
            versao,
            nome,
            ambiente,
            checksum,
            json.dumps(plano, ensure_ascii=False, sort_keys=True),
            status,
            json.dumps(erro or {}, ensure_ascii=False, sort_keys=True) if erro else None,
            datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat(),
        ],
    )


async def migracao_aplicar_versionada_v2(
    conn: DbConnection,
    versao: str,
    nome: str,
    up_sql: str,
    down_sql: str = "",
    ambiente: str = "dev",
    dry_run: bool = False,
    lock_owner: str = "trama",
) -> dict[str, object]:
    await _ensure_meta_tables_v201(conn)
    checksum = _sql_checksum(up_sql)
    plano = {"up_sql": up_sql, "down_sql": down_sql, "dry_run": dry_run}
    try:
        result = await migracao_aplicar_versionada(
            conn,
            versao,
            nome,
            up_sql,
            down_sql,
            dry_run=dry_run,
            lock_owner=lock_owner,
        )
        await _registrar_trilha_migracao(
            conn,
            versao=versao,
            nome=nome,
            ambiente=ambiente,
            checksum=checksum,
            plano=plano,
            status="ok" if bool(result.get("aplicada")) else "ignorada",
        )
        result["ambiente"] = ambiente
        return result
    except Exception as exc:
        await _registrar_trilha_migracao(
            conn,
            versao=versao,
            nome=nome,
            ambiente=ambiente,
            checksum=checksum,
            plano=plano,
            status="falha",
            erro={"codigo": "MIGRACAO_FALHOU", "mensagem": str(exc), "detalhes": {"versao": versao}},
        )
        raise


async def migracao_trilha_listar(conn: DbConnection, limite: int = 100) -> list[dict[str, object]]:
    await _ensure_meta_tables_v201(conn)
    return await consultar(
        conn,
        "SELECT id, versao, nome, ambiente, status, criado_em, finalizado_em FROM _trama_migration_runs ORDER BY id DESC LIMIT ?",
        [max(1, int(limite))],
    )


async def seed_aplicar_ambiente(
    conn: DbConnection,
    ambiente: str,
    nome: str,
    sql_ou_plano: object,
) -> dict[str, object]:
    await _ensure_meta_tables_v201(conn)
    amb = str(ambiente).strip().lower()
    if amb not in {"dev", "teste", "prod"}:
        raise DbError("Ambiente inválido para seed_aplicar_ambiente.")
    nome_seed = str(nome).strip()
    if not nome_seed:
        raise DbError("Nome da seed não pode ser vazio.")

    if isinstance(sql_ou_plano, list):
        plano = [p for p in sql_ou_plano if isinstance(p, dict)]
        plano = sorted(plano, key=lambda p: str(p.get("nome", "")))
        resultados: list[dict[str, object]] = []
        for passo in plano:
            r = await seed_aplicar_ambiente(
                conn,
                amb,
                str(passo.get("nome", "")),
                str(passo.get("sql", "")),
            )
            resultados.append(r)
        return {"ok": True, "ambiente": amb, "nome": nome_seed, "plano": resultados}

    sql = str(sql_ou_plano or "")
    ja = await consultar(
        conn,
        "SELECT nome FROM _trama_seeds_ambiente WHERE ambiente = ? AND nome = ? LIMIT 1",
        [amb, nome_seed],
    )
    if ja:
        return {"ok": True, "aplicada": False, "ambiente": amb, "nome": nome_seed}

    tx = await transacao_iniciar(conn)
    try:
        for stmt in _split_sql_statements(sql):
            await tx_executar(tx, stmt)
        await tx_executar(
            tx,
            "INSERT INTO _trama_seeds_ambiente (ambiente, nome, aplicado_em) VALUES (?, ?, ?)",
            [amb, nome_seed, datetime.now(timezone.utc).isoformat()],
        )
        await transacao_commit(tx)
    except Exception:
        if tx.active:
            await transacao_rollback(tx)
        raise
    return {"ok": True, "aplicada": True, "ambiente": amb, "nome": nome_seed}
