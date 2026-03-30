# Exemplos AniList na Trama

Esta pasta mostra integrações reais com a API GraphQL do AniList e persistência em SQLite local para testes.

## Banco de dados de teste

Todos os exemplos gravam em:

- `.local/tests/anilist/anilist_dados.db`

Arquivos auxiliares de saída (relatórios) também são gerados em `.local/tests/anilist/`.

## Exemplos

- `01_anilist_buscar_anime.trm`: busca anime por nome.
- `02_anilist_buscar_manga.trm`: busca mangá por nome.
- `03_anilist_populares_salvar_db.trm`: busca populares e salva no SQLite.
- `04_anilist_cache_consulta.trm`: integração com cache.
- `05_anilist_resiliencia_retry.trm`: retry/backoff/circuit breaker.
- `06_anilist_observabilidade.trm`: métricas, tracing e logs estruturados.
- `07_anilist_sync_anime_manga_db.trm`: sincroniza anime+mangá no banco.
- `08_anilist_top_genero_db.trm`: consulta top no banco local.
- `09_anilist_fila_processamento.trm`: fila/jobs com dados AniList.
- `10_anilist_migracao_seed_relatorio.trm`: migração + seed + log de sync.
- `11_anilist_backend_api_local.trm`: backend local mínimo pós-sync.
- `12_anilist_exportar_json.trm`: exportação de relatório JSON.

## Execução

```bash
trama executar exemplos/anilist/03_anilist_populares_salvar_db.trm
```
