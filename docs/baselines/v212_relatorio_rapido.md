# Relatorio v2.1.2 - Testes Avancados

- ok: `true`
- versao: `2.1.2`
- perfil: `rapido`
- executado_em: `2026-04-07T14:27:20-03:00`
- duracao_ms: `2324.04`

## Suite: unitario

- ok: `true`
- checks:
  - `cache_runtime_importado`: `true`
  - `web_runtime_importado`: `true`
  - `security_runtime_importado`: `true`

## Suite: integracao

- ok: `true`
- latencia_p95_ms: `18.88`
- erro_pct: `0.0`
- throughput_rps: `125.48`
- checks:
  - `realtime_multi_instancia_entrega`: `true`
  - `slo_multi_instancia`: `true`

## Suite: contrato_http

- ok: `true`
- checks:
  - `erro_auth_envelope_estavel`: `true`
  - `erro_validacao_envelope_estavel`: `true`

## Suite: paridade_python_nativo

- ok: `true`
- checks:
  - `modulos_import_export`: `true`
  - `async_tarefa_timeout_cancelamento`: `true`
  - `controle_fluxo_deterministico`: `true`

## Suite: caos_falha_parcial

- ok: `true`
- checks:
  - `db_indisponivel_erro_controlado`: `true`
  - `cache_indisponivel_fallback_seguro`: `true`
  - `backplane_indisponivel_degradado_sem_perda_local`: `true`

## Suite: seguranca

- ok: `true`
- checks:
  - `rotacao_refresh`: `true`
  - `hardening_cors_producao`: `true`
  - `rate_limit_distribuido_ativo`: `true`
