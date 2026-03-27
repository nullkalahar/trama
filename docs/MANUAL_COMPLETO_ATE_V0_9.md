# Manual Completo da linguagem trama (até v0.9)

Este manual consolida os recursos entregues da `v0.1` até a `v0.9`.

## 1. Fundamentos

- pipeline: `fonte .trm -> lexer -> parser -> AST -> semântica -> compilador -> bytecode -> VM`
- equivalência com/sem acento em keywords
- keywords case-insensitive
- aliases pt-BR oficiais em biblioteca padrão

Exemplos de equivalência:

- `função` = `funcao`
- `senão` = `senao`
- `assíncrona` = `assincrona`

## 2. Linguagem base (v0.1-v0.4)

- variáveis, números, textos, booleanos e `nulo`
- listas e mapas
- `se/senão`, `enquanto`, `pare`, `continue`
- funções, `retorne`, closures
- exceções: `tente/pegue/finalmente`, `lance`
- módulos via `importe ... como ...`
- runtime assíncrono: `assíncrona`, `aguarde`, tarefas e timeout
- stdlib base: JSON, FS, ENV, TIME, HTTP client e logs

## 3. Backend web e banco (v0.5-v0.6)

## 3.1 Web nativo

- `web_criar_app`
- rotas JSON e echo JSON
- middlewares (`request_id`, `log_requisicao`)
- CORS, healthcheck, estáticos
- `web_iniciar` / `web_parar`

## 3.2 Banco de dados

- conexão async com:
  - `sqlite:///...`
  - `postgres://...` e `postgresql://...` (PostgreSQL nativo via `asyncpg`)
- operações:
  - `pg_conectar`, `pg_executar`, `pg_consultar`, `pg_fechar`
  - transações `pg_transacao_*`, `pg_tx_*`
- query builder:
  - `qb_select`, `qb_where_eq`, `qb_order_by`, `qb_limite`, `qb_sql`, `qb_consultar`
- ORM inicial:
  - `orm_inserir`, `orm_atualizar`, `orm_buscar_por_id`
- migração/seed idempotentes:
  - `migracao_aplicar`, `seed_aplicar`

Aliases pt-BR:

- `banco_*`, `consulta_*`, `modelo_*`, `transacao_*`, `semente_aplicar`

## 4. Segurança e autorização (v0.7)

## 4.1 JWT

- `jwt_criar(payload, segredo, exp_segundos?, algoritmo?)`
- `jwt_verificar(token, segredo, leeway_segundos?)`
- aliases: `token_criar`, `token_verificar`

## 4.2 Senhas

- `senha_hash(senha, algoritmo?)`
- `senha_verificar(senha, hash)`
- aliases: `senha_gerar_hash`, `senha_validar`

Algoritmos:

- `pbkdf2` (nativo)
- `bcrypt` (opcional por dependência)
- `argon2`/`argon2id` (opcional por dependência)

## 4.3 RBAC

- `rbac_criar`, `rbac_atribuir`, `rbac_papeis_usuario`
- `rbac_tem_papel`, `rbac_tem_permissao`
- aliases: `papel_*`, `permissao_tem`

## 5. Observabilidade (v0.8)

## 5.1 Logs estruturados

- `log_estruturado`
- `log_estruturado_json`

## 5.2 Métricas

- `metrica_incrementar`, `metrica_observar`
- `metricas_snapshot`, `metricas_reset`
- alias: `metrica_inc`

## 5.3 Tracing

- `traco_iniciar`, `traco_evento`, `traco_finalizar`
- `tracos_snapshot`, `tracos_reset`
- aliases sem acento: `traca_*`, `tracas_*`

## 6. Tooling oficial (v0.9)

## 6.1 Test runner

```bash
trama testar [alvo]
```

Executa `test_*.trm`.

## 6.2 Lint e format

```bash
trama lint [alvo]
trama formatar [alvo] [--aplicar]
```

## 6.3 Cobertura estática

```bash
trama cobertura [alvo]
```

## 6.4 Template backend

```bash
trama template-backend <destino> [--forcar]
```

Gera esqueleto com `src`, `tests`, `migrations`, `seeds`, `config`.

## 7. Comandos principais da CLI

```bash
trama executar arquivo.trm
trama bytecode arquivo.trm
trama compilar arquivo.trm -o programa.tbc
trama testar [alvo]
trama lint [alvo]
trama formatar [alvo] [--aplicar]
trama cobertura [alvo]
trama template-backend <destino>
```

## 8. Exemplo integrado (segurança + observabilidade)

```trm
função principal()
    h = senha_gerar_hash("abc123", "pbkdf2")
    exibir(senha_validar("abc123", h))

    token = token_criar({"sub": "u1", "papel": "admin"}, "segredo", 600)
    claims = token_verificar(token, "segredo")
    exibir(claims["sub"])

    metricas_reset()
    tracos_reset()
    metrica_inc("requests_total", 1, {"rota": "/api"})
    s = traca_iniciar("req", {"metodo": "GET"})
    traca_evento(s, "db.query", {"ok": verdadeiro})
    traca_finalizar(s, "ok")
    exibir(metricas_snapshot()["counters"][0]["nome"])
fim
```

## 9. Requisitos recomendados

- Python 3.11+
- para PostgreSQL nativo: `pip install -e .[db]`
- para algoritmos extras de senha: `pip install -e .[security]`

## 10. Política de atualização

A cada versão nova:

- atualizar este manual consolidado
- atualizar o manual específico da versão
- atualizar roadmap/checklist do README
