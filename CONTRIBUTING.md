# Contribuindo com a Trama

Este guia define o fluxo oficial de contribuicao da Trama a partir da v2.1.0.

## Principios obrigatorios
- superficie oficial em pt-BR canonico.
- compatibilidade retroativa obrigatoria.
- nenhuma feature sem teste de integracao.
- mudanca de contrato HTTP exige teste de contrato.
- toda entrega exige documentacao atualizada.

## Fluxo de contribuicao
1. crie branch de trabalho (`feat/*`, `fix/*`, `docs/*`, `chore/*`).
2. implemente com testes.
3. atualize docs/changelog.
4. abra PR usando o template obrigatorio.
5. aguarde gate CI (`ci_trama_v210`) e revisao.
6. merge somente com jobs obrigatorios verdes.

## Qualidade minima para merge
- lint: `ruff check src tests`
- testes: `pytest`
- cobertura: minima definida na CI
- seguranca: bandit + pip-audit + scan de segredos
- build nativo sem erro

## Convencao de commits
- `feat:` nova capacidade
- `fix:` correcao
- `docs:` documentacao
- `test:` testes
- `chore:` manutencao
- idioma: pt-BR canonico, objetivo e auditavel

## Alteracoes potencialmente quebraveis
Se houver breaking change:
- documentar em `docs/MIGRACAO_BREAKING_CHANGES.md`;
- marcar no PR e no `CHANGELOG.md`;
- incluir plano de migracao/rollback.

## Seguranca e incidentes
- nao exponha segredos no codigo.
- incidentes devem seguir runbook em `docs/GOVERNANCA_CONTRIBUICAO_V2_1_0.md`.
