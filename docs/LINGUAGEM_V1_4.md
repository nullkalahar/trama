# Linguagem Trama v1.4

## Objetivo

Concluir observabilidade avançada para backend de produção com foco canônico pt-BR:

- métricas HTTP/DB/runtime;
- tracing por requisição;
- logs estruturados com correlação completa;
- dashboard operacional mínimo e alertas iniciais.

## Correlação canônica pt-BR

Campos canônicos:

- `id_requisicao`
- `id_traco`
- `id_usuario`

Compatibilidade (aliases):

- `request_id`
- `trace_id`
- `user_id`

Propagação:

- `id_requisicao` e `id_traco` são gerados/reusados no runtime HTTP;
- `id_usuario` é preenchido quando houver autenticação JWT (`sub`, `id_usuario` ou `user_id`).

## Logs estruturados correlacionados

`log_estruturado` e `log_estruturado_json` passam a incluir contexto de correlação automaticamente quando houver contexto de requisição.

## Métricas avançadas

### HTTP

- `http.requisicoes_total`
- `http.latencia_ms`
- `http.erros_total`

### DB

- `db.operacoes_total`
- `db.latencia_ms`
- `db.erros_total`

### Runtime

- `runtime.eventos_total` (cache, resiliência, jobs e webhooks)

## Tracing por requisição

Para cada requisição HTTP:

- span raiz `http.requisicao`;
- evento `http.resposta` com status e latência;
- finalização com status `ok`/`erro`.

## Dashboard e alertas

### Ativação

- `web_ativar_observabilidade(app, caminho_observabilidade?, caminho_alertas?, config_alertas?)`
- alias: `web_observabilidade_ativar`

### Endpoints

- dashboard: `/observabilidade` (customizável)
- alertas: `/alertas` (customizável)

### API de consulta direta

- `observabilidade_resumo(config_alerta?)`
- `alertas_avaliar(config_alerta?)`

## Exemplo rápido

```trama
assíncrona função principal()
    app = web_criar_app()
    web_ativar_observabilidade(app, "/observabilidade", "/alertas", {"erro_percentual_limite": 5, "latencia_ms_limite": 300, "requisicoes_minimas": 20})
    servidor = aguarde web_iniciar(app, "127.0.0.1", 8080)
    aguarde web_parar(servidor)
fim
```
