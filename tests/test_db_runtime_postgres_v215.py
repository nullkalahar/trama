from __future__ import annotations

import asyncio
import os
import time

import pytest

from trama import db_runtime


def _dsn_pg() -> str:
    return str(os.getenv("TRAMA_TEST_PG_DSN", "")).strip()


@pytest.mark.skipif(not _dsn_pg(), reason="TRAMA_TEST_PG_DSN não definido")
def test_v215_postgres_real_transacao_paginacao_constraints_migracao_seed() -> None:
    dsn = _dsn_pg()
    sufixo = str(int(time.time() * 1000))
    tabela = f"v215_itens_{sufixo}"
    mig_tabela = f"v215_mig_{sufixo}"

    conn = asyncio.run(db_runtime.conectar(dsn))
    try:
        asyncio.run(
            db_runtime.executar(
                conn,
                f"CREATE TABLE {tabela} (id SERIAL PRIMARY KEY, codigo TEXT UNIQUE NOT NULL, nome TEXT NOT NULL)",
            )
        )

        tx = asyncio.run(db_runtime.transacao_iniciar(conn))
        asyncio.run(db_runtime.tx_executar(tx, f"INSERT INTO {tabela} (codigo, nome) VALUES (?, ?)", ["c-1", "item 1"]))
        asyncio.run(db_runtime.transacao_rollback(tx))
        rows0 = asyncio.run(db_runtime.consultar(conn, f"SELECT id FROM {tabela}"))
        assert rows0 == []

        for i in range(1, 6):
            asyncio.run(
                db_runtime.executar(
                    conn,
                    f"INSERT INTO {tabela} (codigo, nome) VALUES (?, ?)",
                    [f"c-{i}", f"item {i}"],
                )
            )
        with pytest.raises(Exception):
            asyncio.run(
                db_runtime.executar(
                    conn,
                    f"INSERT INTO {tabela} (codigo, nome) VALUES (?, ?)",
                    ["c-1", "duplicado"],
                )
            )

        modelo = db_runtime.orm_modelo(tabela)
        lista = asyncio.run(
            db_runtime.orm_listar(conn, modelo, filtros={}, opcoes={"pagina": 2, "limite": 2, "ordenacao": "id ASC"})
        )
        assert len(lista["itens"]) == 2
        assert int(lista["paginacao"]["total"]) == 5

        mig = asyncio.run(
            db_runtime.migracao_aplicar_versionada_v2(
                conn=conn,
                versao=f"215.{sufixo}",
                nome="criar_tabela_migracao",
                up_sql=f"CREATE TABLE {mig_tabela} (id SERIAL PRIMARY KEY, nome TEXT NOT NULL);",
                down_sql=f"DROP TABLE IF EXISTS {mig_tabela};",
                ambiente="teste",
            )
        )
        assert mig["aplicada"] is True

        seed = asyncio.run(
            db_runtime.seed_aplicar_ambiente(
                conn=conn,
                ambiente="teste",
                nome=f"seed_{sufixo}",
                sql=f"INSERT INTO {mig_tabela} (nome) VALUES ('a'); INSERT INTO {mig_tabela} (nome) VALUES ('b');",
            )
        )
        assert seed["ok"] is True
        rows_seed = asyncio.run(db_runtime.consultar(conn, f"SELECT nome FROM {mig_tabela} ORDER BY id ASC"))
        assert [r["nome"] for r in rows_seed] == ["a", "b"]
    finally:
        try:
            asyncio.run(db_runtime.executar(conn, f"DROP TABLE IF EXISTS {mig_tabela}"))
        except Exception:
            pass
        try:
            asyncio.run(db_runtime.executar(conn, f"DROP TABLE IF EXISTS {tabela}"))
        except Exception:
            pass
        asyncio.run(db_runtime.fechar(conn))
