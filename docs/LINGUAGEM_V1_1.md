# Linguagem Trama v1.1

## Objetivo

Consolidar fundamentos de backend robusto:

- cache de aplicação com TTL/invalidação/warmup;
- resiliência para integrações externas (retry/backoff/timeout/circuit breaker);
- configuração por ambiente com validação e gestão de segredos.

## Builtins canônicos pt-BR

### Configuração e segredos

- `config_carregar_ambiente(padrao, prefixo?, obrigatorios?, schema?)`
- `config_validar(config, obrigatorios?, schema?)`
- `segredo_obter(nome, padrao?, obrigatorio?, permitir_vazio?)`
- `segredo_mascarar(valor, visivel?)`

Compatibilidade:

- `config_carregar(...)` continua válido.
- `segredo_ler(...)` é alias de `segredo_obter(...)`.

### Cache

- `cache_definir(chave, valor, ttl_segundos?, namespace?)`
- `cache_obter(chave, padrao?, namespace?)`
- `cache_existe(chave, namespace?)`
- `cache_remover(chave, namespace?)`
- `cache_invalidar_padrao(padrao, namespace?)`
- `cache_limpar(namespace?)`
- `cache_aquecer(itens, ttl_segundos?, namespace?)`
- `cache_stats(namespace?)`

### Resiliência

- `resiliencia_executar(nome, operacao_fn, argumentos?, opcoes?)`
- `circuito_status(nome)`
- `circuito_resetar(nome?)`

Opções de `resiliencia_executar`:

- `tentativas`
- `timeout_segundos`
- `max_falhas`
- `reset_timeout_segundos`
- `base_backoff_segundos`
- `max_backoff_segundos`
- `jitter_segundos`
- `nao_retentaveis` (lista de nomes de exceção)

## Exemplo

```trama
assíncrona função principal()
    cfg = config_carregar_ambiente(
        {"host": "127.0.0.1", "porta": 8080},
        "TRAMA_",
        ["host", "porta"],
        {"host": "texto", "porta": "inteiro"}
    )

    cache_definir("usuario:42", {"nome": "ana"}, 30)
    exibir(cache_obter("usuario:42")["nome"])

    função consulta()
        retorne "ok"
    fim
    valor = aguarde resiliencia_executar("servico_x", consulta, [], {"tentativas": 3})
    exibir(valor)
fim
```
