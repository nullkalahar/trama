# Linguagem Trama v2.1.26

## Objetivo

Adicionar backend Redis para jobs com concorrencia distribuida controlada.

## Superficie preservada

- `fila_criar_com_backend(nome, "redis", opcoes_backend)`
- `fila_enfileirar(...)`
- `fila_processar(...)`
- `fila_status(...)`
- `fila_listar_dlq(...)`
- `fila_reprocessar_dlq(...)`

## Backend Redis

Opcoes principais:

- `redis_url`
- `chave_prefixo`
- `lote_processamento`
- `lease_segundos`

## Garantia operacional

- claim atomico de job via Redis;
- fila `pendentes`;
- fila `processando`;
- DLQ;
- reagendamento de retry;
- idempotencia por chave.

## Exemplos oficiais

- `exemplos/v226/226_01_fila_redis_basica.trm`
- `exemplos/v226/226_02_fila_redis_dlq_reprocessamento.trm`
