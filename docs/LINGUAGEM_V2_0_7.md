# Trama v2.0.7 - Observabilidade e SRE

A v2.0.7 fecha a camada de observabilidade de produção com exportadores padrão, correlação, dashboards/runbooks e smoke checks.

## Objetivo

Operação observável ponta a ponta com indicadores auditáveis e procedimentos operacionais prontos.

## Novidades da linguagem e runtime

### Exportadores padrão

- `observabilidade_exportar_prometheus()` retorna payload Prometheus compatível (`text/plain`).
- `observabilidade_exportar_otel_json()` retorna payload JSON compatível com coleta OTEL.

Aliases de compatibilidade:

- `observabilidade_exportar_prom`
- `observabilidade_exportar_otlp`

### Endpoints HTTP de observabilidade

Com `web_ativar_observabilidade` ativo:

- `/observabilidade`: resumo completo (métricas, traces, alertas)
- `/alertas`: alertas ativos e limites
- `/metricas`: exportador Prometheus
- `/otlp-json`: exportador OTEL JSON

### Operação e SRE

- `observabilidade_dashboards_prontos()` / `dashboards_operacionais_prontos()`
- `observabilidade_runbooks_prontos()` / `runbooks_incidentes_prontos()`
- `operacao_smoke_checks(base_url, timeout_segundos, caminhos)`
- CLI: `trama operacao-smoke-check --base-url <url> [--timeout] [--json]`

## Correlação

A correlação segue padrão canônico e aliases de compatibilidade:

- `id_requisicao` (`request_id`)
- `id_traco` (`trace_id`)
- `id_usuario` (`user_id`)

## Dashboards prontos

- API HTTP
- Banco de dados
- Tempo real
- Jobs/filas

## Runbooks prontos

- `runbook_api_erro_alto`
- `runbook_latencia_alta`
- `runbook_backplane_indisponivel`

## Testes e validação

Cobertura implementada:

- `tests/test_observability_v207.py`
- `tests/test_web_observabilidade_v207.py`
- `tests/test_vm.py::test_v207_observabilidade_exportadores_e_smoke_em_vm`
- regressão total da suíte.

## DoD v2.0.7 atendido

- operação observável ponta a ponta: exportadores + endpoints + correlação.
- alertas e runbooks prontos para produção: catálogo pronto e smoke checks operacionais.
