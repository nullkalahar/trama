# Manual Trama completo ate v2.0.9

Este manual consolida as capacidades acumuladas ate a v2.0.9, com foco no fechamento do ciclo nativo.

## Consolidado v2.0.1 -> v2.0.9

- v2.0.1: ORM/migracoes de producao.
- v2.0.2: DTO, validacao profunda e contrato HTTP versionado.
- v2.0.3: realtime distribuido com cursor/ack/nack/retry.
- v2.0.4: cache distribuido com coerencia, lock e fallback.
- v2.0.5: seguranca de producao (refresh rotation, revogacao, hardening, rate-limit).
- v2.0.6: tooling backend (OpenAPI, SDK, CLI admin/op).
- v2.0.7: observabilidade e SRE (exportadores, dashboards, runbooks, alertas).
- v2.0.8: testes avancados (integracao/e2e/carga/contrato/caos).
- v2.0.9: runtime 100% nativo no caminho critico.

## Novidades centrais da v2.0.9

1. Runtime nativo sem ponte para `executar` e `compilar`.
2. Compilador nativo oficial de `.trm` para `.tbc`.
3. Import nativo direto de `.trm` com autocompilacao de modulo.
4. Scheduler async concorrente com timeout/cancelamento.
5. Pipeline de release nativo com standalone + `.deb` e diagnostico explicito.

## Fluxo recomendado de uso (nativo)

```bash
bash scripts/build_native_stub.sh
./dist/native/trama-native compilar exemplos/v209/209_01_compilacao_nativa_basica.trm -o .local/tests/v2_0_9/209_01.tbc
./dist/native/trama-native executar-tbc .local/tests/v2_0_9/209_01.tbc
./dist/native/trama-native executar exemplos/v209/209_04_async_tarefas_timeout_cancelar.trm
./dist/native/trama-native --diagnostico-runtime
```

## Garantias operacionais

- comandos oficiais canonicos em pt-BR preservados no binario nativo.
- aliases de compatibilidade mantidos sem promover ingles como superficie principal.
- erros de runtime nativo com mensagens deterministicas para cenarios cobertos.
- testes de regressao de runtime nativo ativos em CI local por pytest.

## Artefatos de operacao/documentacao

- manual de versao: `docs/LINGUAGEM_V2_0_9.md`
- guia operacional nativo: `docs/OPERACAO_RUNTIME_NATIVO_V2_0_9.md`
- exemplos oficiais: `exemplos/v209/`
- script local de validacao: `.local/tests/v2_0_9/run_local_v209.sh`
