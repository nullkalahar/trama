# Manual Trama v2.1.28

## 1. Resumo

A `v2.1.28` passa a gerar OpenAPI a partir do IR formal da Trama.

## 2. Uso rapido

```bash
trama contrato-ir-gerar --contrato contrato.json --saida build/contrato_ir.json
trama openapi-gerar --contrato build/contrato_ir.json --saida build/openapi.json
```

## 3. Referencias

- `docs/LINGUAGEM_V2_1_28.md`
- `tests/test_cli_v227_v228.py`
