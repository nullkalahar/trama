# Manual Trama v2.1.24

## 1. Resumo

A `v2.1.24` evolui a fachada de jobs para backend persistente via SQL.

Entrega desta versao:

- backend `sql` registrado por padrao;
- fila persistente com retry, lease, DLQ e reprocessamento;
- compatibilidade mantida com o backend `memoria`;
- novas operacoes oficiais para listar DLQ, consultar job e reprocessar DLQ.

## 2. Uso rapido

### 2.1 Fila SQL com SQLite

```trm
fila = fila_criar_com_backend("emails", "sql", {
    "dsn": "sqlite:///.local/v224/jobs.db"
})
```

### 2.2 Enfileirar e processar

```trm
aguarde fila_enfileirar(fila, handler_email, {"id": 1}, 2, 10.0, "mail-1")
resultado = aguarde fila_processar(fila)
status = fila_status(fila)
```

### 2.3 Inspecao e reprocessamento de DLQ

```trm
itens = aguarde fila_listar_dlq(fila, 20)
job = aguarde fila_obter_job(fila, itens[0]["id"])
reprocesso = aguarde fila_reprocessar_dlq(fila, 20)
```

## 3. Opcoes de backend

- `dsn`: conexao com SQLite ou PostgreSQL
- `lote_processamento`: quantidade maxima por chamada de `fila_processar`
- `lease_segundos`: tempo de reserva do job antes de nova aquisicao

Exemplo:

```trm
fila = fila_criar_com_backend("emails", "sql", {
    "dsn": "sqlite:///.local/v224/jobs.db",
    "lote_processamento": 50,
    "lease_segundos": 15.0
})
```

## 4. Modelo operacional

Fluxo normal:

1. `fila_enfileirar` persiste o job em SQL.
2. `fila_processar` adquire jobs elegiveis com lease.
3. sucesso move o job para `concluido`.
4. falha com tentativas restantes move para `falhou` e agenda retry.
5. falha sem tentativas move para `dlq`.
6. `fila_reprocessar_dlq` retorna itens de `dlq` para `pendente`.

## 5. Compatibilidade e limites

- `memoria` continua recomendado para desenvolvimento local rapido.
- `sql` e a forma oficial desta versao para persistencia.
- persistencia de payload e status esta coberta.
- despacho de handlers ainda depende do processo atual; worker standalone entra na `v2.1.25`.

## 6. Troubleshooting

### 6.1 `backend de jobs desconhecido`

Verifique se a fila foi criada com:

```trm
fila = fila_criar_com_backend("emails", "sql", {"dsn": "sqlite:///.local/jobs.db"})
```

### 6.2 `backend sql requer opcao_backend com dsn`

O backend `sql` exige `dsn` em `opcoes_backend`.

### 6.3 Job vai para `dlq`

Inspecione:

```trm
itens = aguarde fila_listar_dlq(fila, 20)
job = aguarde fila_obter_job(fila, itens[0]["id"])
```

Depois reenvie:

```trm
aguarde fila_reprocessar_dlq(fila, 20)
```

### 6.4 Handler nao registrado

Na `v2.1.24`, o backend SQL persiste o estado do job, mas a execucao ainda depende do handler carregado na instancia atual da aplicacao.

## 7. Referencias

- `docs/LINGUAGEM_V2_1_24.md`
- `exemplos/v224/README_V224_EXEMPLOS.md`
- `tests/test_jobs_runtime_v224.py`
