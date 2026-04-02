# Exemplos v2.0.4 (cache distribuido e coerencia)

Arquivos desta pasta demonstram:
- cache distribuido por grupo/instancia;
- invalidez por chave e por padrao;
- cache-aside/read-through com `cache_distribuido_obter_ou_carregar`;
- fallback quando backend de cache esta indisponivel;
- metricas (`hit_ratio`, latencias, invalidacoes);
- integracao com `web_rota` via `opcoes.cache_resposta`.

Execute com:

```bash
PYTHONPATH=src .venv/bin/python -m trama.cli executar exemplos/v204/<arquivo>.trm
```
