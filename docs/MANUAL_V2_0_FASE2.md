# Manual Prático v2.0 Fase 2 (Estado Atual)

## 1. O que já está pronto

1. bytecode/ABI v1 formalizados.
2. execução de `.tbc` no runtime nativo C.
3. diagnóstico de backend com nomenclatura canônica pt-BR.
4. exceções nativas (`THROW`, `PUSH_TRY`, `END_*`).
5. `AWAIT` nativo sequencial.
6. `IMPORT_NAME` nativo para módulos `.tbc`.
7. `executar` e `compilar` expostos no binário nativo por ponte standalone.

## 2. Fluxo recomendado hoje

### Compilar fonte Trama para bytecode

```bash
PYTHONPATH=src .venv/bin/python -m trama.cli compilar arquivo.trm -o arquivo.tbc
```

### Executar bytecode no runtime nativo

```bash
./dist/native/trama-native executar-tbc arquivo.tbc
```

Alias de compatibilidade:

```bash
./dist/native/trama-native run-tbc arquivo.tbc
```

## 3. Diagnóstico de runtime

```bash
./dist/native/trama-native --diagnostico-runtime
```

Saída inclui:
- canônico: `backend_runtime`, `backend_compilador`, `requer_python_host`
- compatibilidade: `runtime_backend`, `compilador_backend`, `python_host_required`

## 4. Build do runtime nativo

```bash
bash scripts/build_native_stub.sh
```

Gera:
- `dist/native/trama-native`
- `dist/native/trama-native-stub`

## 5. Testes da fase 2

```bash
bash .local/tests/v2_0_fase2/run_local_v20_fase2.sh
```

## 6. Escopo pendente da fase 2

- backend 100% nativo para `executar .trm` e `compilar .trm` (sem ponte standalone);
- import nativo de módulo `.trm` com compilação local;
- async avançado com scheduler concorrente.

## 7. Exemplos práticos

Use a pasta:
- `exemplos/v20/`

Ela contém exemplos de linguagem, backend, banco, segurança, observabilidade e fluxo bytecode.
