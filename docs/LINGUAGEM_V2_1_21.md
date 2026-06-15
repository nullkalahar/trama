# Linguagem Trama v2.1.21

## Escopo desta versão

Esta versão consolida três entregas de segurança, mantendo API canônica pt-BR:

- v2.1.19: JWT assimétrico (`RS256`) com chaves locais e `kid`
- v2.1.20: JWK/JWKS com cache, rotação e validação de `iss`/`aud`
- v2.1.21: base OIDC para autenticação federada

## Princípios canônicos pt-BR

- superfície oficial em português brasileiro
- aliases legados mantidos apenas para compatibilidade
- mensagens de erro e diagnósticos em pt-BR

## Builtins novos (canônicos)

### JWT assimétrico

- `jwt_assinar(payload, chave, exp_segundos, algoritmo, kid, senha_chave)`
- `jwt_validar(token, chave, leeway_segundos, emissor, audiencia)`

Observações:

- `algoritmo` aceita `HS256` e `RS256`
- em `RS256`, `chave` pode ser PEM em texto ou caminho de arquivo
- `kid` é opcional no cabeçalho, mas obrigatório para validação por JWKS

### JWKS

- `jwks_obter(url_jwks, cache_ttl_segundos, timeout_segundos, forcar_refresh)`
- `jwt_validar_jwks(token, url_jwks, leeway_segundos, emissor, audiencia, cache_ttl_segundos, timeout_segundos)`

Comportamento:

- cache em memória por URL de JWKS
- refresh automático quando o `kid` não é encontrado (rotação)
- validação de `iss`/`aud` durante a verificação

### OIDC (base federada)

- `oidc_descobrir_configuracao(issuer_url, timeout_segundos)`
- `oidc_configurar_provedor(nome, issuer_url, audiencia, timeout_segundos, cache_ttl_jwks_segundos)`
- `oidc_validar_token(nome_provedor, token, leeway_segundos, audiencia, emissor)`
- `oidc_listar_provedores()`
- `oidc_remover_provedor(nome)`

Mapeamento de identidade retornado por `oidc_validar_token`:

- `id_usuario_externo` <- `sub`
- `email` <- `email`
- `nome` <- `name` ou `nome`
- `papeis` <- `roles` ou `papeis`

## Aliases de compatibilidade

- `token_assinar` -> `jwt_assinar`
- `token_validar` -> `jwt_validar`
- `token_validar_jwks` -> `jwt_validar_jwks`
- `autenticacao_oidc_descobrir` -> `oidc_descobrir_configuracao`
- `autenticacao_oidc_configurar` -> `oidc_configurar_provedor`
- `autenticacao_oidc_validar` -> `oidc_validar_token`

## Exemplos oficiais desta versão

- `exemplos/v221/221_01_jwt_rs256_assinar_validar.trm`
- `exemplos/v221/221_02_jwt_rs256_com_kid_iss_aud.trm`
- `exemplos/v221/221_03_token_alias_assinar_validar.trm`
- `exemplos/v221/221_04_jwks_obter_cache_refresh.trm`
- `exemplos/v221/221_05_jwt_validar_jwks_com_iss_aud.trm`
- `exemplos/v221/221_06_oidc_descobrir_configuracao.trm`
- `exemplos/v221/221_07_oidc_configurar_e_validar.trm`
- `exemplos/v221/221_08_oidc_multiplos_provedores.trm`
- `exemplos/v221/221_09_oidc_listar_e_remover.trm`
- `exemplos/v221/221_10_fluxo_gateway_federado.trm`

## Erros canônicos relevantes

- `algoritmo JWT não suportado`
- `chave privada RS256 inválida`
- `chave pública RS256 inválida`
- `token RS256 sem 'kid' não pode ser validado por JWKS`
- `chave JWKS não encontrada para o kid informado`
- `claim 'iss' inválida para o emissor esperado`
- `claim 'aud' inválida para a audiência esperada`
- `provedor OIDC não configurado`

## Checklist operacional da versão

- usar rotação de chave com `kid` único por chave
- definir TTL de cache JWKS adequado ao provedor
- validar sempre `iss` e `aud` em produção
- auditar provedores OIDC configurados por ambiente
