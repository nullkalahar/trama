# Manual Trama v2.1.26

## 1. Resumo

A `v2.1.26` adiciona backend `redis` para jobs.

## 2. Uso rapido

```trm
fila = fila_criar_com_backend("emails", "redis", {
    "redis_url": "redis://127.0.0.1:6379/0"
})
```

## 3. Referencias

- `docs/LINGUAGEM_V2_1_26.md`
- `tests/test_jobs_runtime_v226.py`
