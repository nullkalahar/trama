# Operacao - Runtime nativo v2.0.9

## 1) Build do runtime nativo

```bash
bash scripts/build_native_stub.sh
```

Saida esperada:
- `dist/native/trama-native-stub`
- `dist/native/trama-native`

## 2) Compilar e executar programa `.trm`

```bash
./dist/native/trama-native compilar exemplos/v209/209_01_compilacao_nativa_basica.trm -o .local/tests/v2_0_9/209_01.tbc
./dist/native/trama-native executar-tbc .local/tests/v2_0_9/209_01.tbc
./dist/native/trama-native executar exemplos/v209/209_01_compilacao_nativa_basica.trm
```

## 3) Import nativo de modulo `.trm`

```bash
./dist/native/trama-native executar exemplos/v209/209_03_importe_nativo_modulo.trm
```

Comportamento esperado:
- se `modulo.tbc` nao existir, o runtime compila `modulo.trm` de forma nativa e executa.

## 4) Async concorrente (tarefas/timeout/cancelamento)

```bash
./dist/native/trama-native executar exemplos/v209/209_04_async_tarefas_timeout_cancelar.trm
```

## 5) Diagnostico oficial

```bash
./dist/native/trama-native --diagnostico-runtime
```

Campos obrigatorios para v2.0.9:
- `backend_runtime=nativo_c_vm`
- `backend_compilador=nativo_c_compilador`
- `requer_python_host=nao`

## 6) Release nativo (standalone + .deb)

```bash
bash scripts/build_release_nativo.sh 2.0.9 amd64
```

## 7) Testes automatizados recomendados

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_native_runtime_v20.py tests/test_native_runtime_v209.py
```

## 8) Troubleshooting

1. Erro de link com `floor/trunc`:
- confirmar build com `-lm` em `scripts/build_native_stub.sh`.

2. Falha de concorrencia `Text file busy` em testes:
- usar copia local do binario por teste (ja aplicado em `tests/test_native_runtime_v209.py`).

3. Import de modulo falhou:
- validar caminho relativo do `.trm` a partir do modulo chamador.
- confirmar permissao de escrita para gerar `.tbc` no diretorio alvo.
