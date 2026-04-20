# Operacao v2.1.3 - Substituicao total JS/TS

## 1. Checklist de pre-deploy

- `pytest` verde no repositorio;
- suite v2.1.3 verde;
- artefatos de release gerados;
- checksum publicado;
- plano de rollback validado.

## 2. Build e empacotamento

```bash
scripts/build_native_stub.sh
scripts/build_standalone.sh
scripts/package_deb.sh 2.1.3 amd64
```

Opcional (pipeline unico):

```bash
scripts/build_release_nativo.sh 2.1.3 amd64
```

## 3. Instalacao local do .deb

```bash
sudo dpkg -i build/trama_2.1.3_amd64.deb
```

## 4. Validacao pos-instalacao

```bash
trama --diagnostico-runtime
trama
```

Validar coerencia de versao:

```bash
dpkg -s trama | rg '^Version:'
trama | head -n 1
```

## 5. Execucao da suite critica v2.1.3

```bash
trama testes-avancados-v213 \
  --perfil rapido \
  --saida-json .local/test-results/v213_relatorio_pos_install.json \
  --saida-md .local/test-results/v213_relatorio_pos_install.md \
  --json
```

## 6. Rollback padrao

1. remover versao atual:

```bash
sudo apt remove -y trama
```

2. reinstalar pacote anterior:

```bash
sudo dpkg -i trama_<VERSAO_ANTERIOR>_amd64.deb
```

3. validar runtime:

```bash
trama --diagnostico-runtime
```

## 7. Troubleshooting

### 7.1 Versao divergente entre pacote e binario

Sintoma:
- `dpkg -s trama` reporta uma versao;
- `trama` reporta outra.

Acao:
- rebuild com `scripts/build_native_stub.sh`;
- repacotar com `scripts/package_deb.sh <versao> amd64`;
- reinstalar e revalidar.

### 7.2 Diagnostico reporta backend inesperado

Acao:
- executar `trama --diagnostico-runtime`;
- confirmar valores esperados (`backend_runtime=nativo_c_vm`, `requer_python_host=nao`);
- se divergente, rebuild/reinstall.

### 7.3 Suite v2.1.3 falha em carga/caos

Acao:
- revisar `.local/test-results/v213_relatorio*.json`;
- isolar suite com perfil rapido;
- repetir em ambiente limpo para reproducao.
