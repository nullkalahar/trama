# Contratos da CLI Nativa (Preparação da Fase 2 - v2.0)

Este documento define o contrato canônico pt-BR da CLI nativa da Trama.

## Comandos oficiais (canônicos)

1. `trama executar <arquivo.trm>`
- executa fonte Trama diretamente;
- saída e erros em pt-BR.

2. `trama compilar <arquivo.trm> -o <arquivo.tbc>`
- compila fonte para bytecode v1;
- gera `.tbc` compatível com VM v1.

3. `trama executar-tbc <arquivo.tbc>`
- executa bytecode sem recompilar fonte.

## Compatibilidade

- aliases em inglês podem existir por compatibilidade (`run`, `compile`, `run-tbc`);
- documentação e help oficial permanecem em pt-BR canônico;
- mensagens principais de erro e sucesso devem ser em pt-BR.

## Contrato de mensagens (pt-BR)

Padrão mínimo:

- sucesso:
  - `Bytecode salvo em: <caminho>`
  - `Execução concluída.`
- erro:
  - prefixo `Erro: ...`
  - causa objetiva (arquivo inválido, opcode desconhecido, aridade etc.).

## Diagnóstico de runtime

Comando de diagnóstico:

- `trama --diagnostico-runtime`

Campos canônicos planejados/atuais:

- `backend_runtime`
- `backend_compilador`
- `requer_python_host`

Campos de compatibilidade:

- `runtime_backend`
- `compilador_backend`
- `python_host_required`

## Critérios de pronto para fase 2

- contratos acima documentados no README e neste arquivo;
- comportamento de ajuda/erros em pt-BR consistente;
- testes de CLI cobrindo comandos canônicos e diagnóstico.

## Estado de implementação atual

- `executar-tbc`: nativo C completo.
- `executar` e `compilar`: expostos na CLI nativa com ponte de compatibilidade para binário standalone (`trama`), sem invocação direta de `python`.
- fase 2 só será concluída quando `executar` e `compilar` forem backend nativo integral (sem ponte).
