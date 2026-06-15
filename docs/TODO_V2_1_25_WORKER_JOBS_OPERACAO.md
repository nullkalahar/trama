# TODO v2.1.25 - Worker standalone e comandos operacionais de jobs

Este documento define a lista interna de execucao da `v2.1.25`, alinhada ao roadmap do `README.md`, mantendo a linguagem e a superficie oficial canonicamente pt-BR.

## 1. Objetivo da versao

Entregar:

- worker standalone para filas de jobs;
- comandos operacionais para filas;
- comandos operacionais para DLQ;
- comandos operacionais para reprocessamento;
- preservacao da sintaxe e da superficie canonica pt-BR em lexer, parser e runtime.

## 2. Regras obrigatorias

- [x] nenhuma palavra-chave nova na linguagem;
- [x] nenhuma regressao em lexer, parser, semantica e VM;
- [x] nomes novos em superficie oficial apenas em pt-BR canonico;
- [x] compatibilidade total com a fachada de jobs da `v2.1.24`;
- [x] qualquer comando novo precisa ter teste automatizado;
- [x] a versao so fecha com manual, exemplos e evidencias executadas.

## 3. Superficie operacional esperada

- [x] `jobs-worker-rodar`
- [x] `jobs-fila-status`
- [x] `jobs-dlq-listar`
- [x] `jobs-dlq-reprocessar`

Comportamento esperado:

- [x] worker consegue carregar handlers a partir de arquivo `.trm`;
- [x] worker consegue processar fila SQL fora do processo que enfileirou;
- [x] comandos operacionais retornam JSON estavel;
- [x] saida texto continua objetiva e legivel.

## 4. Ordem de implementacao

### 4.1 Runtime de jobs

- [x] permitir injetar registro de handlers no backend SQL;
- [x] permitir processamento externo por worker standalone;
- [x] expor helpers internos suficientes para status, DLQ e reprocessamento;
- [x] manter backend `memoria` e `sql` sem regressao.

### 4.2 CLI operacional

- [x] adicionar `jobs-worker-rodar`;
- [x] adicionar `jobs-fila-status`;
- [x] adicionar `jobs-dlq-listar`;
- [x] adicionar `jobs-dlq-reprocessar`;
- [x] adicionar carregamento de handlers `.trm` para o worker.

### 4.3 Testes

- [x] criar `tests/test_jobs_runtime_v225.py`;
- [x] criar `tests/test_cli_v225.py`;
- [x] validar regressao de jobs anteriores;
- [x] validar regressao de lexer/parser/semantica/VM.

### 4.4 Documentacao e exemplos

- [x] criar `docs/LINGUAGEM_V2_1_25.md`;
- [x] criar `docs/MANUAL_TRAMA_COMPLETO_V2_1_25.md`;
- [x] criar `exemplos/v225/`;
- [x] criar `exemplos/v225/README_V225_EXEMPLOS.md`;
- [x] atualizar `README.md` ao concluir a versao.

## 5. Validacao final obrigatoria

- [x] `.venv/bin/pytest -q tests/test_lexer.py tests/test_parser.py tests/test_semantic.py tests/test_jobs_runtime.py tests/test_jobs_runtime_v223.py tests/test_jobs_runtime_v224.py tests/test_jobs_runtime_v225.py tests/test_cli.py tests/test_cli_v225.py tests/test_vm.py`
- [x] `.venv/bin/python -m trama.cli lint exemplos/v225 --json`
