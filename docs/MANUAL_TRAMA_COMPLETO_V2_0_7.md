# Manual Completo Trama até v2.0.7

Este manual consolida os recursos da linguagem Trama desde o núcleo até as versões v2.0.6 e v2.0.7.

## Pilares

- linguagem canônica pt-BR
- compatibilidade retroativa por aliases
- runtime backend de produção
- observabilidade e operação auditáveis

## Capacidades consolidadas

1. Núcleo da linguagem: lexer/parser/semântica/bytecode/VM.
2. Runtime backend: HTTP, DB, segurança, realtime, cache, jobs.
3. Contratos HTTP/DTO: validação profunda, versão e erros estáveis.
4. Segurança de produção: sessão/dispositivo, rotação de refresh, revogação, hardening.
5. Tooling v2.0.6: OpenAPI, SDK, CLI admin/operação, templates, migração/seed padronizadas.
6. SRE v2.0.7: Prometheus/OTEL, correlação ponta a ponta, dashboards/runbooks, smoke checks.

## Referências por versão

- v2.0.6: `docs/LINGUAGEM_V2_0_6.md`
- v2.0.7: `docs/LINGUAGEM_V2_0_7.md`
- segurança v2.0.5: `docs/LINGUAGEM_V2_0_5.md`
- DTO/contrato v2.0.2: `docs/LINGUAGEM_V2_0_2.md`

## Guia rápido de adoção em projeto novo

1. `trama template-servico ./meu_servico`
2. implementar rotas + DTO/contratos
3. exportar OpenAPI e gerar SDK
4. aplicar migração/seed por ambiente
5. ativar observabilidade e validar smoke checks
6. operacionalizar dashboards/runbooks

## Checklist de produção

- contrato HTTP versionado
- teste de integração e contrato
- segurança (auth/rate-limit/hardening)
- métricas, traces e logs correlacionados
- smoke check operacional em release
