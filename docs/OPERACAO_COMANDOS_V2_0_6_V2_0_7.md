# Operacao Comando a Comando - v2.0.6 e v2.0.7

## OpenAPI e SDK

```bash
trama openapi-gerar --contrato config/contrato_base.json --saida build/openapi.json --titulo "API Trama" --versao "2.0.6"
trama sdk-gerar --openapi build/openapi.json --saida sdk/cliente_api.py --linguagem python --cliente ClienteApiTrama
trama sdk-gerar --openapi build/openapi.json --saida sdk/cliente_api.ts --linguagem typescript --cliente ClienteApiTramaTs
```

## Templates

```bash
trama template-servico ./novo_servico
trama template-modulo ./novo_modulo --nome cobranca_fatura
```

## Administração

```bash
trama admin-usuario-criar --id admin --nome "Administrador" --papeis root,ops
trama admin-permissao-conceder --id admin --permissoes usuarios:listar,jobs:executar,manutencao:editar
trama admin-usuario-listar --json
trama admin-jobs-listar --json
trama admin-manutencao-status --json
```

## Banco e diagnóstico

```bash
trama migracao-aplicar-v2 --dsn sqlite:///./.local/producao.db --versao 206.001 --nome inicial --up-arquivo migrations/206001_up.sql --down-arquivo migrations/206001_down.sql --ambiente prod
trama migracao-trilha-listar --dsn sqlite:///./.local/producao.db --json
trama seed-aplicar-ambiente --dsn sqlite:///./.local/producao.db --ambiente prod --nome base --sql-arquivo seeds/prod_base.sql
trama operacao-diagnostico --json
```

## Observabilidade e SRE

```bash
trama operacao-smoke-check --base-url http://127.0.0.1:8080 --json
```

Endpoints operacionais:

- `GET /saude`
- `GET /pronto`
- `GET /vivo`
- `GET /observabilidade`
- `GET /alertas`
- `GET /metricas`
- `GET /otlp-json`

## Troubleshooting rápido

1. `migracao-aplicar-v2` falhou: valide SQL e lock de migração.
2. `operacao-smoke-check` falhou: inspecione `resultados[].erro` e latência por rota.
3. `/alertas` em degradado: consultar `taxa_erro_pct`, `latencia_p95_ms` e runbook correspondente.
