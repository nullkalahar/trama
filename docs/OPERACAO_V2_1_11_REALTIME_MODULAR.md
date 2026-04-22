# Operacao v2.1.11 - runtime web/realtime modular

## 1. Checklist pre-validacao

- ambiente virtual ativo com dependencias de dev;
- redis local disponivel (opcional, recomendado para cenarios distribuidos reais);
- porta de teste livre.

## 2. Comandos de validacao tecnica

### 2.1 Suite web/realtime principal

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

### 2.2 Foco Redis distribuido

```bash
.venv/bin/pytest -q tests/test_realtime_v203.py -k redis
```

### 2.3 Sanidade de import/compilacao do pacote

```bash
.venv/bin/python -m compileall -q src/trama
```

## 3. Fluxo rapido de smoke runtime

```bash
trama executar exemplos/v214/214_01_estado_modular.trm
trama executar exemplos/v214/214_04_barramento_memoria_fabrica.trm
trama executar exemplos/v214/214_08_metricas_tempo_real_modular.trm
```

## 4. Diagnostico de falhas comuns

### 4.1 Falha em teste Redis

Sintoma:
- teste `-k redis` falha sem `TRAMA_TEST_REDIS_URL`.

Acao:
- exportar `TRAMA_TEST_REDIS_URL=redis://127.0.0.1:6379/0`;
- ou garantir `redis-server` no PATH.

### 4.2 Erro em fallback HTTP de tempo real

Verifique:
- `fallback_ativo` habilitado;
- prefixo configurado (`/tempo-real/fallback`);
- canal registrado.

### 4.3 Divergencia entre engine padrao e legada explicita

Acao:
- executar `tests/test_web_engine_paridade_v216.py`;
- comparar headers/envelopes/codigos de erro.

## 5. Rollback tecnico da modularizacao

Se necessario rollback cirurgico:
1. reverter apenas modulos novos (`web_app_model.py`, `web_engine.py`, `web_model.py`, `realtime_core.py`, `realtime_fallback_http.py`, `realtime_websocket.py`);
2. restaurar `web_runtime.py` monolitico da versao anterior;
3. executar suites web/realtime novamente.

## 6. Criterio de operacao estavel

- todas as suites acima verdes;
- cenarios Redis de integracao passando;
- exemplos v214 executando sem regressao de contrato.
