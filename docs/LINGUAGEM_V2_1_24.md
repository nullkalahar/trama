# Linguagem Trama v2.1.24

## Objetivo

Adicionar backend persistente de jobs via SQL com:

- retry persistente;
- leasing de execucao;
- DLQ;
- reprocessamento;
- preservacao da fachada canonicamente pt-BR introduzida na `v2.1.23`.

## Superficie canonica pt-BR

Superficie preservada:

- `fila_criar(nome)`
- `fila_criar_com_backend(nome, backend, opcoes_backend)`
- `fila_backends_listar()`
- `fila_enfileirar(fila, handler, payload, tentativas, timeout_segundos, chave_idempotencia)`
- `fila_processar(fila)`
- `fila_status(fila)`

Superficie nova da versao:

- `fila_listar_dlq(fila, limite)`
- `fila_obter_job(fila, id_job)`
- `fila_reprocessar_dlq(fila, limite)`

## Backend SQL

Backend oficial novo:

- `sql`

Configuracao minima:

```trm
fila = fila_criar_com_backend("emails", "sql", {
    "dsn": "sqlite:///.local/v224/jobs.db"
})
```

Opcoes suportadas:

- `dsn`: DSN do banco (`sqlite:///...`, `postgresql://...`, `postgres://...`)
- `lote_processamento`: limite de jobs por ciclo de `fila_processar`
- `lease_segundos`: duracao do lease ao adquirir um job

## Estados formais de job

- `pendente`
- `processando`
- `concluido`
- `falhou`
- `dlq`

## Contrato operacional

### `fila_processar`

Retorna, entre outros:

- `fila`
- `backend`
- `processados`
- `pendentes`
- `processando`
- `concluidos`
- `falhos`
- `dlq`

### `fila_status`

Retorna, entre outros:

- `fila`
- `backend`
- `pendentes`
- `processando`
- `concluidos`
- `falhos`
- `dlq`

### `fila_listar_dlq`

Cada item retorna, entre outros:

- `id`
- `fila`
- `handler_ref`
- `payload`
- `status`
- `tentativas`
- `tentativas_maximas`
- `ultimo_erro`
- `backend`

### `fila_reprocessar_dlq`

Retorna, entre outros:

- `backend`
- `reprocessados`
- contadores atuais da fila

## Compatibilidade

- `memoria` continua como backend padrao de desenvolvimento.
- `fila_criar(...)` continua criando fila em memoria sem alteracoes.
- `fila_criar_com_backend(..., "sql", ...)` adiciona persistencia sem mudar a sintaxe da linguagem.

## Limitacoes conhecidas da v2.1.24

- o backend SQL persiste estado e payload, mas o despacho de handlers ainda depende do processo atual;
- worker standalone e operacao multiworker ficam para `v2.1.25+`;
- `fila_status` no backend SQL reflete o snapshot operacional da instancia ativa da fila, atualizado nas operacoes da propria fachada.

## Exemplos oficiais

- `exemplos/v224/224_01_fila_sql_basica.trm`
- `exemplos/v224/224_02_fila_sql_retry.trm`
- `exemplos/v224/224_03_fila_sql_leasing.trm`
- `exemplos/v224/224_04_fila_sql_dlq.trm`
- `exemplos/v224/224_05_fila_sql_reprocessamento.trm`
- `exemplos/v224/224_06_fila_sql_status_operacional.trm`
- `exemplos/v224/224_07_fila_sql_idempotencia.trm`
- `exemplos/v224/224_08_fluxo_completo_jobs_sql.trm`

## Evidencias da versao

- `tests/test_jobs_runtime.py`
- `tests/test_jobs_runtime_v223.py`
- `tests/test_jobs_runtime_v224.py`
- `tests/test_vm.py`
