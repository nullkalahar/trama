# Manual Trama Completo - ate v2.1.17

## 1. Resumo executivo

A trilha `v2.1.12` ate `v2.1.17` consolida:
- engine HTTP ASGI real para `WebRuntime` com fallback automatico para engine legada;
- shutdown gracioso e endpoints de operacao (`/saude`, `/pronto`, `/vivo`) com criterio mais rigido;
- limites operacionais por engine;
- camada formal de capabilities de banco por backend;
- introspecao e diff de schema com foco em paridade SQLite/PostgreSQL.

## 2. Superficie nova da linguagem

### 2.1 Web runtime

- `web_configurar_engine_http(app, engine, fallback_automatico, shutdown_gracioso_segundos, limites)`
  - `engine`: `"legada"` ou `"asgi"`;
  - `limites`: mapa por engine com `max_body_bytes` e `timeout_leitura_segundos`.

### 2.2 Banco

- `db_capacidades(conn)` retorna matriz formal de capacidade do backend.
- `schema_inspecionar(conn)` agora cobre SQLite e PostgreSQL.
- `schema_definir(tabelas, dialeto_sql)` permite declarar dialeto esperado.

### 2.3 CLI

- `trama db-capacidades --dsn <dsn> --json`

## 3. Exemplos oficiais v2.1.17

- `exemplos/v217/README_V217_EXEMPLOS.md`
- `exemplos/v217/217_01_engine_legada_padrao.trm`
- `exemplos/v217/217_02_engine_asgi_configuracao.trm`
- `exemplos/v217/217_03_engine_asgi_contingencia_automatica.trm`
- `exemplos/v217/217_04_saude_pronto_vivo_rigidos.trm`
- `exemplos/v217/217_05_limites_operacionais_por_engine.trm`
- `exemplos/v217/217_06_capacidades_sqlite_runtime.trm`
- `exemplos/v217/217_07_capacidades_postgres_runtime.trm`
- `exemplos/v217/217_08_schema_inspecionar_sqlite.trm`
- `exemplos/v217/217_09_schema_diff_sqlite_com_dialeto.trm`
- `exemplos/v217/217_10_schema_diff_postgres_com_dialeto.trm`
- `exemplos/v217/217_11_cli_db_capacidades_documentado.trm`
- `exemplos/v217/217_12_migracao_seed_backend_neutro.trm`
- `exemplos/v217/217_13_orm_paginacao_backend_neutro.trm`
- `exemplos/v217/217_14_schema_preview_plano_dialeto.trm`
- `exemplos/v217/217_15_fluxo_completo_web_db_v217.trm`

## 4. Comandos essenciais

```bash
trama executar exemplos/v217/217_01_engine_legada_padrao.trm
trama executar exemplos/v217/217_02_engine_asgi_configuracao.trm
trama executar exemplos/v217/217_06_capacidades_sqlite_runtime.trm
trama db-capacidades --dsn sqlite:///./dados/app.db --json
```

## 5. Critério de prontidão operacional

- health/readiness/liveness respondendo conforme estado real;
- limite de payload aplicado por engine;
- matrix de capabilities publicada e consumível via runtime e CLI;
- schema/diff com metadata de dialeto explícita.
