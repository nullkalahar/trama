# Linguagem Trama v2.1.22

## Objetivo

Evoluir autorização de RBAC puro para políticas contextuais baseadas em:
- ator
- ação
- recurso
- contexto

Sem quebrar compatibilidade com RBAC existente.

## Superfície nova (pt-BR canônica)

- `autorizacao_politicas_criar(regras, efeito_padrao)`
- `autorizacao_politicas_avaliar(modelo, ator, acao, recurso, contexto)`
- `autorizacao_avaliar(modelo_rbac, usuarios_papeis, ator, acao, recurso, contexto, politicas)`

Aliases canônicos adicionais:
- `politica_autorizacao_criar`
- `politica_autorizacao_avaliar`

## Modelo de política

Cada regra aceita:

- `id`: identificador estável da regra
- `efeito`: `permitir` ou `negar`
- `ator`:
  - `ids`: lista de IDs permitidos/negados
  - `papeis`: lista de papéis permitidos/negados
- `acao`: string ou lista de strings
- `recurso` (opcional): `{ "tipo": ..., "id": ... }`
- `contexto` (opcional): mapa de filtros por chave

`*` pode ser usado como wildcard em campos de regra.

## Ordem de decisão

1. `autorizacao_avaliar` calcula resultado RBAC.
2. Se houver `politicas` e uma regra contextual explícita casar:
   - decisão final vem da política.
3. Sem regra explícita contextual:
   - fallback para RBAC.

## Retorno padronizado

`autorizacao_avaliar` retorna:

- `permitido`
- `origem_decisao`: `politica_explicita` ou `rbac`
- `permitido_rbac`
- `resultado_politica` (detalhes da decisão contextual)

`autorizacao_politicas_avaliar` retorna:

- `permitido`
- `decisao_explicita`
- `regra_id`
- `efeito_aplicado`
- `motivo`

## Exemplos oficiais

- `exemplos/v222/222_01_politica_permitir_basica.trm`
- `exemplos/v222/222_02_politica_negar_contexto_producao.trm`
- `exemplos/v222/222_03_politica_por_papel.trm`
- `exemplos/v222/222_04_politica_por_ator_id.trm`
- `exemplos/v222/222_05_politica_por_recurso_tipo_id.trm`
- `exemplos/v222/222_06_fallback_rbac_sem_regra_explicita.trm`
- `exemplos/v222/222_07_politica_override_rbac.trm`
- `exemplos/v222/222_08_fluxo_api_autorizacao_contextual.trm`

## Compatibilidade

- RBAC legado continua funcional (`rbac_criar`, `rbac_atribuir`, `rbac_tem_permissao`).
- A evolução para políticas é incremental e opcional.
