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
- `exemplos/v20/*`: exemplos práticos do andamento de autossuficiência v2.0.

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

## Base formal para v2.0 (autossuficiência)

- especificação de bytecode canônico v1:
  - [`docs/BYTECODE_V1.md`](BYTECODE_V1.md)
- ABI formal da VM v1:
  - [`docs/ABI_VM_V1.md`](ABI_VM_V1.md)
- matriz de cobertura da linguagem para bytecode/ABI:
  - [`docs/MATRIZ_COBERTURA_BYTECODE_ABI_V1.md`](MATRIZ_COBERTURA_BYTECODE_ABI_V1.md)
- contratos canônicos da próxima etapa de VM/CLI nativa:
  - [`docs/CLI_NATIVA_V2_CONTRATOS.md`](CLI_NATIVA_V2_CONTRATOS.md)

Observação:
- comandos oficiais permanecem canônicos em pt-BR: `executar`, `compilar`, `executar-tbc`;
- aliases em inglês existem apenas para compatibilidade.

## Auditoria da fase 2 (VM/CLI nativas)

- estado real de paridade documentado em:
  - [`docs/V2_FASE2_PARIDADE_VM_NATIVA.md`](V2_FASE2_PARIDADE_VM_NATIVA.md)
- status atual:
  - `executar-tbc` nativo: disponível;
  - `executar` e `compilar` nativos: ainda pendentes;
  - opcodes de exceção/import/await: ainda pendentes no backend nativo C.

## Manuais dedicados da v2.0

- visão geral da versão:
  - [`docs/LINGUAGEM_V2_0.md`](LINGUAGEM_V2_0.md)
- manual prático da fase 2:
  - [`docs/MANUAL_V2_0_FASE2.md`](MANUAL_V2_0_FASE2.md)
