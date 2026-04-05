# Exemplos da Trama

Este diretório traz exemplos cobrindo recursos da linguagem do v0.1 ao v2.0.5.

## Como executar

```bash
trama executar exemplos/01_ola_mundo.trm
```

## Índice

- `01_ola_mundo.trm`: saída básica
- `02_funcoes_e_closure.trm`: funções e closure
- `03_controle_fluxo.trm`: `se/senão`, `enquanto`, `pare`, `continue`
- `04_tente_pegue_finalmente.trm`: tratamento de erro
- `05_colecoes_e_json.trm`: listas/mapas + JSON
- `06_importe_modulo.trm`: `importe` com módulo local
- `07_async_tarefas.trm`: `assíncrona`, `aguarde`, tarefas
- `08_io_arquivos.trm`: IO síncrono/assíncrono
- `09_http_cliente.trm`: cliente HTTP
- `10_web_basico.trm`: servidor web simples
- `11_web_handler_dinamico.trm`: rota dinâmica com parâmetros
- `12_segurança_jwt_rbac.trm`: JWT e RBAC
- `13_observabilidade.trm`: logs, métricas e traços
- `14_fila_jobs.trm`: fila/jobs
- `15_db_sqlite_basico.trm`: banco SQL (SQLite)
- `16_migracoes_e_sementes.trm`: migração + semente
- `17_query_builder_orm.trm`: query builder + ORM inicial
- `18_selfhost_compilar_arquivo.trm`: compilação para `.tbc`
- `v11/19_cache_v11.trm`: cache v1.1
- `v11/20_config_segredos_v11.trm`: config/segredos v1.1
- `v11/21_resiliencia_v11.trm`: retry/backoff/circuit breaker v1.1
- `v12/22_storage_local_v12.trm`: storage local v1.2
- `v12/23_midia_gzip_v12.trm`: pipeline de mídia (gzip) v1.2
- `v12/24_multipart_schema_v12.trm`: upload multipart com schema v1.2
- `v13/26_tempo_real_websocket_basico_v13.trm`: websocket básico nativo
- `v13/27_tempo_real_jwt_v13.trm`: websocket com JWT
- `v13/28_tempo_real_salas_v13.trm`: salas/canais
- `v13/29_tempo_real_typing_receipt_v13.trm`: typing/read-receipt
- `v13/30_tempo_real_broadcast_seletivo_v13.trm`: broadcast seletivo
- `v13/31_tempo_real_fallback_ativo_v13.trm`: fallback de transporte
- `v13/32_tempo_real_limites_protecao_v13.trm`: limites e proteção
- `v13/33_tempo_real_observabilidade_v13.trm`: observabilidade realtime
- `v13/34_tempo_real_status_admin_v13.trm`: status administrativo
- `v13/35_tempo_real_backend_integrado_v13.trm`: backend integrado com realtime
- `v14/25_observabilidade_dashboard_v14.trm`: correlação (`id_requisicao/id_traco/id_usuario`), dashboard e alertas v1.4
- `v15/36_tempo_real_ack_retry_v15.trm`: realtime com ack/retry/reenvio
- `v15/37_socketio_compat_v15.trm`: compatibilidade Socket.IO mínima
- `v15/38_eventos_sociais_alertas_v15.trm`: eventos sociais e alertas em tempo real
- `v15/48_realtime_publicar_ack_manual_v15.trm`: publicação com ACK manual
- `v15/49_realtime_nack_reenvio_v15.trm`: reenvio de pendências ACK
- `v15/50_realtime_socketio_evento_custom_v15.trm`: evento custom compat Socket.IO
- `v15/51_realtime_status_multicanais_v15.trm`: status administrativo multi-canais
- `v15/52_realtime_fallback_jwt_eventos_v15.trm`: fallback JWT ponta a ponta
- `v16/39_comunidades_guildas_v16.trm`: comunidades/guildas, cargos e permissões
- `v16/40_moderacao_completa_v16.trm`: moderação (report/ban/mute) em comunidade
- `v16/53_social_multicomunidades_v16.trm`: múltiplas comunidades
- `v16/54_social_canais_cargos_v16.trm`: criação de canais/cargos
- `v16/55_social_moderacao_pipeline_v16.trm`: pipeline de moderação
- `v16/56_social_permissoes_por_cargo_v16.trm`: permissões por cargo
- `v17/41_admin_auditoria_v17.trm`: APIs administrativas com auditoria
- `v17/42_campanhas_push_v17.trm`: campanhas push (criar/agendar/executar/status)
- `v17/43_metricas_campanha_v17.trm`: métricas operacionais de campanhas
- `v17/57_admin_auditoria_lote_v17.trm`: auditoria em lote
- `v17/58_campanha_segmentada_v17.trm`: campanha segmentada
- `v17/59_campanha_execucoes_multiplas_v17.trm`: múltiplas execuções por campanha
- `v17/60_admin_metricas_snapshot_v17.trm`: métricas de runtime/admin
- `v18/44_upload_midia_persistencia_v18.trm`: upload/persistência de mídia com storage
- `v18/45_sync_incremental_offline_v18.trm`: sync incremental por cursor + cache offline
- `v18/46_sync_conflito_v18.trm`: resolução de conflito em sincronização offline
- `v18/47_deploy_observabilidade_v18.trm`: endpoint de observabilidade e alertas
- `v18/61_sync_cursor_paginado_v18.trm`: paginação por cursor
- `v18/62_cache_offline_namespaces_v18.trm`: cache offline por namespace
- `v18/63_sync_conflito_estrategias_v18.trm`: estratégias de conflito
- `v18/64_storage_lista_url_v18.trm`: listagem/url de storage local
- `v18/65_deploy_health_paths_v18.trm`: endpoints de saúde (saude/pronto/vivo)
- `v18/66_observabilidade_alerta_custom_v18.trm`: alerta customizado de erro/latência
- `v201/README_V201_EXEMPLOS.md`: coleção v2.0.1 (ORM, schema diff, migrações/rollback/seed)
- `v201/201_relacoes_orm.trm` até `v201/215_migracao_compatibilidade_assinatura.trm`: exemplos detalhados de produção para ORM e migrações
- `v202/README_V202_EXEMPLOS.md`: coleção v2.0.2 (DTO, validação profunda, contrato HTTP versionado)
- `v202/202_01_dto_validar_basico.trm` até `v202/202_12_dto_sanitizacao_avancada.trm`: exemplos focados em DTO/contrato e retrocompatibilidade
- `v203/README_V203_EXEMPLOS.md`: coleção v2.0.3 (realtime distribuído, cursor de reconexão, ack/nack/reenvio)
- `v203/203_01_distribuicao_config_status.trm` até `v203/203_06_backplane_indisponivel_degradado.trm`: cenários de presença/salas multi-instância, broadcast distribuído, limites e degradação de backplane
- `v204/README_V204_EXEMPLOS.md`: coleção v2.0.4 (cache distribuído, coerência, fallback, métricas)
- `v204/204_01_cache_distribuido_basico.trm` até `v204/204_07_web_rota_cache_resposta.trm`: cenários de produção para cache multi-instância, invalidação remota e integração HTTP
- `v205/README_V205_EXEMPLOS.md`: coleção v2.0.5 (segurança de produção, revogação, hardening e abuso)
- `v205/205_01_auth_sessao_refresh_rotacao.trm` até `v205/205_07_realtime_token_revogado.trm`: fluxos reais de sessão/dispositivo, denylist, rate-limit distribuído, CORS estrito e auditoria sensível
- `sintaxe/01_expressoes_multilinha.trm`: lista/mapa/chamada multilinha
- `sintaxe/02_encadeamento_multilinha.trm`: encadeamento com indexação multilinha
- `anilist/README_ANILIST_EXEMPLOS.md`: coleção completa de integrações AniList (anime/mangá + DB em `.local/tests/anilist/`)

## Exemplos de Backend (robustos)

Em `exemplos/backend/` há uma coleção completa para cenários de backend:

- `backend/01_api_crud_versionada.trm`: API CRUD versionada
- `backend/02_api_auth_jwt_rbac.trm`: autenticação/autorização
- `backend/03_api_middlewares_rate_limit.trm`: middleware + limite de taxa
- `backend/04_api_contrato_versao.trm`: contrato de API versionado
- `backend/05_api_observabilidade_v14.trm`: observabilidade v1.4
- `backend/06_db_sqlite_crud_repositorio.trm`: persistência com SQLite
- `backend/07_db_transacoes_consistencia.trm`: transações
- `backend/08_db_migracoes_sementes_versionadas.trm`: migrações/sementes
- `backend/09_jobs_fila_idempotencia.trm`: jobs e idempotência
- `backend/10_cache_ttl_invalida.trm`: cache TTL/invalidação
- `backend/11_resiliencia_retry_circuito.trm`: retry/circuit breaker
- `backend/12_storage_local_upload.trm`: armazenamento local
- `backend/13_backend_completo_integrado.trm`: fluxo backend integrado
- `backend/14_realtime_social_push_integrado_v18.trm`: realtime + social + campanha
- `backend/15_sync_offline_api_v18.trm`: sync incremental + cache offline
- `backend/16_admin_ops_dashboard_v18.trm`: operação com dashboard/alertas

## Observações

- Alguns exemplos dependem de ambiente externo (internet, variáveis de ambiente).
- Para os exemplos de v1.1 com segredos:

```bash
export TRAMA_HOST=localhost
export TRAMA_PORTA=8080
export TRAMA_TOKEN=minha_chave_super_secreta
trama executar exemplos/v11/20_config_segredos_v11.trm
```
