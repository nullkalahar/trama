# Manual Trama v2.1.23

## 1. Resumo

A v2.1.23 introduz arquitetura de jobs orientada a fachada:
- API da linguagem permanece simples e estável
- backend de execução é plugável
- backend em memória segue como padrão de desenvolvimento

## 2. Uso rápido

### 2.1 Fila padrão (memória)

```trm
fila = fila_criar("emails")
```

### 2.2 Fila com backend explícito

```trm
fila = fila_criar_com_backend("emails", "memoria")
```

### 2.3 Enfileirar e processar

```trm
aguarde fila_enfileirar(fila, handler, {"id": 1}, 3, 10.0, "chave-1")
resultado = aguarde fila_processar(fila)
status = fila_status(fila)
```

## 3. Idempotência

- Use `chave_idempotencia` para evitar duplicidade de job.
- Reenvio com mesma chave não cria novo job.

## 4. Observabilidade

Métricas de jobs continuam emitidas com labels por fila/backend.

## 5. Guia de evolução para próximos backends

Para v2.1.24+ (SQL) e v2.1.26 (Redis):
- manter contrato `enqueue/process_all/status`
- preservar campos padrão no retorno
- manter comportamento de fallback em memória para desenvolvimento local

## 6. Referências

- `docs/LINGUAGEM_V2_1_23.md`
- `exemplos/v223/README_V223_EXEMPLOS.md`
- `tests/test_jobs_runtime.py`
- `tests/test_jobs_runtime_v223.py`
