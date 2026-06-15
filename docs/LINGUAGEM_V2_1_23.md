# Linguagem Trama v2.1.23

## Objetivo

Transformar jobs em **fachada com backend plugável**, preservando o backend em memória como padrão de desenvolvimento.

## Superfície canônica pt-BR

- `fila_criar(nome)`
  - cria fila usando backend padrão `memoria`
- `fila_criar_com_backend(nome, backend, opcoes_backend)`
  - cria fila com backend explícito
- `fila_backends_listar()`
  - lista backends registrados
- `fila_enfileirar(fila, handler, payload, tentativas, timeout_segundos, chave_idempotencia)`
- `fila_processar(fila)`
- `fila_status(fila)`

## Compatibilidade

- `fila_criar` legado continua funcionando sem mudanças.
- Comportamento padrão em desenvolvimento permanece em memória.

## Contrato de backend (runtime)

Um backend plugável de jobs precisa implementar:

- `enqueue(...)`
- `process_all()`
- `status()`

## Backends

- padrão: `memoria`
- extensível via registro de fábrica no runtime Python

## Retornos principais

`fila_processar` retorna, entre outros:

- `backend`
- `processados`
- `concluidos`
- `dlq`

`fila_status` retorna, entre outros:

- `backend`
- `pendentes`
- `concluidos`
- `dlq`

## Exemplos oficiais

- `exemplos/v223/223_01_fila_memoria_padrao.trm`
- `exemplos/v223/223_02_fila_criar_com_backend_memoria.trm`
- `exemplos/v223/223_03_fila_backends_listar.trm`
- `exemplos/v223/223_04_jobs_retry_idempotencia.trm`
- `exemplos/v223/223_05_jobs_status_backend.trm`
- `exemplos/v223/223_06_jobs_processamento_em_lote.trm`
- `exemplos/v223/223_07_webhook_assinado_basico.trm`
- `exemplos/v223/223_08_fluxo_dev_fachada_jobs.trm`
