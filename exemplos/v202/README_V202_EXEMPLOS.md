# Exemplos v2.0.2 (DTO, validação e contrato HTTP)

Arquivos desta pasta demonstram:
- DTO declarativo por contexto (corpo/consulta/parametros);
- coerção e sanitização de payload;
- erros padronizados por campo;
- geração de exemplos válidos/inválidos;
- contrato de entrada (campos permitidos);
- contrato de resposta versionado e retrocompatível;
- alias de compatibilidade `web_rota_com_dto`.

Execute com:

```bash
PYTHONPATH=src .venv/bin/python -m trama.cli executar exemplos/v202/<arquivo>.trm
```
