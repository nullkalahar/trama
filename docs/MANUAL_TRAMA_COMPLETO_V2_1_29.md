# Manual v2.1.29

## Uso rápido

Gerar IR:

```bash
trama contrato-ir-gerar --contrato contrato.json --saida build/contrato_ir.json
```

Gerar SDK Python:

```bash
trama sdk-gerar --contrato-ir build/contrato_ir.json --saida build/cliente.py --linguagem python
```

Gerar SDK TypeScript:

```bash
trama sdk-gerar --contrato-ir build/contrato_ir.json --saida build/cliente.ts --linguagem typescript
```

Saída:
- cliente contém métodos por rota
- cliente embute `contrato()` com o IR formal usado na geração
