# Exemplos v2.1.19-v2.1.21

Coleção de exemplos canônicos pt-BR para:
- JWT assimétrico RS256 com `kid` (v2.1.19)
- JWK/JWKS com cache, rotação e validação `iss`/`aud` (v2.1.20)
- Base OIDC federada (discovery + validação) (v2.1.21)

## Arquivos

- `221_01_jwt_rs256_assinar_validar.trm`
- `221_02_jwt_rs256_com_kid_iss_aud.trm`
- `221_03_token_alias_assinar_validar.trm`
- `221_04_jwks_obter_cache_refresh.trm`
- `221_05_jwt_validar_jwks_com_iss_aud.trm`
- `221_06_oidc_descobrir_configuracao.trm`
- `221_07_oidc_configurar_e_validar.trm`
- `221_08_oidc_multiplos_provedores.trm`
- `221_09_oidc_listar_e_remover.trm`
- `221_10_fluxo_gateway_federado.trm`

## Observações

- Para execução real de RS256/JWKS/OIDC é necessário ter chaves/URLs válidas.
- Os exemplos usam nomes e fluxo canônicos em pt-BR.
