# Linguagem Trama v2.1.12-v2.1.17

## Escopo implementado

- engine HTTP ASGI real com fallback automático para engine legada;
- shutdown gracioso com readiness/liveness/health mais rígidos;
- limites operacionais por engine (`max_body_bytes`, `timeout_leitura_segundos`);
- separação explícita de dialeto SQL/capacidades por backend;
- introspecção de schema com paridade SQLite/PostgreSQL;
- comando CLI `db-capacidades` e builtin `db_capacidades`.

## Exemplos canônicos (pt-BR)

- `exemplos/v217/README_V217_EXEMPLOS.md`
- `exemplos/v217/217_01_engine_legada_padrao.trm`
- `exemplos/v217/217_02_engine_asgi_configuracao.trm`
- `exemplos/v217/217_03_engine_asgi_contingencia_automatica.trm`
- `exemplos/v217/217_04_saude_pronto_vivo_rigidos.trm`
- `exemplos/v217/217_05_limites_operacionais_por_engine.trm`
- `exemplos/v217/217_06_capacidades_sqlite_runtime.trm`
- `exemplos/v217/217_07_capacidades_postgres_runtime.trm`
- `exemplos/v217/217_08_schema_inspecionar_sqlite.trm`
- `exemplos/v217/217_09_schema_diff_sqlite_com_dialeto.trm`
- `exemplos/v217/217_10_schema_diff_postgres_com_dialeto.trm`
- `exemplos/v217/217_11_cli_db_capacidades_documentado.trm`
- `exemplos/v217/217_12_migracao_seed_backend_neutro.trm`
- `exemplos/v217/217_13_orm_paginacao_backend_neutro.trm`
- `exemplos/v217/217_14_schema_preview_plano_dialeto.trm`
- `exemplos/v217/217_15_fluxo_completo_web_db_v217.trm`

## Exemplo: configurar engine HTTP ASGI

```trama
assíncrona função principal()
    app = web_criar_app()

    web_configurar_engine_http(
        app,
        "asgi",
        verdadeiro,
        8.0
    )

    web_rota(app, "GET", "/ping", função(req)
        retorne {"status": 200, "json": {"ok": verdadeiro}}
    fim, {}, {})

    servidor = aguarde web_iniciar(app, "127.0.0.1", 8080)
    escreva(servidor["base_url"])
fim
```

## Exemplo: capabilities de banco no runtime

```trama
assíncrona função principal()
    conn = aguarde banco_conectar("sqlite:///./dados/app.db")
    caps = db_capacidades(conn)
    escreva(caps["backend"])
    escreva(caps["dialeto_sql"])
    aguarde banco_fechar(conn)
fim
```

## Exemplo: capabilities de banco no CLI

```bash
trama db-capacidades --dsn sqlite:///./dados/app.db --json
```

## Testes e CI

- `tests/test_web_engine_asgi_v212_v213.py`
- `tests/test_db_capacidades_v217.py`
- `tests/test_db_runtime_postgres_v215.py`
- `tests/test_cli_db_capacidades_v217.py`
- workflow CI com job `postgres_real_v215` usando serviço PostgreSQL real.
