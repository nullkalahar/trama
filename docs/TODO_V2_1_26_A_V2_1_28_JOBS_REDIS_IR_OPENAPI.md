# TODO v2.1.26-v2.1.28 - Jobs Redis + IR formal de contrato + OpenAPI via IR

Este documento define a lista interna de execucao para concluir as versoes `v2.1.26`, `v2.1.27` e `v2.1.28`, mantendo a Trama canonicamente pt-BR em lexer, sintaxe, parser, semantica, runtime, docs e exemplos.

## 1. Escopo consolidado

### v2.1.26

- [x] backend Redis para jobs;
- [x] concorrencia distribuida controlada por claim atomico;
- [x] DLQ e reprocessamento no backend Redis;
- [x] status operacional de fila no backend Redis.

### v2.1.27

- [x] modelo de contrato/IR formal para HTTP;
- [x] IR cobrindo DTOs, erros, auth, exemplos e versionamento;
- [x] builtins canonicamente pt-BR para gerar/exportar IR;
- [x] CLI para gerar IR formal.

### v2.1.28

- [x] OpenAPI consumindo IR formal;
- [x] geracao de OpenAPI a partir de IR em tooling;
- [x] CLI `openapi-gerar` aceitando IR formal;
- [x] compatibilidade preservada com entrada OpenAPI/legada.

## 2. Regras obrigatorias

- [x] nenhuma palavra-chave nova na linguagem;
- [x] nenhuma regressao de lexer, parser, semantica ou VM;
- [x] superficie nova apenas em nomes pt-BR canonicos;
- [x] documentacao e exemplos oficiais por versao;
- [x] testes automatizados cobrindo runtime, CLI e VM.

## 3. Entregas de codigo

- [x] backend `redis` em `src/trama/jobs_runtime.py`;
- [x] modulo formal de IR em `src/trama/contrato_ir.py`;
- [x] `tooling_runtime` migrado para gerar OpenAPI via IR;
- [x] builtins `web_gerar_ir_contrato` e `web_exportar_ir_contrato`;
- [x] aliases canonicos `web_contrato_ir_gerar` e `web_contrato_ir_exportar`;
- [x] CLI `contrato-ir-gerar`.

## 4. Entregas de documentacao

- [x] `docs/LINGUAGEM_V2_1_26.md`
- [x] `docs/LINGUAGEM_V2_1_27.md`
- [x] `docs/LINGUAGEM_V2_1_28.md`
- [x] `docs/MANUAL_TRAMA_COMPLETO_V2_1_26.md`
- [x] `docs/MANUAL_TRAMA_COMPLETO_V2_1_27.md`
- [x] `docs/MANUAL_TRAMA_COMPLETO_V2_1_28.md`
- [x] `README.md` atualizado

## 5. Entregas de exemplos

- [x] `exemplos/v226/`
- [x] `exemplos/v227/`
- [x] `exemplos/v228/`

## 6. Validacao executada

- [x] `.venv/bin/pytest -q tests/test_lexer.py tests/test_parser.py tests/test_semantic.py tests/test_jobs_runtime.py tests/test_jobs_runtime_v223.py tests/test_jobs_runtime_v224.py tests/test_jobs_runtime_v225.py tests/test_jobs_runtime_v226.py tests/test_tooling_runtime_v206.py tests/test_tooling_runtime_v227_v228.py tests/test_cli.py tests/test_cli_v225.py tests/test_cli_v227_v228.py tests/test_vm.py`
- [x] `.venv/bin/python -m trama.cli lint exemplos/v226 --json`
- [x] `.venv/bin/python -m trama.cli lint exemplos/v227 --json`
- [x] `.venv/bin/python -m trama.cli lint exemplos/v228 --json`
