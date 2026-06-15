# Linguagem Trama v2.1.27

## Objetivo

Formalizar IR canonico de contrato HTTP para:

- DTOs;
- erros;
- auth;
- exemplos;
- versionamento.

## Superficie nova

- `web_gerar_ir_contrato(app, titulo, versao, servidor_base)`
- `web_exportar_ir_contrato(app, arquivo_saida, titulo, versao, servidor_base)`

Aliases canonicos:

- `web_contrato_ir_gerar`
- `web_contrato_ir_exportar`

## Identificador do IR

- `ir_contrato = "trama_http_v1"`

## Estrutura principal

- `titulo`
- `versao`
- `servidores`
- `rotas`
- `componentes`

## Exemplos oficiais

- `exemplos/v227/227_01_ir_contrato_basico.trm`
- `exemplos/v227/227_02_ir_contrato_com_dto_auth.trm`
