# Linguagem Trama v2.0.4 (Cache distribuido e coerencia)

Esta versao introduz runtime de cache distribuido com coerencia entre nos, protecao contra stampede, fallback degradado e metricas operacionais auditaveis.

## Objetivo

- cache compartilhado com TTL e invalidez por chave/padrao;
- leitura otimizada para consultas criticas com cache-aside/read-through;
- comportamento previsivel sob concorrencia e indisponibilidade de backend;
- visibilidade operacional por metricas e eventos.

## API canonica pt-BR

- `cache_distribuido_criar(grupo?, id_instancia?, auto_sincronizar?)`
- `cache_distribuido_configurar_backplane(grupo?, disponivel?)`
- `cache_distribuido_sincronizar(instancia?)`
- `cache_distribuido_definir(chave, valor, ttl_segundos?, namespace?, instancia?)`
- `cache_distribuido_obter(chave, padrao?, namespace?, instancia?)`
- `cache_distribuido_invalidar_chave(chave, namespace?, instancia?)`
- `cache_distribuido_invalidar_padrao(padrao, namespace?, instancia?)`
- `cache_distribuido_obter_ou_carregar(chave, carregador_fn, ttl_segundos?, namespace?, timeout_coalescencia_segundos?, fallback?, instancia?)`
- `cache_distribuido_stats(namespace?, instancia?)`
- `cache_distribuido_limpar(namespace?, instancia?)`

Aliases de compatibilidade:

- `cache_dist_*` (equivalentes diretos aos canonicos).

## Modelo operacional

### Namespace, chave e padrao

- Use `namespace` para separar dominios de cache (ex.: `http`, `catalogo`, `sessao`).
- Use invalidacao por chave para alvo especifico.
- Use invalidacao por padrao (`produto:*`) para lotes de chaves.

### TTL e read-through

- `cache_distribuido_definir` grava com TTL opcional.
- `cache_distribuido_obter` faz hit local e, em miss, tenta read-through no backend compartilhado.
- TTL e respeitado entre nos no valor reidratado localmente.

### Invalidez remota

- Invalidez publica evento no backplane do `grupo`.
- Cada instancia pode sincronizar automaticamente (`auto_sincronizar=verdadeiro`) ou manualmente com `cache_distribuido_sincronizar`.

### Stampede

`cache_distribuido_obter_ou_carregar` implementa:

- lock por chave;
- coalescencia de concorrencia para uma unica carga;
- timeout de espera (`timeout_coalescencia_segundos`);
- fallback controlado em timeout/erro do carregador.

### Fallback quando backend indisponivel

- Falha de backend nao interrompe fluxo critico.
- Runtime registra falhas em `falhas_backend` e uso de fallback em `fallback_usado`.
- Fonte de verdade deve continuar no sistema de origem (DB/servico).

## Metricas e observabilidade

`cache_distribuido_stats` expoe, por namespace:

- `hits`, `misses`, `hit_ratio`;
- `definicoes`, `remocoes`, `expirados`;
- `invalidacoes_locais`, `invalidacoes_remotas`;
- `falhas_backend`, `fallback_usado`;
- `coalescencia_lider`, `coalescencia_espera`;
- `latencias` por operacao (`obter`, `definir`, `invalidar_padrao`, `sincronizar` etc.).

## Integracao HTTP (web_runtime)

Rotas `web_rota` podem habilitar cache de resposta GET com `opcoes.cache_resposta`:

```trama
opcoes = {
    "cache_resposta": {
        "namespace": "http",
        "ttl_segundos": 30,
        "instancia": cache_distribuido_criar("api", "web-1", verdadeiro)
    }
}
```

Campos suportados:

- `namespace`: isolamento de cache HTTP.
- `ttl_segundos`: tempo de expiracao.
- `instancia`: no de cache usado pela rota.
- `chave`: chave customizada (opcional). Se omitida, usa `GET:{path}?{query}`.

## Exemplo rapido

```trama
assíncrona função principal()
    cache_a = cache_distribuido_criar("catalogo", "a", verdadeiro)
    cache_b = cache_distribuido_criar("catalogo", "b", verdadeiro)

    cache_distribuido_definir("produto:1", {"id": 1, "nome": "Mouse"}, 60, "produtos", cache_a)
    exibir(cache_distribuido_obter("produto:1", nulo, "produtos", cache_b)["nome"])

    cache_distribuido_invalidar_chave("produto:1", "produtos", cache_a)
    cache_distribuido_sincronizar(cache_b)
    exibir(cache_distribuido_obter("produto:1", nulo, "produtos", cache_b) == nulo)
fim
```

## Testes de referencia da versao

- `tests/test_cache_runtime_v204.py`
- `tests/test_web_cache_v204.py`
- `tests/test_vm.py::test_v204_cache_distribuido_em_vm`
