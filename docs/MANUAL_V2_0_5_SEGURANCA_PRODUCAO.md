# Manual v2.0.5 - Seguranca de Producao (Trama)

Este manual descreve, de forma pratica e operacional, como usar os recursos da v2.0.5 da Trama em producao.

## 1. Visao geral

A v2.0.5 adiciona um pacote de seguranca de runtime com foco em:

- autenticacao com sessao/dispositivo;
- refresh token rotation com deteccao de reuso;
- revogacao imediata por token, sessao, dispositivo e usuario;
- denylist com TTL;
- rate-limit distribuido por rota/IP/usuario;
- hardening HTTP por ambiente (dev/teste/producao);
- CORS estrito em producao;
- auditoria rastreavel de acoes administrativas sensiveis.

Tudo mantendo API canonica pt-BR e aliases de compatibilidade.

## 2. Superficie da linguagem (v2.0.5)

### 2.1 Sessao e autenticacao

- `auth_sessao_criar(id_usuario, id_dispositivo?, ttl_refresh_segundos?, metadados?)`
- `auth_sessao_obter(id_sessao)`
- `auth_sessao_ativa(id_sessao)`
- `auth_sessao_revogar(id_sessao, motivo?)`
- `auth_sessao_revogar_dispositivo(id_usuario, id_dispositivo, motivo?)`
- `auth_sessao_revogar_usuario(id_usuario, motivo?)`
- `auth_token_acesso_emitir(id_usuario, segredo, exp_segundos?, id_sessao?, id_dispositivo?, permissoes?, claims_extras?)`
- `auth_refresh_emitir(id_usuario, segredo, id_sessao, id_dispositivo?, exp_segundos?, claims_extras?)`
- `auth_refresh_rotacionar(token_refresh, segredo, exp_segundos?)`

### 2.2 Revogacao/denylist

- `auth_token_revogar(token, ttl_segundos?, motivo?)`
- `auth_token_revogado(token)`
- `auth_token_limpar_denylist()`

### 2.3 Seguranca HTTP

- `web_configurar_seguranca_http(app, ambiente?, cors_origens?, csp?, headers_seguranca?, auditoria_admin_ativa?)`
- `web_rate_limit_distribuido(app, max_requisicoes, janela_segundos, caminho?, metodo?, chaves?, opcoes?)`

### 2.4 Auditoria

- `seguranca_auditoria_registrar(ator, acao, alvo, resultado, id_requisicao?, id_traco?, origem?, detalhes?)`
- `seguranca_auditoria_listar(limite?, ator?, acao?)`

## 3. Contratos de erro estaveis

Formato padrao:

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

Codigos comuns v2.0.5:

- `NAO_AUTENTICADO`
- `TOKEN_INVALIDO`
- `TOKEN_REVOGADO`
- `SESSAO_INVALIDA`
- `RATE_LIMIT_EXCEDIDO`
- `CORS_ORIGEM_NAO_PERMITIDA`

## 4. Fluxos recomendados de producao

### 4.1 Login inicial

1. validar credenciais de usuario;
2. criar sessao (`auth_sessao_criar`);
3. emitir access token curto (`auth_token_acesso_emitir`);
4. emitir refresh token (`auth_refresh_emitir`);
5. armazenar refresh no cliente com politica segura (cookie httpOnly/secure, quando aplicavel).

### 4.2 Renovacao de token (refresh rotation)

1. cliente envia refresh token atual;
2. backend chama `auth_refresh_rotacionar`;
3. refresh antigo e imediatamente invalidado;
4. se houver reuso de refresh antigo, sessao deve ser revogada.

### 4.3 Logout

- por sessao: `auth_sessao_revogar`;
- por dispositivo: `auth_sessao_revogar_dispositivo`;
- global por usuario: `auth_sessao_revogar_usuario`;
- para corte imediato do JWT em voo: `auth_token_revogar`.

## 5. Hardening HTTP por ambiente

### 5.1 Dev

- CORS mais flexivel;
- CSP mais permissiva para debug local;
- nao usar configuracao de dev em producao.

### 5.2 Teste

- CORS controlado para origens de CI e homologacao;
- CSP intermediaria.

### 5.3 Producao

- CORS estrito (`cors_origens` explicitas);
- CSP explicita por ambiente;
- headers de seguranca ativos por padrao:
  - `Strict-Transport-Security`
  - `X-Content-Type-Options`
  - `X-Frame-Options`
  - `Referrer-Policy`
  - `Content-Security-Policy`

## 6. Rate-limit distribuido

`web_rate_limit_distribuido` permite aplicar limite por combinacao de escopos.

Escopos recomendados:

- `rota`: protege endpoint globalmente;
- `ip`: reduz abuso volumetrico por origem;
- `usuario`: protege uso autenticado por conta.

### 6.1 Opcoes de backend

- `memoria`: bom para testes e cenarios simples;
- `redis`: recomendado para producao multi-instancia.

Quando backend distribuido falha, o runtime degrada com fallback controlado (sem bypass inseguro).

## 7. Auditoria de acoes sensiveis

Registre eventos de admin com:

- ator;
- acao;
- alvo;
- timestamp;
- resultado;
- id_requisicao/id_traco;
- origem;
- detalhes.

Use a auditoria para trilha forense e investigacao de incidentes.

## 8. Boas praticas obrigatorias

- tokens de acesso curtos (ex.: 5 a 15 min);
- refresh com rotacao em toda renovacao;
- revogar refresh e sessao ao detectar reuso;
- habilitar validacao de revogacao em rotas sensiveis;
- exigir sessao ativa para caminhos criticos;
- configurar CORS estrito em producao;
- aplicar rate-limit por rota/IP/usuario;
- registrar auditoria em acao administrativa sensivel.

## 9. Checklist de operacao (go-live)

- [ ] segredos JWT segregados por ambiente;
- [ ] `web_configurar_seguranca_http(..., "producao", ...)` aplicado;
- [ ] politicas de rate-limit definidas para rotas de login/refresh/admin;
- [ ] revogacao por logout validada;
- [ ] deteccao de reuso de refresh validada;
- [ ] trilha de auditoria consultavel;
- [ ] metricas de seguranca no painel de observabilidade.

## 10. Referencias de exemplos

Ver diretorio `exemplos/v205/` e indice em:

- `exemplos/v205/README_V205_EXEMPLOS.md`
- `docs/LINGUAGEM_V2_0_5.md`

