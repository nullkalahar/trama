# Manual Completo da Trama (até v1.8)

A Trama é uma linguagem canônica pt-BR com foco em backend robusto.

## Base da linguagem

- Controle de fluxo: `se/senão`, `enquanto`, `pare`, `continue`.
- Funções: `função` e `assíncrona função` com `aguarde`.
- Coleções: listas e mapas.
- Erros: `tente/pegue/finalmente`.
- Multilinha: chamadas, listas e mapas em múltiplas linhas.

## Backend HTTP

- App web: `web_criar_app`, `web_rota`, `web_iniciar`, `web_parar`.
- Segurança: JWT e RBAC.
- Contrato/versionamento/rate limit/middlewares.
- Observabilidade: logs estruturados, métricas, tracing, dashboard e alertas.

## Banco e persistência

- SQL: conectar/executar/consultar/transações.
- Query Builder + ORM inicial.
- Migrações/sementes versionadas.
- Storage local/S3 compatível e pipeline de mídia.

## Realtime (v1.3 + v1.5)

- WebSocket nativo + fallback.
- Salas/canais, presença, typing, read-receipt.
- Broadcast seletivo por conexão/usuário/sala.
- `ack/nack`, retry e reenvio de pendências.
- Compat Socket.IO mínima.

## Domínio social/admin (v1.6-v1.7)

- Comunidades/guildas com permissões e moderação.
- Auditoria administrativa.
- Campanhas push com métricas operacionais.

## Offline/sync (v1.8)

- Eventos incrementais por cursor.
- Cache offline versionado.
- Política de conflito configurável.

## Nomenclatura canônica pt-BR

A superfície oficial de API/builtins é em pt-BR.

Aliases em inglês existem apenas para compatibilidade e não substituem a forma canônica.

## Exemplos

Use o diretório `exemplos/`:

- `exemplos/v15/*`: realtime avançado.
- `exemplos/v16/*`: comunidades e moderação.
- `exemplos/v17/*`: admin e campanhas push.
- `exemplos/v18/*`: mídia, sync offline e deploy/observabilidade.

## Deploy

- Standalone: `scripts/build_standalone.sh`
- Debian: `scripts/package_deb.sh <versao> <arch>`
- Docker: `Dockerfile` e `docker-compose.yml`
- Smoke: `scripts/smoke_deploy.sh`
- Healthcheck HTTP: `scripts/healthcheck_http.sh`

## Suíte de validação

- `PYTHONPATH=src .venv/bin/python -m pytest -q`
- `PYTHONPATH=src .venv/bin/python -m trama.cli lint exemplos`
- `bash .local/tests/v1_5_v1_8/run_local_v158.sh`
