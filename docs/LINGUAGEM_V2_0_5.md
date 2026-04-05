# Linguagem Trama v2.0.5 - Seguranca de producao

Este documento descreve a entrega da v2.0.5 com foco em seguranca operacional para ambiente de producao, mantendo API canonica pt-BR e compatibilidade retroativa.

## Objetivos da versao

- refresh token rotation com revogacao por sessao/dispositivo/usuario;
- denylist de token com TTL e invalidacao imediata;
- rate-limit distribuido por rota/IP/usuario;
- hardening HTTP com headers de seguranca + CORS estrito por ambiente;
- trilha de auditoria de acoes administrativas sensiveis;
- testes de seguranca para authn/authz e abuso.

## Superficie canonica (pt-BR)

### Auth e sessao

- `auth_sessao_criar(id_usuario, id_dispositivo?, ttl_refresh_segundos?, metadados?)`
- `auth_sessao_obter(id_sessao)`
- `auth_sessao_ativa(id_sessao)`
- `auth_sessao_revogar(id_sessao, motivo?)`
- `auth_sessao_revogar_dispositivo(id_usuario, id_dispositivo, motivo?)`
- `auth_sessao_revogar_usuario(id_usuario, motivo?)`
- `auth_token_acesso_emitir(id_usuario, segredo, exp_segundos?, id_sessao?, id_dispositivo?, permissoes?, claims_extras?)`
- `auth_refresh_emitir(id_usuario, segredo, id_sessao, id_dispositivo?, exp_segundos?, claims_extras?)`
- `auth_refresh_rotacionar(token_refresh, segredo, exp_segundos?)`
- `auth_token_revogar(token, ttl_segundos?, motivo?)`
- `auth_token_revogado(token)`
- `auth_token_limpar_denylist()`

### Auditoria de seguranca

- `seguranca_auditoria_registrar(ator, acao, alvo, resultado, id_requisicao?, id_traco?, origem?, detalhes?)`
- `seguranca_auditoria_listar(limite?, ator?, acao?)`

### Hardening e limite de taxa no runtime web

- `web_configurar_seguranca_http(app, ambiente?, cors_origens?, csp?, headers_seguranca?, auditoria_admin_ativa?)`
- `web_rate_limit_distribuido(app, max_requisicoes, janela_segundos, caminho?, metodo?, chaves?, opcoes?)`

## Aliases de compatibilidade

- `sessao_criar`, `sessao_ativa`, `sessao_revogar`
- `token_revogar`, `token_revogado`
- `refresh_emitir`, `refresh_rotacionar`
- `web_limite_taxa_distribuido`, `web_rate_limit_dist`
- `web_configurar_hardening`, `web_security_configure`

## Integracao com HTTP e realtime

### HTTP (`web_runtime`)

- `_apply_auth` valida token revogado (`TOKEN_REVOGADO`) quando `jwt_validar_revogacao` ativo (padrao `verdadeiro`);
- `_apply_auth` pode exigir sessao ativa por JWT com `jwt_exigir_sessao_ativa`;
- politica distribuida de abuso via `RateLimitDistribuidoPolicy`:
  - escopo por `rota`, `ip`, `usuario`;
  - backend memoria/redis;
  - fallback degradado controlado sem bypass inseguro;
- CORS estrito por ambiente com erro estavel `CORS_ORIGEM_NAO_PERMITIDA`;
- headers de seguranca enviados em todas respostas.

### Realtime/fallback

- autenticacao de websocket/fallback valida token revogado e sessao ativa (quando configurado), com erro estavel.

## Contratos de erro estaveis

Exemplos de codigos emitidos:

- `NAO_AUTENTICADO`
- `TOKEN_INVALIDO`
- `TOKEN_REVOGADO`
- `SESSAO_INVALIDA`
- `RATE_LIMIT_EXCEDIDO`
- `CORS_ORIGEM_NAO_PERMITIDA`

Envelope padrao:

```json
{
  "ok": false,
  "erro": {
    "codigo": "...",
    "mensagem": "...",
    "detalhes": {}
  }
}
```

## Exemplos

Ver `exemplos/v205/`:

- `205_01_auth_sessao_refresh_rotacao.trm`
- `205_02_revogacao_sessao_dispositivo_usuario.trm`
- `205_03_denylist_tokens.trm`
- `205_04_web_rate_limit_distribuido.trm`
- `205_05_web_hardening_cors_producao.trm`
- `205_06_auditoria_admin_sensivel.trm`
- `205_07_realtime_token_revogado.trm`

## Evidencias de teste

- `tests/test_security_runtime_v205.py`
- `tests/test_web_security_v205.py`
- `tests/test_vm.py::test_v205_seguranca_producao_em_vm`

Esses testes cobrem cenario positivo/negativo, abuso, revogacao e concorrencia multi-instancia.
