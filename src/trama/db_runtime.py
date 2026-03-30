"""Runtime de banco de dados para a linguagem trama (v0.6+).

Suporta backends:
- SQLite: `sqlite:///caminho/arquivo.db`
- PostgreSQL nativo: `postgres://...` ou `postgresql://...` (via asyncpg)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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
