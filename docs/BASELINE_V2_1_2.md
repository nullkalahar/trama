# Baseline v2.1.2

Baseline oficial reproduzivel da suite critica v2.1.2.

## Comando oficial

```bash
trama testes-avancados-v212 \
  --perfil rapido \
  --saida-json .local/test-results/v212_relatorio.json \
  --saida-md .local/test-results/v212_relatorio.md \
  --json
```

## Parametros versionados

- perfil: `rapido`
- total_requisicoes: `80`
- concorrencia: `8`

## Resultado (amostra oficial)

- latencia_p50_ms: `12.58`
- latencia_p95_ms: `18.88`
- throughput_rps: `125.48`
- erro_pct: `0.0`
- duracao_s: `0.64`

## Evidencia

- JSON: `docs/baselines/v212_relatorio_rapido.json`
- Markdown: `docs/baselines/v212_relatorio_rapido.md`
