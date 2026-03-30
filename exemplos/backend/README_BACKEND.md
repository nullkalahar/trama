# Exemplos de Backend em Trama

Este diretório concentra exemplos de backend usando os recursos já implementados na linguagem Trama (pt-BR canônico).

## Conteúdo

- `01_api_crud_versionada.trm`: API CRUD básica com versionamento.
- `02_api_auth_jwt_rbac.trm`: autenticação JWT + RBAC por rota.
- `03_api_middlewares_rate_limit.trm`: middleware e limite de taxa.
- `04_api_contrato_versao.trm`: contrato de resposta versionado.
- `05_api_observabilidade_v14.trm`: correlação, dashboard e alertas.
- `06_db_sqlite_crud_repositorio.trm`: CRUD com camada de dados.
- `07_db_transacoes_consistencia.trm`: transações e consistência.
- `08_db_migracoes_sementes_versionadas.trm`: migrações e sementes idempotentes.
- `09_jobs_fila_idempotencia.trm`: fila, retries e idempotência.
- `10_cache_ttl_invalida.trm`: cache com TTL e invalidação por padrão.
- `11_resiliencia_retry_circuito.trm`: retry + circuit breaker.
- `12_storage_local_upload.trm`: upload/storage local.
- `13_backend_completo_integrado.trm`: exemplo integrado de API backend.

## Execução

```bash
trama executar exemplos/backend/01_api_crud_versionada.trm
```
