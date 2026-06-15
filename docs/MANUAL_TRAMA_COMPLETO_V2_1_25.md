# Manual Trama v2.1.25

## 1. Resumo

A `v2.1.25` fecha a operacao basica de jobs SQL com worker standalone e comandos de administracao por CLI.

Entrega desta versao:

- worker externo com arquivo `.trm` de handlers;
- status operacional da fila por CLI;
- listagem de DLQ por CLI;
- reprocessamento de DLQ por CLI;
- nenhuma regressao de sintaxe ou parser.

## 2. Uso rapido

### 2.1 Arquivo de handlers

```trm
função processar(payload)
    retorne payload["ok"]
fim
```

### 2.2 Rodar worker standalone

```bash
trama jobs-worker-rodar \
  --dsn sqlite:///.local/v225/jobs.db \
  --fila emails \
  --arquivo exemplos/v225/225_01_handlers_worker_basico.trm \
  --uma-vez \
  --json
```

### 2.3 Consultar status da fila

```bash
trama jobs-fila-status --dsn sqlite:///.local/v225/jobs.db --fila emails --json
```

### 2.4 Consultar DLQ

```bash
trama jobs-dlq-listar --dsn sqlite:///.local/v225/jobs.db --fila emails --limite 20 --json
```

### 2.5 Reprocessar DLQ

```bash
trama jobs-dlq-reprocessar --dsn sqlite:///.local/v225/jobs.db --fila emails --limite 20 --json
```

## 3. Modelo operacional

Fluxo recomendado:

1. a aplicacao enfileira com backend `sql`;
2. o worker carrega handlers do arquivo `.trm`;
3. o worker processa a fila;
4. falhas finais vao para `dlq`;
5. a operacao lista itens de `dlq`;
6. a operacao executa reprocessamento quando necessario.

## 4. Requisitos do worker

- o nome da funcao no arquivo `.trm` deve coincidir com `handler_ref` persistido no job;
- o arquivo informado deve conter ao menos um handler;
- o worker atua sobre o backend `sql`.

## 5. Troubleshooting

### 5.1 `Nenhum handler de job encontrado`

Verifique se o arquivo `.trm` contem funcoes nomeadas no escopo global.

### 5.2 `handler nao registrado`

O nome do handler persistido no job precisa existir no arquivo passado ao worker.

### 5.3 Status da fila nao bate com o processo que enfileirou

Use `jobs-fila-status`. Na `v2.1.25`, o status do backend SQL e recarregado do banco para comandos operacionais.

## 6. Referencias

- `docs/LINGUAGEM_V2_1_25.md`
- `exemplos/v225/README_V225_EXEMPLOS.md`
- `tests/test_jobs_runtime_v225.py`
- `tests/test_cli_v225.py`
