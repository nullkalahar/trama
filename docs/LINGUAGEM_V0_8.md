# Linguagem trama v0.8

A `v0.8` adiciona observabilidade para backend em produção: logs estruturados, métricas e tracing inicial.

## Logs estruturados

- `log_estruturado(nivel, mensagem, contexto?)`
- `log_estruturado_json(nivel, mensagem, contexto?)`

## Métricas

- `metrica_incrementar(nome, valor?, labels?)`
- `metrica_observar(nome, valor, labels?)`
- `metricas_snapshot()`
- `metricas_reset()`

Aliases:

- `metrica_inc`

## Tracing

- `traco_iniciar(nome, atributos?)`
- `traco_evento(span, nome, atributos?)`
- `traco_finalizar(span, status?, erro?)`
- `tracos_snapshot()`
- `tracos_reset()`

Aliases pt-BR sem acento:

- `traca_iniciar`, `traca_evento`, `traca_finalizar`
- `tracas_snapshot`, `tracas_reset`

## Exemplo

```trm
função principal()
    metricas_reset()
    tracos_reset()

    metrica_inc("http_requests_total", 1, {"rota": "/health"})
    metrica_observar("http_latencia_ms", 12.7, {"rota": "/health"})
    exibir(metricas_snapshot()["counters"][0]["nome"])

    s = traca_iniciar("request", {"metodo": "GET"})
    traca_evento(s, "db.query", {"ok": verdadeiro})
    sf = traca_finalizar(s, "ok")
    exibir(sf["status"])
fim
```
