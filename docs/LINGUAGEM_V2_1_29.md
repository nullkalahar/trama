# Trama v2.1.29

Tema: SDKs Python e TypeScript passam a consumir o mesmo IR formal de contrato HTTP.

Entregas:
- `tooling_runtime.gerar_sdk_cliente()` agora aceita IR formal ou OpenAPI e normaliza tudo para `trama_http_v1`
- `web_gerar_sdk()` passou a gerar SDK a partir do IR do app
- CLI `sdk-gerar` aceita `--contrato-ir` além de `--openapi`

Garantias:
- nenhuma mudança de lexer, parser ou sintaxe
- superfície canônica segue em pt-BR

Arquivos centrais:
- `src/trama/tooling_runtime.py`
- `src/trama/builtins.py`
- `src/trama/cli.py`
