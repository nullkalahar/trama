# Exemplos da Trama

Este diretório traz exemplos cobrindo recursos da linguagem do v0.1 ao v1.1.

## Como executar

```bash
trama executar examples/01_ola_mundo.trm
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

## Observações

- Alguns exemplos dependem de ambiente externo (internet, variáveis de ambiente).
- Para os exemplos de v1.1 com segredos:

```bash
export TRAMA_HOST=localhost
export TRAMA_PORTA=8080
export TRAMA_TOKEN=minha_chave_super_secreta
trama executar examples/v11/20_config_segredos_v11.trm
```
