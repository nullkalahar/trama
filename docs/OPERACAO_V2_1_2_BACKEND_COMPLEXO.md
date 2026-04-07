# Operacao v2.1.2 - Backend complexo

## 1) Suite critica obrigatoria

Execucao local rapida:

```bash
trama testes-avancados-v212 --perfil rapido --json
```

Execucao com relatorios:

```bash
trama testes-avancados-v212 \
  --perfil completo \
  --saida-json .local/test-results/v212_relatorio.json \
  --saida-md .local/test-results/v212_relatorio.md
```

Execucao por pytest:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_testes_avancados_v212.py tests/test_cli_v212.py tests/test_v212_ci_release.py
```

## 2) Leitura de baseline/performance

No relatorio v2.1.2:

- `baseline.latencia_p50_ms`
- `baseline.latencia_p95_ms`
- `baseline.throughput_rps`
- `baseline.erro_pct`

Se `suites.integracao.ok=false`, investigar saturacao local (CPU/rede) e repetir com o mesmo perfil.

## 3) Troubleshooting (paridade/falha parcial)

1. Paridade Python/nativo falhou:
- rodar `bash scripts/build_native_stub.sh`;
- validar `dist/native/trama-native --diagnostico-runtime`;
- executar novamente `trama testes-avancados-v212 --perfil rapido`.

2. Falha parcial DB:
- validar DSN e permissao de escrita no diretorio;
- confirmar que erro permanece controlado (sem crash global).

3. Falha parcial cache/backplane:
- confirmar estado degradado em metricas/checks;
- validar que fallback foi aplicado sem corromper integridade.

## 4) Rollback operacional

Checklist de rollback:

1. Validar checksums do pacote alvo:

```bash
sha256sum -c SHA256SUMS.txt
```

2. Rollback de `.deb`:

```bash
sudo apt remove -y trama || true
sudo dpkg -i trama_<VERSAO_ANTERIOR>_amd64.deb
```

3. Rollback de standalone:

```bash
cp trama-standalone-amd64 /opt/trama/bin/trama
chmod +x /opt/trama/bin/trama
```

4. Verificacao final:

```bash
/opt/trama/bin/trama --diagnostico-runtime
```

## 5) Recuperacao pos-incidente

1. Executar smoke HTTP:

```bash
trama operacao-smoke-check --base-url http://127.0.0.1:8000 --json
```

2. Executar suite critica rapida:

```bash
trama testes-avancados-v212 --perfil rapido --json
```

3. Registrar evidencias:
- relatorio JSON/MD;
- hash dos artefatos;
- horario UTC da recuperacao.

## 6) Auditoria de cobertura de documentacao (100%)

Gerar referencia completa a partir do codigo:

```bash
PYTHONPATH=src .venv/bin/python scripts/gerar_referencia_capacidades.py --saida docs/REFERENCIA_CAPACIDADES_V2_1_2.md
```

Validar que a referencia publicada esta atualizada:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_documentacao_capacidades_v212.py
```
