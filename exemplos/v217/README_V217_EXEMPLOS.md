# Exemplos v2.1.12-v2.1.17 (engine ASGI, operação HTTP e capacidades de banco)

Arquivos desta pasta demonstram:
- seleção de engine HTTP (`legada` e `asgi`) com fallback automático;
- health/readiness/liveness com estado operacional explícito;
- limites operacionais por engine (`max_body_bytes`, `timeout_leitura_segundos`);
- capabilities formais por backend de banco;
- introspecção/diff de schema com dialeto explícito;
- fluxo de migração/seed com backend neutro.

Execute com:

```bash
PYTHONPATH=src .venv/bin/python -m trama.cli executar exemplos/v217/<arquivo>.trm
```

Índice rápido:
- `217_01_engine_legada_padrao.trm`
- `217_02_engine_asgi_configuracao.trm`
- `217_03_engine_asgi_contingencia_automatica.trm`
- `217_04_saude_pronto_vivo_rigidos.trm`
- `217_05_limites_operacionais_por_engine.trm`
- `217_06_capacidades_sqlite_runtime.trm`
- `217_07_capacidades_postgres_runtime.trm`
- `217_08_schema_inspecionar_sqlite.trm`
- `217_09_schema_diff_sqlite_com_dialeto.trm`
- `217_10_schema_diff_postgres_com_dialeto.trm`
- `217_11_cli_db_capacidades_documentado.trm`
- `217_12_migracao_seed_backend_neutro.trm`
- `217_13_orm_paginacao_backend_neutro.trm`
- `217_14_schema_preview_plano_dialeto.trm`
- `217_15_fluxo_completo_web_db_v217.trm`
