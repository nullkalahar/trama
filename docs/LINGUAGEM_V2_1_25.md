# Linguagem Trama v2.1.25

## Objetivo

Adicionar operacao standalone para jobs com:

- worker externo para filas SQL;
- comandos operacionais de fila;
- comandos operacionais de DLQ;
- reprocessamento por CLI;
- preservacao integral da superficie canonica pt-BR.

## Superficie da linguagem preservada

Sem mudancas de sintaxe, lexer ou parser.

Superficie canonica de jobs continua:

- `fila_criar(nome)`
- `fila_criar_com_backend(nome, backend, opcoes_backend)`
- `fila_backends_listar()`
- `fila_enfileirar(fila, handler, payload, tentativas, timeout_segundos, chave_idempotencia)`
- `fila_processar(fila)`
- `fila_status(fila)`
- `fila_listar_dlq(fila, limite)`
- `fila_obter_job(fila, id_job)`
- `fila_reprocessar_dlq(fila, limite)`

## Superficie operacional nova da CLI

- `trama jobs-worker-rodar --dsn ... --fila ... --arquivo handlers.trm`
- `trama jobs-fila-status --dsn ... --fila ...`
- `trama jobs-dlq-listar --dsn ... --fila ...`
- `trama jobs-dlq-reprocessar --dsn ... --fila ...`

## Worker standalone

O worker:

- carrega um arquivo `.trm`;
- registra handlers exportados pelo nome canonicamente pt-BR da funcao;
- processa a fila SQL sem depender do processo que enfileirou;
- preserva o contrato do backend `sql` da `v2.1.24`.

## Contratos operacionais

### `jobs-worker-rodar`

Retorna, entre outros:

- `ok`
- `backend`
- `fila`
- `arquivo_handlers`
- `handlers`
- `ciclos`
- `processados_total`
- `status_final`
- `historico`

### `jobs-fila-status`

Retorna, entre outros:

- `ok`
- `fila`
- `backend`
- `pendentes`
- `processando`
- `concluidos`
- `falhos`
- `dlq`

### `jobs-dlq-listar`

Retorna, entre outros:

- `ok`
- `fila`
- `backend`
- `total`
- `itens`

### `jobs-dlq-reprocessar`

Retorna, entre outros:

- `ok`
- `fila`
- `backend`
- `reprocessados`

## Compatibilidade

- nenhuma palavra-chave nova foi introduzida;
- nenhuma mudanca de sintaxe foi necessaria;
- a `v2.1.25` opera sobre o backend `sql` da `v2.1.24`;
- o backend `memoria` continua valido para desenvolvimento local.

## Exemplos oficiais

- `exemplos/v225/225_01_handlers_worker_basico.trm`
- `exemplos/v225/225_02_handlers_worker_dlq.trm`
- `exemplos/v225/225_03_worker_fluxo_operacional.trm`
