# Operação v2.1.17 - Engine ASGI e Capacidades de Banco

## 1. Objetivo

Padronizar operacao de:
- engine HTTP (`legada`/`asgi`);
- estado de saude/readiness/liveness;
- diagnostico de backend de banco via capabilities.

## 2. Checklist rapido

1. confirmar dependencia ASGI quando `engine=asgi` (`uvicorn`);
2. validar endpoints `/saude`, `/pronto`, `/vivo`;
3. validar limites por engine (`max_body_bytes`);
4. validar capabilities por banco com CLI;
5. manter fallback automatico ativo em ambiente de transicao.

## 3. Comandos de smoke

```bash
trama executar exemplos/v217/217_04_saude_pronto_vivo_rigidos.trm
trama executar exemplos/v217/217_05_limites_operacionais_por_engine.trm
trama db-capacidades --dsn sqlite:////tmp/trama_ops.db --json
```

## 4. Diagnostico de falhas comuns

### 4.1 Falha ao subir engine ASGI

Sintoma:
- inicializacao falha ao configurar `engine=asgi`.

Ação:
- instalar dependencia ASGI (`uvicorn`);
- manter `fallback_automatico=true` para continuar em engine legada.

### 4.2 `/pronto` retorna 503

Sintoma:
- readiness em `503` com status `draining` ou `not_ready`.

Ação:
- verificar ciclo de vida de inicializacao/shutdown;
- checar se instancia esta em drenagem durante deploy.

### 4.3 capabilities incoerentes no banco

Sintoma:
- comando `db-capacidades` nao condiz com backend esperado.

Ação:
- validar DSN usado pela aplicacao;
- confirmar driver/credenciais e ambiente alvo.

## 5. Execução em CI

- workflow inclui job `postgres_real_v215`;
- testes chave:
  - `tests/test_web_engine_asgi_v212_v213.py`
  - `tests/test_db_runtime_postgres_v215.py`
  - `tests/test_db_capacidades_v217.py`
  - `tests/test_cli_db_capacidades_v217.py`
