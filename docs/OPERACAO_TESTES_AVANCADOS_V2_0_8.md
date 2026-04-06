# Operacao - Testes avancados v2.0.8

## 1) Execucao rapida local

```bash
trama testes-avancados-v208 --perfil rapido --sem-postgres --sem-redis --json
```

## 2) Execucao completa com relatorios

```bash
trama testes-avancados-v208 \
  --perfil completo \
  --saida-json .local/test-results/v208_relatorio.json \
  --saida-md .local/test-results/v208_relatorio.md
```

## 3) Execucao com PostgreSQL/Redis reais

```bash
export TRAMA_TEST_PG_DSN='postgresql://usuario:senha@127.0.0.1:5432/trama_teste'
export TRAMA_TEST_REDIS_URL='redis://127.0.0.1:6379/0'
trama testes-avancados-v208 --perfil completo --json
```

## 4) Execucao por pytest

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_testes_avancados_v208.py tests/test_cli_v208.py
```

## 5) Interpretacao do relatorio

- `ok=true`: todas as suites passaram.
- `suites.integracao`: fixture real de banco e status de dependencias opcionais.
- `suites.e2e`: fluxos criticos ponta a ponta.
- `suites.carga.metricas`: `latencia_p50_ms`, `latencia_p95_ms`, `erro_pct`, `throughput_rps`.
- `suites.contrato`: regressao de contrato e erros estaveis.
- `suites.caos`: degradacao controlada em falhas parciais.

## 6) Troubleshooting

1. Se `integracao.postgres.status=falha`, revisar `TRAMA_TEST_PG_DSN` e conectividade.
2. Se `integracao.redis.status=falha`, revisar `TRAMA_TEST_REDIS_URL`.
3. Se `carga.ok=false`, ajustar perfil/carga alvo e investigar latencia/erro.
4. Se `caos.ok=false`, revisar fallback e contratos de erro previsiveis.
