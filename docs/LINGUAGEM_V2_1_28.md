# Linguagem Trama v2.1.28

## Objetivo

Fazer OpenAPI consumir o IR formal da `v2.1.27`.

## Mudanca principal

- `web_gerar_openapi` passa a gerar OpenAPI a partir do IR formal;
- `openapi-gerar` aceita IR formal diretamente;
- compatibilidade preservada com documentos OpenAPI e contratos legados baseados em `paths`.

## Exemplos oficiais

- `exemplos/v228/228_01_openapi_via_ir.trm`
- `exemplos/v228/228_02_cli_openapi_via_ir.trm`
