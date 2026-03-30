# Trama v1.5-v1.8

Este documento registra as entregas da Trama v1.5-v1.8 com foco em backend robusto e API canônica pt-BR.

## v1.5 - Realtime avançado

### Recursos

- WebSocket nativo com autenticação JWT.
- Compatibilidade Socket.IO mínima para frames `42["evento", {...}]`.
- Mensageria com `id_mensagem`, ordenação por canal, `ack/nack`, retry e reenvio de pendências.

### Builtins canônicos

- `web_tempo_real_publicar(app, canal, evento, dados, opcoes)`
- `web_tempo_real_confirmar_ack(app, canal, id_mensagem, id_conexao, status)`
- `web_tempo_real_reenviar_pendentes(app, canal, id_mensagem?)`

### Compatibilidade

- `web_realtime_publicar`
- `web_realtime_confirmar_ack`
- `web_realtime_reenviar_pendentes`

## v1.6 - Comunidades/guildas

### Recursos

- Comunidades, canais, cargos, membros e permissões por escopo.
- Moderação com ações: `reportar`, `banir`, `mutar`, `expulsar`, `soft_delete`.

### Builtins canônicos

- `comunidade_criar`, `comunidade_obter`, `comunidade_listar`
- `canal_criar`, `cargo_criar`
- `membro_entrar`, `membro_sair`, `membro_atribuir_cargo`
- `comunidade_permissao_tem`
- `moderacao_acao`, `moderacao_listar`

## v1.7 - Admin + campanhas push

### Recursos

- Auditoria administrativa com trilha de eventos.
- Campanhas push com criação, agendamento, execução, status e listagem.
- Métricas operacionais de runtime para eventos administrativos/campanhas.

### Builtins canônicos

- `admin_auditoria_registrar`, `admin_auditoria_listar`
- `campanha_criar`, `campanha_agendar`, `campanha_executar`, `campanha_status`, `campanha_listar`

## v1.8 - Mídia + offline/sync + deploy

### Recursos

- Upload/persistência de mídia com storage local/S3 compatível.
- Cache offline e sincronização incremental por cursor.
- Resolução de conflito (`last_write_wins`, `local`, `remoto`).
- Operação com Docker, `.deb` e standalone.

### Builtins canônicos

- `sync_registrar_evento`, `sync_consumir`, `sync_cursor_atual`, `sync_resolver_conflito`
- `cache_offline_salvar`, `cache_offline_obter`, `cache_offline_listar`

## Testes de validação

- `PYTHONPATH=src .venv/bin/python -m pytest -q`
- `PYTHONPATH=src .venv/bin/python -m trama.cli lint exemplos`
- `bash .local/tests/v1_5_v1_8/run_local_v158.sh`
