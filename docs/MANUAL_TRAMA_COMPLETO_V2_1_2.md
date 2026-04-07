# Manual Trama Completo ate v2.1.2

Este manual consolida o estado oficial da linguagem ate a versao `v2.1.2`.

## Base consolidada anterior

Para o historico completo ate `v2.1.1`, consultar:

- `docs/MANUAL_TRAMA_COMPLETO_V2_1_1.md`

## Delta oficial v2.1.2

### 1) Qualidade e regressao bloqueante

- suite critica oficial com:
  - unitario
  - integracao multi-instancia
  - contrato HTTP
  - paridade Python/nativo
  - caos/falha parcial
  - seguranca minima de producao
- comando:
  - `trama testes-avancados-v212`
- gate de merge:
  - `.github/workflows/ci.yml` (`suite_critica_v212` + `gate_v212_obrigatorio`)

### 2) Escala e resiliencia

- baseline reproduzivel de desempenho com `p50`, `p95`, throughput e taxa de erro;
- validacao de comportamento multi-instancia (HTTP/realtime);
- validacao de degradacao segura para indisponibilidade de DB/cache/backplane.

### 3) Seguranca, operacao e release

- validacao de rotacao/revogacao de token;
- validacao de rate-limit distribuido e hardening/CORS por ambiente;
- release auditavel com:
  - `standalone`
  - `.deb`
  - `SHA256SUMS.txt`
  - `metadados_release.json`
  - `ROLLBACK.md`

## Artefatos principais da v2.1.2

- codigo:
  - `src/trama/testes_avancados_runtime.py`
  - `src/trama/cli.py`
- testes:
  - `tests/test_testes_avancados_v212.py`
  - `tests/test_cli_v212.py`
  - `tests/test_v212_ci_release.py`
- docs:
  - `docs/LINGUAGEM_V2_1_2.md`
  - `docs/OPERACAO_V2_1_2_BACKEND_COMPLEXO.md`
  - `docs/BASELINE_V2_1_2.md`
  - `docs/REFERENCIA_CAPACIDADES_V2_1_2.md`
