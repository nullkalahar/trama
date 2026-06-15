# TODO v2.1.29 a v2.1.34

Execução interna concluída para o bloco:

1. `v2.1.29`
- unificar geração de SDK Python/TypeScript sobre o IR formal `trama_http_v1`
- manter compatibilidade de entrada com OpenAPI via conversão para IR
- validar geração por API direta e por CLI

2. `v2.1.30`
- comparar contratos entre versões
- detectar remoção de rota, campo obrigatório novo em requisição, remoção de campo obrigatório em resposta e troca de tipo
- expor verificação por API e CLI

3. `v2.1.31`
- formalizar upload com `iniciar -> escrever -> finalizar`
- validar `mime_permitidos`, `tamanho_maximo` e `hash_sha256`
- suportar promoção temporário->definitivo

4. `v2.1.32`
- trocar parse multipart baseado em payload inteiro por fluxo com `FieldStorage` e tempfile
- marcar arquivos grandes como `streaming`
- ampliar teste de upload grande

5. `v2.1.33`
- integrar pipeline de mídia ao storage
- gerar variantes e manifesto
- persistir metadados mínimos de rastreabilidade

6. `v2.1.34`
- formalizar políticas de visibilidade, retenção, lifecycle e URL assinada
- refletir políticas em metadados de storage
- documentar uso para backend local e S3-compatível

Verificações obrigatórias da rodada:
- `pytest` nas suítes de `tooling`, `cli`, `storage`, `media`, `web multipart`, `semantic`, `vm`
- `lint` dos exemplos `v229` a `v234`
