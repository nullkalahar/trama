# Exemplos v2.0.3 (realtime distribuido em escala)

Arquivos desta pasta demonstram:

- sincronizacao de presenca/salas entre instancias;
- publicacao distribuida por backplane;
- ack/nack/retry/reenvio com cursor;
- reconexao por cursor no fallback HTTP;
- limites por conexao/usuario/sala;
- comportamento degradado com backplane indisponivel.

Execute com:

```bash
PYTHONPATH=src .venv/bin/python -m trama.cli executar exemplos/v203/<arquivo>.trm
```
