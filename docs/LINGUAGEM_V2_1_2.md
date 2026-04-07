# Trama v2.1.2 - Prontidao backend complexo

## Objetivo

Concluir a prontidao de backend complexo com foco de producao:

- paridade pratica Python/nativo em fluxos criticos;
- carga/concorrencia multi-instancia com degradacao controlada;
- seguranca minima forte, operacao auditavel e release reproduzivel.

## Entregas tecnicas

- runtime de suite critica v2.1.2 em `src/trama/testes_avancados_runtime.py`:
  - `executar_suite_v212`
  - `executar_paridade_python_nativo_fluxos_criticos`
  - `executar_contrato_http_critico_v212`
  - `executar_carga_multi_instancia_v212`
  - `executar_caos_falha_parcial_v212`
  - `executar_seguranca_minima_v212`
- CLI oficial:
  - `trama testes-avancados-v212`
- gates de CI:
  - workflow `ci_trama_v212` com job `suite_critica_v212`
  - gate de merge `gate_v212_obrigatorio`
- release auditavel:
  - workflow `release_trama_v212` com `SHA256SUMS.txt`, metadados e `ROLLBACK.md`

## Superficie canonica pt-BR

- comando oficial em pt-BR: `testes-avancados-v212`;
- identificadores novos em `snake_case`;
- nenhuma keyword/token oficial novo em ingles.

## Suites obrigatorias cobertas

1. Paridade Python/nativo
- modulos/import/export
- async/tarefas/timeout/cancelamento
- erro previsivel com `tente/pegue/finalmente`

2. Contrato HTTP
- envelopes de erro estaveis com `codigo`, `mensagem`, `detalhes`

3. Carga/concorrencia multi-instancia
- medicao de `p50`, `p95`, throughput e taxa de erro
- validacao de entrega realtime entre instancias

4. Caos/falha parcial
- indisponibilidade de DB/cache/backplane
- degradacao controlada e fallback seguro

5. Seguranca minima
- rotacao/revogacao de token
- rate-limit distribuido
- hardening HTTP/CORS por ambiente

## Evidencias

- codigo: `src/trama/testes_avancados_runtime.py`, `src/trama/cli.py`
- testes: `tests/test_testes_avancados_v212.py`, `tests/test_cli_v212.py`, `tests/test_v212_ci_release.py`
- operacao: `docs/OPERACAO_V2_1_2_BACKEND_COMPLEXO.md`
- baseline: `docs/BASELINE_V2_1_2.md`
- referencia 100% de capacidades (lexer/CLI/builtins): `docs/REFERENCIA_CAPACIDADES_V2_1_2.md`

## Referencia de capacidades

A cobertura integral da superficie da linguagem e publicada em:

- `docs/REFERENCIA_CAPACIDADES_V2_1_2.md`

Geracao automatica (fonte de verdade: codigo):

```bash
PYTHONPATH=src .venv/bin/python scripts/gerar_referencia_capacidades.py --saida docs/REFERENCIA_CAPACIDADES_V2_1_2.md
```
