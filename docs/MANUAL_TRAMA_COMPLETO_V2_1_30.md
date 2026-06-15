# Manual v2.1.30

## Verificação de breaking changes

```bash
trama contrato-breaking-verificar --antes contrato_v1.json --depois contrato_v2.json --saida build/breaking.json
```

Interpretação:
- `ok: true`: sem incompatibilidade detectada
- `breaking_changes`: regressões objetivas
- `avisos`: mudanças novas que pedem revisão mas não bloqueiam por si
