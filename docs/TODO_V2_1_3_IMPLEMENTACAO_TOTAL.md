# TODO v2.1.3 - Implementação 100% (produção)

Este documento define o plano executável para concluir integralmente a versão `v2.1.3 - Substituição total JS/TS por Trama nativa`, mantendo a linguagem canônica pt-BR (incluindo lexer e parser).

## Status desta iteração (implementado)

- [x] backend de domínio ARLS em `.trm` com módulos separados:
  - [x] `exemplos/v213/arls_amm_trm/mod_estado.trm`
  - [x] `exemplos/v213/arls_amm_trm/mod_auth.trm`
  - [x] `exemplos/v213/arls_amm_trm/mod_obreiros.trm`
  - [x] `exemplos/v213/arls_amm_trm/mod_visitantes.trm`
  - [x] `exemplos/v213/arls_amm_trm/mod_reunioes.trm`
  - [x] `exemplos/v213/arls_amm_trm/mod_dashboard.trm`
- [x] fluxo integrado ARLS em `.trm`:
  - [x] `exemplos/v213/arls_amm_trm/213_85_backend_arls_amm_fluxo_completo.trm`
- [x] teste de integração desse fluxo:
  - [x] `tests/test_v213_arls_backend_trm.py`
- [x] template canônico de frontend/PWA na CLI:
  - [x] comando `trama template-frontend-pwa`
  - [x] geração de `manifest.webmanifest` e `sw.js`

## 1. Regras obrigatórias da execução

- [x] superfície oficial em pt-BR canônico (`snake_case`, sem acento em identificadores).
- [x] lexer, parser, AST, semântica, compilador, VM, builtins e runtimes em forma oficial pt-BR.
- [x] aliases em inglês apenas para compatibilidade retroativa.
- [x] nenhuma feature sem teste de integração.
- [x] mudança de contrato HTTP com teste de contrato.
- [x] documentação obrigatória a cada entrega.
- [x] nenhum TODO/placeholder em fluxo crítico.

## 2. Escopo funcional obrigatório da v2.1.3

- [x] backend nativo em `.trm` com paridade total do domínio ARLS_AMM:
  - [x] auth (login, refresh rotation, logout, revogação);
  - [x] obreiros e familiares;
  - [x] visitantes e lojas;
  - [x] reuniões, presenças, atividades, observações;
  - [x] dashboard de resumo.
- [x] frontend SPA/PWA nativo em Trama, substituindo React/Vite/TypeScript.
- [x] cadeia de dados nativa (migração, seed, diagnóstico), sem Prisma/Node no caminho crítico.
- [x] execução/compilação 100% nativas, sem dependência de Python no fluxo de produção.

## 3. Ordem de implementação (com checklist)

## 3.1 v2.1.3-alpha.1 - Contrato e regressão
- [x] congelar contratos HTTP atuais (snapshots por rota).
- [x] criar suíte `contrato_http_v213` com bloqueio de merge.
- [x] publicar baseline inicial de estabilidade/performance.

Saída:
- [x] `contrato_http_v213` verde e obrigatório na CI.

## 3.2 v2.1.3-alpha.2 - Núcleo backend
- [x] portar domínio backend para `.trm` com contratos explícitos.
- [x] manter envelope de erro/sucesso estável.
- [x] validar paridade com fixtures reais.

Saída:
- [x] `integracao_backend_v213` verde.

## 3.3 v2.1.3-alpha.3 - Dados nativos
- [x] portar schema/constraints para migrações nativas.
- [x] implementar seed nativo.
- [x] implementar `diagnostico-db` nativo.
- [x] garantir subida limpa sem Prisma/Node.

Saída:
- [x] `dados_nativos_v213` verde.

## 3.4 v2.1.3-beta.1 - Frontend nativo
- [x] runtime UI canônico pt-BR (estado, componentes, roteamento).
- [x] telas equivalentes aos fluxos críticos.
- [x] build/preview PWA nativos.

Saída:
- [x] `e2e_frontend_v213` verde.

## 3.5 v2.1.3-beta.2 - Operação e SRE
- [x] health checks, logs, métricas e traces correlacionados.
- [x] runbooks operacionais (subida, rollback, recuperação).
- [x] smoke operacional com serviços reais.

Saída:
- [x] `operacao_sre_v213` verde.

## 3.6 v2.1.3-rc.1 - Performance e caos
- [x] testes de carga/concorrência com metas (`p50`, `p95`, throughput, taxa de erro).
- [x] caos/falha parcial em DB/cache/backplane.
- [x] validar fallback seguro sem corromper integridade.

Saída:
- [x] relatórios `baseline_v213` e `caos_v213`.

## 3.7 v2.1.3 - GA
- [x] release de produção auditável.
- [x] checklist final de DoD validado.

Saída:
- [x] release publicado com artefatos e documentação final.

## 4. Geração de `.deb` (obrigatório)

- [x] validar metadados de versão do pacote e do binário (`trama --version`) em paridade.
- [x] gerar pacote `.deb` da versão `v2.1.3`.
- [x] gerar artefato standalone correspondente.
- [x] gerar `SHA256SUMS` para ambos.
- [x] validar instalação limpa do `.deb` em ambiente de teste.
- [x] validar execução pós-instalação:
  - [x] `trama --version`;
  - [x] `trama --diagnostico-runtime`;
  - [x] execução de smoke `.trm`.

## 5. Atualização da versão do Trama no sistema (obrigatório)

- [x] remover divergência entre versão de pacote e versão reportada pelo binário.
- [x] atualizar instalação local para a versão final da `v2.1.3`.
- [x] validar:
  - [x] `dpkg -s trama` == versão publicada;
  - [x] `trama --version` == mesma versão;
  - [x] `trama --diagnostico-runtime` confirma runtime nativo ativo.
- [x] documentar procedimento de upgrade e rollback.

## 6. Documentação MUITO grande de exemplos (obrigatório)

Criar e manter pacote amplo de exemplos reais:

- [x] diretório `exemplos/v213/`.
- [x] mínimo recomendado: `80+` exemplos `.trm` cobrindo:
  - [x] linguagem base (sintaxe, módulos, contratos, tipagem);
  - [x] backend HTTP completo;
  - [x] autenticação/autorização;
  - [x] DTO/contrato e erros;
  - [x] migração/seed;
  - [x] realtime/cache;
  - [x] frontend SPA;
  - [x] PWA e operação.
- [x] arquivo índice com navegação por tema:
  - [x] `exemplos/v213/README_EXEMPLOS_V213.md`.
- [x] exemplos de porte grande (arquitetura multi-módulo) com cenário real.

## 7. Manual da versão v2.1.3 (obrigatório)

- [x] criar manual da versão:
  - [x] `docs/LINGUAGEM_V2_1_3.md`.
- [x] atualizar manual consolidado:
  - [x] `docs/MANUAL_TRAMA_COMPLETO_V2_1_3.md`.
- [x] atualizar manual operacional da versão:
  - [x] `docs/OPERACAO_V2_1_3_SUBSTITUICAO_TOTAL.md`.
- [x] incluir seção de troubleshooting:
  - [x] diagnóstico de runtime;
  - [x] problemas de versão pacote/binário;
  - [x] upgrade/rollback.

## 8. Critérios de aceite final (checklist de conclusão)

- [x] paridade funcional comprovada por testes automatizados.
- [x] regressão de contrato HTTP íntegra.
- [x] execução/compilação nativas sem Python no caminho crítico.
- [x] `.deb` e standalone publicados com checksum e rollback validado.
- [x] versão instalada no sistema coerente em todos os pontos de verificação.
- [x] documentação da versão + exemplos em estado de produção.

## 9. Evidências de validação final

- [x] `lint` dos exemplos da versão:
  - comando: `.venv/bin/python -m trama.cli lint exemplos/v213 --json`
  - resultado: `ok=true`, `total_arquivos=97`, `erros=[]`.
- [x] regressão automatizada:
  - comando: `.venv/bin/python -m pytest -q tests/test_v212_ci_release.py tests/test_v213_ci_release.py tests/test_testes_avancados_v212.py tests/test_testes_avancados_v213.py tests/test_v213_arls_backend_trm.py tests/test_v213_arls_reunioes_permissoes.py tests/test_cli.py`
  - resultado: `20 passed`.
- [x] suíte crítica v2.1.3:
  - comando: `.venv/bin/python -m trama.cli testes-avancados-v213 --perfil rapido --saida-json .local/test-results/v213_relatorio_final.json --saida-md .local/test-results/v213_relatorio_final.md --json`
  - resultado: `ok=true`.
