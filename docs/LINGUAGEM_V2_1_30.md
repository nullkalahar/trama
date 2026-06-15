# Trama v2.1.30

Tema: verificação automatizada de breaking changes em contrato.

Entregas:
- comparação IR->IR, OpenAPI->IR ou legado->IR
- detecção automática de:
  - rota removida
  - novo campo obrigatório em requisição
  - remoção de campo obrigatório em resposta
  - troca de tipo de campo de requisição

APIs:
- `tooling_runtime.verificar_breaking_changes_contrato()`
- CLI `contrato-breaking-verificar`
