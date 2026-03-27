# Linguagem trama v0.6

A `v0.6` entrega o núcleo de persistência de dados para backend.

## Objetivo da versão

Disponibilizar uma base robusta para acesso a banco, transações, query builder/ORM inicial e gestão de migrações/seed.

## Banco de dados (driver async)

Builtins principais:

- `pg_conectar(dsn)`
- `pg_fechar(conn)`
- `pg_executar(conn, sql, params?)`
- `pg_consultar(conn, sql, params?)`

Aliases pt-BR oficiais (recomendados):

- `banco_conectar`, `banco_fechar`, `banco_executar`, `banco_consultar`

### DSN suportada

- `sqlite:///caminho/arquivo.db`
- `postgres://...` e `postgresql://...` (compatibilidade inicial via shim local)

Nesta versão, o runtime usa SQLite como backend local para facilitar desenvolvimento e testes.

## Transações

- `pg_transacao_iniciar(conn)`
- `pg_transacao_commit(tx)`
- `pg_transacao_rollback(tx)`
- `pg_tx_executar(tx, sql, params?)`
- `pg_tx_consultar(tx, sql, params?)`

Aliases pt-BR:

- `transacao_iniciar`, `transacao_confirmar`, `transacao_cancelar`
- `transacao_executar`, `transacao_consultar`

## Query Builder inicial

- `qb_select(tabela, colunas?)`
- `qb_where_eq(query, campo, valor)`
- `qb_order_by(query, campo, direcao?)`
- `qb_limite(query, limite)`
- `qb_sql(query)`
- `qb_consultar(conn, query)`

Aliases pt-BR:

- `consulta_selecionar`, `consulta_onde_igual`, `consulta_ordenar_por`
- `consulta_limite`, `consulta_sql`, `consulta_executar`

## ORM inicial

- `orm_inserir(conn, tabela, dados)`
- `orm_atualizar(conn, tabela, dados, where)`
- `orm_buscar_por_id(conn, tabela, id)`

Aliases pt-BR:

- `modelo_inserir`, `modelo_atualizar`, `modelo_buscar_por_id`

## Migrações idempotentes e seed

- `migracao_aplicar(conn, nome, sql)`
- `seed_aplicar(conn, nome, sql)`

Alias pt-BR:

- `semente_aplicar(conn, nome, sql)`

Regras:

- cada migração/seed é aplicada uma única vez por `nome`
- metadados internos são mantidos em:
  - `_trama_migrations`
  - `_trama_seeds`

## Exemplo completo

```trama
assíncrona função principal()
    conn = aguarde pg_conectar("sqlite:///./app.db")

    aguarde pg_executar(conn, "CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")

    m = aguarde migracao_aplicar(conn, "001_cria_posts", "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT);")
    exibir(m["aplicada"])

    id = aguarde orm_inserir(conn, "usuarios", {"nome": "ana"})
    usuario = aguarde orm_buscar_por_id(conn, "usuarios", id)
    exibir(usuario["nome"])

    tx = aguarde pg_transacao_iniciar(conn)
    aguarde pg_tx_executar(tx, "INSERT INTO usuarios (nome) VALUES (?)", ["bia"])
    aguarde pg_transacao_commit(tx)

    q = qb_select("usuarios", ["id", "nome"])
    q = qb_order_by(q, "id", "DESC")
    rows = aguarde qb_consultar(conn, q)
    exibir(rows[0]["nome"])

    aguarde pg_fechar(conn)
fim
```
