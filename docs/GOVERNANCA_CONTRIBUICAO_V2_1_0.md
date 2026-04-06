# Governanca e contribuicao v2.1.0

## Objetivo
Padronizar evolucao tecnica com previsibilidade, rastreabilidade e responsabilidade operacional.

## Papeis
- mantenedor: define direcao, aprova release e incidentes criticos.
- revisor: valida qualidade tecnica e compatibilidade retroativa.
- contribuidor: implementa com testes e documentacao atualizada.

## Politicas obrigatorias
- PR sem gate verde nao faz merge.
- mudanca de contrato HTTP sem teste de contrato nao faz merge.
- breaking change sem guia de migracao nao faz merge.
- API oficial sempre em pt-BR canonico.

## Fluxo de incidente (resumo)
1. detectar e classificar impacto.
2. mitigar (rollback/feature flag/hotfix).
3. registrar causa raiz e acoes corretivas.
4. atualizar runbook/changelog/docs.

## SLA interno sugerido
- incidente critico: resposta inicial em ate 30 min.
- incidente alto: resposta inicial em ate 2 h.
- incidente medio: resposta inicial em ate 8 h.

## Auditoria
Toda release deve ter:
- hash dos artefatos;
- metadados de build;
- changelog e versao semver validos.
