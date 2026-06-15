# TODO v2.1.24 - Backend persistente de jobs via SQL

Este documento define a lista interna de tarefas para executar e implementar a versão `v2.1.24`, com foco em backend persistente de jobs via SQL, mantendo a linguagem e toda a superfície oficial em forma canônica pt-BR.

## 1. Objetivo da versão

Entregar backend persistente de jobs via SQL com:

- retry determinístico;
- leasing de execução;
- DLQ;
- reprocessamento seguro;
- preservação da fachada canônica já publicada em `v2.1.23`.

Escopo direto desta versão:

- runtime de jobs com backend SQL de primeira classe;
- integração com SQLite e PostgreSQL por meio do runtime de banco existente;
- observabilidade operacional mínima para fila persistente;
- documentação, exemplos e testes oficiais da versão.

Fora do escopo direto desta versão:

- worker standalone dedicado;
- comandos operacionais completos de filas/DLQ/reprocessamento por CLI;
- backend Redis para jobs;
- concorrência distribuída completa entre múltiplos workers externos.

Itens acima pertencem às versões seguintes do roadmap (`v2.1.25+`).

## 2. Regras obrigatórias da implementação

- [x] manter lexer, parser, AST, semântica, compilador e VM sem regressão da forma canônica pt-BR;
- [x] não introduzir nova palavra-chave fora do padrão oficial pt-BR;
- [x] qualquer superfície nova exposta para código `.trm` deve nascer em `snake_case`, sem acento em identificadores;
- [x] aliases em inglês, se necessários, apenas como compatibilidade retroativa e nunca como forma principal;
- [x] nenhum comportamento novo entra sem teste automatizado;
- [x] mudanças observáveis de contrato devem ter documentação e exemplos oficiais;
- [x] manter compatibilidade total com `fila_criar`, `fila_criar_com_backend`, `fila_enfileirar`, `fila_processar`, `fila_status` e `fila_backends_listar`.

## 3. Superfície canônica pt-BR esperada

Superfície já existente e que deve ser preservada:

- [x] `fila_criar(nome)`
- [x] `fila_criar_com_backend(nome, backend, opcoes_backend)`
- [x] `fila_backends_listar()`
- [x] `fila_enfileirar(fila, handler, payload, tentativas, timeout_segundos, chave_idempotencia)`
- [x] `fila_processar(fila)`
- [x] `fila_status(fila)`

Superfície adicional aceitável nesta versão, desde que permaneça canônica pt-BR:

- [x] `fila_reprocessar_dlq(fila, limite)`
- [x] `fila_listar_dlq(fila, limite)`
- [x] `fila_obter_job(fila, id_job)`

Se algum destes itens não for implementado diretamente em `.trm`, a mesma capacidade deve existir no runtime Python e ficar documentada como experimental/interna até estabilização.

## 4. Ordem de execução recomendada

### 4.1 Fase A - Modelagem e contratos internos

- [x] definir contrato formal do backend SQL no runtime de jobs:
  - [x] `enqueue(...)`
  - [x] `process_all()`
  - [x] `status()`
  - [x] `reprocess_dlq(...)`, se fizer parte da entrega final;
- [x] definir campos persistidos por job:
  - [x] `id`
  - [x] `fila`
  - [x] `handler`
  - [x] `payload`
  - [x] `status`
  - [x] `tentativas`
  - [x] `tentativas_maximas`
  - [x] `timeout_segundos`
  - [x] `chave_idempotencia`
  - [x] `leased_at` / `lease_expira_em`
  - [x] `ultimo_erro`
  - [x] `disponivel_em`
  - [x] timestamps de criação/atualização/conclusão;
- [x] definir estados formais do job em pt-BR:
  - [x] `pendente`
  - [x] `processando`
  - [x] `concluido`
  - [x] `falhou`
  - [x] `dlq`;
- [x] definir invariantes de transição entre estados;
- [x] definir formato de retorno estável para `fila_processar` e `fila_status`.

Critério de aceite:

- [x] contrato interno do backend SQL documentado e coerente com a fachada existente.

### 4.2 Fase B - Persistência SQL

- [x] projetar schema SQL canônico para jobs persistentes;
- [x] definir compatibilidade entre SQLite e PostgreSQL;
- [x] criar migração oficial da versão para tabelas/índices de jobs;
- [x] criar índices mínimos para:
  - [x] busca por fila/status;
  - [x] leasing expirado;
  - [x] idempotência;
  - [x] DLQ/reprocessamento;
- [x] definir estratégia de serialização do `payload` e do `handler`;
- [x] definir política para `chave_idempotencia` nula ou repetida;
- [x] garantir que o backend em memória continue como padrão de desenvolvimento.

Critério de aceite:

- [x] schema sobe do zero em SQLite e PostgreSQL com paridade mínima de comportamento.

### 4.3 Fase C - Execução com retry, leasing e DLQ

- [x] implementar backend SQL em `src/trama/jobs_runtime.py` ou módulo dedicado;
- [x] registrar backend `sql` na fachada de jobs;
- [x] implementar aquisição de lote pendente com leasing;
- [x] impedir processamento duplicado do mesmo job durante lease ativo;
- [x] implementar retry com atualização persistente de tentativas;
- [x] mover para `dlq` após esgotar tentativas;
- [x] registrar `ultimo_erro` de forma determinística;
- [x] implementar reprocessamento de DLQ preservando idempotência e histórico mínimo;
- [x] garantir que `fila_status` exponha métricas mínimas:
  - [x] `pendentes`
  - [x] `processando`
  - [x] `concluidos`
  - [x] `falhos`
  - [x] `dlq`
  - [x] `backend`.

Critério de aceite:

- [x] fluxo `enfileirar -> processar -> retry -> dlq -> reprocessar` funcional com persistência real.

### 4.4 Fase D - Compatibilidade da linguagem e builtins canônicos

- [x] revisar [src/trama/builtins.py](/home/arara/trama/src/trama/builtins.py) para garantir que a fachada continue canônica em pt-BR;
- [x] revisar lexer/tokens/parser para confirmar que a versão não introduz regressão na sintaxe canônica;
- [x] caso surja nova API exposta em `.trm`, adicionar apenas nomes oficiais pt-BR;
- [x] validar que exemplos e docs não introduzam identificadores oficiais em inglês;
- [x] validar que mensagens de erro novas permaneçam coerentes com o padrão do projeto.

Critério de aceite:

- [x] nenhuma regressão de sintaxe/semântica pt-BR detectada pelos testes de linguagem.

### 4.5 Fase E - Observabilidade e operação mínima

- [x] emitir métricas por backend/fila/status;
- [x] incluir eventos de:
  - [x] enfileiramento;
  - [x] lease adquirido;
  - [x] retry;
  - [x] conclusão;
  - [x] envio para DLQ;
  - [x] reprocessamento;
- [x] garantir inspeção via `admin-jobs-listar` sem quebrar compatibilidade;
- [x] documentar limitações operacionais desta versão:
  - [x] ausência de worker standalone;
  - [x] processamento ainda orientado à fachada atual;
  - [x] diferenças de locking entre SQLite e PostgreSQL.

Critério de aceite:

- [x] estado operacional do backend SQL observável de forma consistente.

## 5. Verificações e testes obrigatórios

### 5.1 Testes unitários e de integração

- [x] adicionar cobertura em `tests/test_jobs_runtime.py` para backend SQL;
- [x] criar `tests/test_jobs_runtime_v224.py` cobrindo a versão;
- [x] cobrir:
  - [x] enfileiramento persistente;
  - [x] idempotência;
  - [x] retry persistente;
  - [x] timeout;
  - [x] DLQ;
  - [x] reprocessamento;
  - [x] leasing simples;
  - [x] status da fila por backend;
  - [x] paridade mínima entre memória e SQL;
- [x] adicionar testes de integração com SQLite real;
- [x] adicionar testes de integração com PostgreSQL real quando a fixture estiver disponível;
- [x] validar que a CLI e as métricas existentes não regrediram.

### 5.2 Testes de linguagem e compatibilidade canônica pt-BR

- [x] rodar regressão de lexer:
  - [x] `tests/test_lexer.py`
- [x] rodar regressão de parser:
  - [x] `tests/test_parser.py`
- [x] rodar regressão semântica:
  - [x] `tests/test_semantic.py`
- [x] rodar regressão de VM/builtins relevantes:
  - [x] `tests/test_vm.py`
- [x] validar exemplos `.trm` da nova versão com `trama lint`.

### 5.3 Critério objetivo de fechamento

- [x] toda suíte nova da `v2.1.24` verde;
- [x] nenhuma regressão nas suítes de jobs já existentes (`v223`);
- [x] nenhuma regressão nas suítes de linguagem base;
- [x] evidências salvas em relatório/saída reproduzível.

## 6. Manual e documentação da versão

- [x] criar `docs/LINGUAGEM_V2_1_24.md` com:
  - [x] objetivo da versão;
  - [x] superfície canônica pt-BR;
  - [x] contrato do backend SQL;
  - [x] estados de job;
  - [x] exemplos oficiais;
- [x] criar `docs/MANUAL_TRAMA_COMPLETO_V2_1_24.md` com:
  - [x] uso rápido;
  - [x] configuração do backend SQL;
  - [x] limitações da versão;
  - [x] troubleshooting;
- [x] atualizar documentação operacional se necessário com comandos e diagnósticos;
- [x] atualizar `README.md` após entrega para marcar `v2.1.24` como concluída, se todos os critérios forem satisfeitos.

## 7. Exemplos oficiais da versão

- [x] criar diretório `exemplos/v224/`;
- [x] criar `exemplos/v224/README_V224_EXEMPLOS.md`;
- [x] publicar exemplos mínimos da versão:
  - [x] `224_01_fila_sql_basica.trm`
  - [x] `224_02_fila_sql_retry.trm`
  - [x] `224_03_fila_sql_leasing.trm`
  - [x] `224_04_fila_sql_dlq.trm`
  - [x] `224_05_fila_sql_reprocessamento.trm`
  - [x] `224_06_fila_sql_status_operacional.trm`
  - [x] `224_07_fila_sql_idempotencia.trm`
  - [x] `224_08_fluxo_completo_jobs_sql.trm`;
- [x] garantir que todos os exemplos usem nomes canônicos pt-BR na superfície oficial.

## 8. Sequência executável resumida

- [x] fechar contrato interno do backend SQL;
- [x] implementar schema e persistência;
- [x] implementar leasing, retry, DLQ e reprocessamento;
- [x] validar compatibilidade pt-BR da superfície e ausência de regressão no parser/lexer;
- [x] escrever testes unitários, integração e regressão;
- [x] escrever manual da versão;
- [x] publicar exemplos oficiais;
- [x] executar verificação final e consolidar evidências.

## 9. Evidências finais esperadas

- [x] `tests/test_jobs_runtime.py` preservado e validado em regressão;
- [x] `tests/test_jobs_runtime_v224.py` verde;
- [x] `docs/LINGUAGEM_V2_1_24.md` criado;
- [x] `docs/MANUAL_TRAMA_COMPLETO_V2_1_24.md` criado;
- [x] `exemplos/v224/README_V224_EXEMPLOS.md` criado;
- [x] exemplos `.trm` da versão criados e validados;
- [x] comandos de validação final registrados no fechamento da versão.

## 10. Validação executada nesta entrega

- [x] `.venv/bin/pytest -q tests/test_lexer.py tests/test_parser.py tests/test_semantic.py tests/test_jobs_runtime.py tests/test_jobs_runtime_v223.py tests/test_jobs_runtime_v224.py tests/test_vm.py`
- [x] `.venv/bin/python -m trama.cli lint exemplos/v224 --json`
