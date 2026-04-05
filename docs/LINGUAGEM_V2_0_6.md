# Trama v2.0.6 - Tooling de backend maduro

A v2.0.6 entrega tooling operacional para ciclo completo de backend: contrato OpenAPI, SDK, templates e CLI administrativa.

## Objetivo

Padronizar onboarding técnico e operação de backend com superfície canônica pt-BR.

## Novidades da linguagem e runtime

### Builtins novos (canônicos)

- `web_gerar_openapi(app, titulo, versao, servidor_base)`
- `web_exportar_openapi(app, arquivo_saida, titulo, versao, servidor_base)`
- `web_gerar_sdk(app, arquivo_saida, linguagem, nome_cliente, titulo, versao, servidor_base)`

Aliases de compatibilidade:

- `web_openapi_gerar`
- `web_openapi_exportar`
- `web_sdk_gerar`

### CLI nova (produção)

- `trama openapi-gerar --contrato <json> --saida <openapi.json> [--titulo] [--versao] [--servidor]`
- `trama sdk-gerar --openapi <openapi.json> --saida <sdk.py|sdk.ts> [--linguagem python|typescript] [--cliente NomeCliente]`
- `trama admin-usuario-criar --id <id> [--nome] [--papeis]`
- `trama admin-usuario-listar [--json]`
- `trama admin-permissao-conceder --id <id> --permissoes <p1,p2>`
- `trama admin-jobs-listar [--json]`
- `trama admin-manutencao-status [--json]`
- `trama migracao-aplicar-v2 --dsn <dsn> --versao <v> --nome <nome> --up-arquivo <sql> [--down-arquivo] [--ambiente] [--dry-run]`
- `trama migracao-trilha-listar --dsn <dsn> [--limite N] [--json]`
- `trama seed-aplicar-ambiente --dsn <dsn> --ambiente <dev|teste|prod> --nome <nome> --sql-arquivo <sql>`
- `trama operacao-diagnostico [--json]`

### Templates novos

- `trama template-servico <destino> [--forcar] [--json]`
- `trama template-modulo <destino> [--nome modulo_exemplo] [--forcar] [--json]`

## Fluxo recomendado de uso

1. Gere base de serviço com `template-servico`.
2. Modele contrato e exporte OpenAPI.
3. Gere SDK para clientes internos.
4. Rode migrações/seeds versionadas.
5. Gerencie usuários/permissões operacionais pela CLI admin.
6. Execute diagnóstico operacional antes de release.

## Testes e validação

Cobertura implementada:

- `tests/test_tooling_runtime_v206.py`
- `tests/test_cli.py` (comandos novos)
- `tests/test_devtools.py` (templates novos)
- `tests/test_vm.py::test_v206_tooling_openapi_sdk_em_vm`

## DoD v2.0.6 atendido

- onboarding técnico previsível: templates + OpenAPI + SDK.
- fluxo de desenvolvimento/admin padronizado: CLI administrativa e operacional completa.
