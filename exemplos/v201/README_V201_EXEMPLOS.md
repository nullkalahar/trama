# Exemplos v2.0.1 (ORM e migrações nível produção)

Arquivos desta pasta demonstram:
- relações ORM (1:1, 1:N, N:N);
- paginação e listagem por modelo;
- constraints e evolução de schema;
- diff/preview/aplicação de schema;
- migração versionada v2, trilha e rollback;
- seed por ambiente.

Execute com:

```bash
PYTHONPATH=src .venv/bin/python -m trama.cli executar exemplos/v201/<arquivo>.trm
```
