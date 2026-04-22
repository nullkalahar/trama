# Exemplos v2.1.4-v2.1.11 (runtime web/realtime modular)

Arquivos desta pasta demonstram:

- status do runtime de tempo real apos modularizacao;
- fallback HTTP desacoplado com reconexao por cursor;
- fluxo de WebSocket com `ack`/`nack`/reenvio;
- configuracao de distribuicao em memoria e redis;
- degradacao e recuperacao de barramento de distribuicao;
- smoke de paridade da fachada do motor HTTP.

Execute com:

```bash
PYTHONPATH=src .venv/bin/python -m trama.cli executar exemplos/v214/<arquivo>.trm
```
