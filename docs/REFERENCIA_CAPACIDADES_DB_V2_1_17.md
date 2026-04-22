# Referência de Capacidades de Banco v2.1.17

## Estrutura de `db_capacidades(conn)`

Campos principais:
- `backend`
- `dialeto_sql`
- `transacao`
- `migracao_versionada`
- `seed_ambiente`
- `schema_inspecao`
- `schema_diff_aplicar`
- `json_nativo`
- `retorno_insert_id`
- `concorrencia_escrita`
- `schema_drop_column`

## Matriz atual

### SQLite

- `backend`: `sqlite`
- `dialeto_sql`: `sqlite`
- `json_nativo`: `false`
- `concorrencia_escrita`: `serializada`
- `schema_drop_column`: `false`

### PostgreSQL

- `backend`: `postgres`
- `dialeto_sql`: `postgresql`
- `json_nativo`: `true`
- `concorrencia_escrita`: `multiconexao`
- `schema_drop_column`: `true`

## Uso no runtime

```trama
assíncrona função principal()
    conn = aguarde banco_conectar("sqlite:////tmp/app.db")
    caps = db_capacidades(conn)
    exibir(caps["backend"])
    exibir(caps["dialeto_sql"])
    aguarde banco_fechar(conn)
fim
```

## Uso no CLI

```bash
trama db-capacidades --dsn sqlite:////tmp/app.db --json
trama db-capacidades --dsn postgresql://trama:trama@127.0.0.1:5432/trama_ci --json
```
