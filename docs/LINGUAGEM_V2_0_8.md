# Trama v2.0.8 - Testes avancados (integracao/e2e/carga)

A v2.0.8 entrega a infraestrutura oficial de testes avancados para qualidade de producao.

## Objetivo

Cobrir cenarios criticos com execucao reproduzivel: integracao real, e2e, carga/concorrrencia, contrato e caos.

## Entregas tecnicas

- runtime de harness: `src/trama/testes_avancados_runtime.py`
- comando oficial de execucao:
  - `trama testes-avancados-v208`
- relatorios automaticos:
  - JSON consolidado
  - Markdown consolidado

## Suites implementadas

1. Integracao com fixtures reais de banco
- SQLite real com migracao versionada v2 + seed por ambiente.
- Validacao opcional de PostgreSQL/Redis por variavel de ambiente.

2. E2E de fluxos criticos
- auth JWT por rota
- DTO/validacao profunda
- contrato HTTP versionado com retrocompatibilidade
- persistencia real em SQLite
- fluxo realtime fallback com autenticacao

3. Carga e concorrencia com SLO
- medicao automatica de `p50`, `p95`, taxa de erro e throughput
- avaliacao automatica contra SLO configuravel

4. Regressao de contrato HTTP
- validacao de versao legacy
- validacao de erro estavel para versao invalida

5. Caos/falha parcial
- DB indisponivel com erro controlado
- cache/backplane indisponivel com fallback degradado
- rede indisponivel com smoke check sem quebra do processo

6. Relatorio consolidado
- saida em arquivo JSON + markdown
- status por suite e checks detalhados

## CLI oficial

```bash
trama testes-avancados-v208 --perfil completo --saida-json .local/test-results/v208_relatorio.json --saida-md .local/test-results/v208_relatorio.md
```

Opcoes importantes:
- `--perfil rapido|completo`
- `--sem-postgres`
- `--sem-redis`
- `--json`

## Variaveis de ambiente opcionais

- `TRAMA_TEST_PG_DSN`: habilita validacao real de fixture PostgreSQL.
- `TRAMA_TEST_REDIS_URL`: habilita validacao real de fixture Redis.

## DoD v2.0.8 atendido

- cobertura de cenarios criticos de producao: sim, por suites de integracao/e2e/carga/contrato/caos.
- baseline de performance reproduzivel: sim, com perfil, parametros e metricas no relatorio.
