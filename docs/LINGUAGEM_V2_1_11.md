# Trama v2.1.11 - Runtime web/realtime modularizado

## 1. Escopo

Esta versao consolida a trilha tecnica `v2.1.4` ate `v2.1.11` com foco em modularizacao do runtime web/realtime mantendo compatibilidade retroativa da superficie canônica pt-BR.

Entregas principais:
- separacao de modelo web em modulo dedicado;
- fachada de engine HTTP com backend legado padrao;
- extracao do core de tempo real;
- extracao dos transportes fallback HTTP e WebSocket;
- interface formal de backplane distribuido com fabrica explicita;
- endurecimento de cenarios Redis em integracao real.

## 2. Garantia canônica pt-BR

A forma oficial da linguagem permanece pt-BR em:
- lexer;
- parser;
- AST;
- semantica;
- compilador;
- VM;
- builtins e runtimes;
- CLI, docs e exemplos.

A modularizacao aqui e interna de runtime, sem alteracao da gramática da linguagem.

## 3. Modulos novos

- `src/trama/web_model.py`
  - `WebRoute`, `RateLimitPolicy`, `RateLimitDistribuidoPolicy`.
- `src/trama/web_app_model.py`
  - configuracao consolidada de `WebApp`.
- `src/trama/web_engine.py`
  - protocolo de engine HTTP e engine legada padrao.
- `src/trama/realtime_core.py`
  - `TempoRealHub`, `TempoRealConexao` e backplane distribuido.
- `src/trama/realtime_fallback_http.py`
  - transporte fallback HTTP desacoplado.
- `src/trama/realtime_websocket.py`
  - transporte WebSocket desacoplado.

## 4. Compatibilidade

Compromissos mantidos:
- `web_runtime.TempoRealHub` e `web_runtime.TempoRealConexao` seguem publicos via reexport;
- contratos de erro e envelope HTTP preservados;
- transporte fallback e transporte WebSocket com comportamento equivalente ao anterior;
- engine legada continua sendo padrao.

## 5. Validacao oficial

Suites relevantes:
- `tests/test_web_runtime_v202.py`;
- `tests/test_realtime_v203.py`;
- `tests/test_web_engine_paridade_v216.py`;
- `tests/test_realtime_modular_v211.py`.

Execucao recomendada:

```bash
.venv/bin/pytest -q \
  tests/test_realtime_v203.py \
  tests/test_web_runtime_v202.py \
  tests/test_web_cache_v204.py \
  tests/test_web_security_v205.py \
  tests/test_web_observabilidade_v207.py \
  tests/test_web_runtime_multipart.py \
  tests/test_web_engine_paridade_v216.py \
  tests/test_realtime_modular_v211.py
```

## 6. Evidencias minimas de pronto

- modularizacao `v2.1.4` a `v2.1.11` marcada como concluida no roadmap;
- testes web/realtime verdes em CI;
- exemplos tecnicos publicados em `exemplos/v214/`;
- manual e operacao da versao publicados.
