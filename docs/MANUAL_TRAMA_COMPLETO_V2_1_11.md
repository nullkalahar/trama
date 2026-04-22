# Manual Trama Completo - ate v2.1.11

## 1. Resumo executivo

A v2.1.11 fecha o bloco de modularizacao do runtime web/realtime iniciado em `v2.1.4`.

Objetivo tecnico:
- manter a superficie canônica pt-BR intacta para usuarios da linguagem;
- separar responsabilidades internas para facilitar evolucao de engine HTTP e transporte de tempo real.

## 2. O que mudou na arquitetura

Antes:
- `web_runtime.py` concentrava modelo web, engine HTTP, core realtime e transportes.

Depois:
- modelo web separado (`web_model.py`, `web_app_model.py`);
- engine HTTP abstraida por fachada (`web_engine.py`);
- core realtime separado (`realtime_core.py`);
- fallback HTTP separado (`realtime_fallback_http.py`);
- WebSocket separado (`realtime_websocket.py`).

## 3. Mapa de modulos

- `web_runtime.py`
  - fachada publica e ponto de compatibilidade.
- `web_model.py`
  - tipos de rota e politicas de rate limit.
- `web_app_model.py`
  - configuracao padrao de `WebApp`.
- `web_engine.py`
  - contrato `EngineRuntimeHttp` e `EngineHttpServerLegado`.
- `realtime_core.py`
  - estado e regras de negocio de tempo real.
- `realtime_fallback_http.py`
  - fluxo de conexao/recebimento/envio no fallback HTTP.
- `realtime_websocket.py`
  - handshake, loop e mensagens WebSocket.

## 4. Guia de desenvolvimento

### 4.1 Alterar comportamento de presenca/sala/ack

Edite:
- `src/trama/realtime_core.py`

Valide:
- `tests/test_realtime_v203.py`

### 4.2 Alterar contrato fallback HTTP

Edite:
- `src/trama/realtime_fallback_http.py`

Valide:
- cenarios de reconexao por cursor em `tests/test_realtime_v203.py`.

### 4.3 Alterar handshake ou loop WebSocket

Edite:
- `src/trama/realtime_websocket.py`

Valide:
- cenarios de realtime em `tests/test_realtime_v203.py`.

## 5. Backplane distribuido

### 5.1 Interface

`BackplaneTempoReal` define:
- `set_disponivel`;
- `publicar_evento`;
- `coletar_eventos`.

### 5.2 Fabrica

`criar_backplane_tempo_real(...)`:
- `memoria`/`memory`: backend de referencia local;
- `redis`: backend distribuido real.

## 6. Testes obrigatorios da trilha

- paridade de engine:
  - `tests/test_web_engine_paridade_v216.py`
- core e transportes:
  - `tests/test_realtime_v203.py`
  - `tests/test_realtime_modular_v211.py`

## 7. Exemplos oficiais da trilha

- `exemplos/v214/README_EXEMPLOS_V214.md`
- `exemplos/v214/214_01_estado_modular.trm`
- `exemplos/v214/214_02_contingencia_http_modular.trm`
- `exemplos/v214/214_03_websocket_confirmacao_retentativa_modular.trm`
- `exemplos/v214/214_04_barramento_memoria_fabrica.trm`
- `exemplos/v214/214_05_barramento_redis_configuracao.trm`
- `exemplos/v214/214_06_barramento_degradado_recupera.trm`
- `exemplos/v214/214_07_reprocesso_cursor_contingencia_modular.trm`
- `exemplos/v214/214_08_metricas_tempo_real_modular.trm`
- `exemplos/v214/214_09_motor_http_fachada.trm`
- `exemplos/v214/214_10_paridade_motor_fumaca.trm`

## 8. Encerramento de versao

Considerar a trilha `v2.1.4` a `v2.1.11` pronta quando:
- checklist do roadmap estiver marcado;
- suites web/realtime estiverem verdes;
- docs/manuais/operacao publicados;
- exemplos tecnicos publicados e navegaveis.
