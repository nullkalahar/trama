# Exemplos da Trama

Este diretório traz exemplos cobrindo recursos da linguagem do v0.1 ao v1.4.

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

## Observações

- Alguns exemplos dependem de ambiente externo (internet, variáveis de ambiente).
- Para os exemplos de v1.1 com segredos:

```bash
export TRAMA_HOST=localhost
export TRAMA_PORTA=8080
export TRAMA_TOKEN=minha_chave_super_secreta
trama executar exemplos/v11/20_config_segredos_v11.trm
```
