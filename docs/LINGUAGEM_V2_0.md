# Linguagem Trama v2.0 (Andamento Atual)

Este manual descreve, de forma objetiva, o que a v2.0 já implementa e o que ainda está pendente.

## Objetivo da v2.0

Autossuficiência da linguagem, removendo Python do caminho crítico do usuário final.

## Fase 1 (concluída)

- especificação formal do bytecode canônico v1;
- ABI formal da VM v1;
- matriz de cobertura de recursos da linguagem para bytecode/ABI;
- testes de conformidade (shape, roundtrip, payload inválido, opcode inválido).

Documentos:
- `docs/BYTECODE_V1.md`
- `docs/ABI_VM_V1.md`
- `docs/MATRIZ_COBERTURA_BYTECODE_ABI_V1.md`

## Fase 2 (em andamento)

### Já implementado

- runtime nativo C com `executar-tbc`;
- alias de compatibilidade `run-tbc`;
- diagnóstico nativo de runtime (`--diagnostico-runtime`) com campos canônicos pt-BR e campos de compatibilidade;
- auditoria formal de paridade de opcode/feature entre VM Python e VM nativa.
- opcodes de exceção implementados (`THROW`, `PUSH_TRY`, `END_*`);
- `AWAIT` implementado no modo sequencial;
- `IMPORT_NAME` implementado para módulos `.tbc`;
- `executar` e `compilar` disponíveis no binário nativo por ponte de compatibilidade via standalone.

### Ainda pendente para fechar 100%

- `executar .trm` nativo;
- `compilar .trm` nativo;
- remover ponte standalone e operar com backend nativo completo;
- import nativo direto de `.trm`;
- runtime async avançado (scheduler concorrente completo).

Documento de auditoria:
- `docs/V2_FASE2_PARIDADE_VM_NATIVA.md`

## Contratos canônicos pt-BR da CLI

Comandos oficiais:
- `trama executar`
- `trama compilar`
- `trama executar-tbc`

Aliases em inglês existem apenas para compatibilidade.

Documento de contratos:
- `docs/CLI_NATIVA_V2_CONTRATOS.md`

## Situação real de uso

Hoje já é possível:
- programar em Trama com sintaxe canônica pt-BR;
- compilar para `.tbc`;
- executar `.tbc` via runtime nativo C.

Hoje ainda não é possível (100% nativo):
- compilar `.trm` para `.tbc` no backend nativo sem caminho Python.
