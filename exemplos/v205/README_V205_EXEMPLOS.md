# Exemplos v2.0.5 (seguranca de producao)

Colecao ampla de cenarios da v2.0.5 para auth, revogacao, hardening HTTP, auditoria e protecao de abuso.

## Como usar

```bash
trama executar exemplos/v205/205_01_auth_sessao_refresh_rotacao.trm
```

## Auth e sessao

- `205_01_auth_sessao_refresh_rotacao.trm`: sessao + refresh rotation basica.
- `205_02_revogacao_sessao_dispositivo_usuario.trm`: revogacao por dispositivo e usuario.
- `205_08_auth_login_completo.trm`: fluxo de login com access/refresh e claims extras.
- `205_09_refresh_rotation_reuso_detectado.trm`: deteccao de reuso de refresh antigo.
- `205_10_logout_global_usuario.trm`: encerramento global das sessoes do usuario.
- `205_17_revogacao_token_acesso_imediata.trm`: invalidez imediata de token de acesso.

## HTTP hardening e CORS

- `205_05_web_hardening_cors_producao.trm`: ambiente producao com CORS estrito.
- `205_11_web_auth_sessao_ativa.trm`: rota HTTP exigindo sessao JWT ativa.
- `205_14_hardening_multiambiente.trm`: configuracao por ambiente (`dev`, `teste`, `producao`).

## Rate-limit distribuido

- `205_04_web_rate_limit_distribuido.trm`: politica distribuida base.
- `205_12_rate_limit_distribuido_por_usuario.trm`: limite por usuario autenticado.
- `205_13_rate_limit_distribuido_por_ip_rota.trm`: limite combinado por IP + rota.

## Auditoria de seguranca

- `205_06_auditoria_admin_sensivel.trm`: registro de evento administrativo sensivel.
- `205_15_auditoria_consulta_filtrada.trm`: consulta filtrada por ator/acao.
- `205_18_fluxo_admin_completo_v205.trm`: fluxo admin completo com auditoria + rate-limit + hardening.

## Realtime

- `205_07_realtime_token_revogado.trm`: canal realtime com token revogado.
- `205_16_realtime_jwt_sessao_ativa.trm`: canal realtime exigindo sessao ativa.

