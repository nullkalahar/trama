# Núcleo Nativo (v2.0)

Este diretório concentra a implementação nativa da Trama para eliminar Python no caminho do usuário final.

## Estado atual

- `runtime_stub.c`: stub nativo inicial com diagnóstico de backend.
- `trama_native.c`: VM/CLI nativa base com suporte a `executar-tbc`.
- build local via `scripts/build_native_stub.sh`.
- o entrypoint Python (`python -m trama.cli` ou instalação editável de desenvolvimento) continua existindo para desenvolvimento e diagnóstico legado.
- o binário nativo de distribuição é `dist/native/trama-native`.

## Objetivo final

Substituir gradualmente os caminhos Python por binário nativo que suporte:

1. `trama executar arquivo.trm`
2. `trama compilar arquivo.trm -o arquivo.tbc`
3. `trama executar-tbc arquivo.tbc`

sem Python instalado no host do usuário.

## Capacidades da VM nativa

- `executar-tbc` sem Python no host.
- `executar arquivo.trm` por compilação nativa para bytecode temporário.
- `compilar arquivo.trm -o arquivo.tbc` pelo compilador nativo.
- alias de compatibilidade: `run-tbc`.
- diagnóstico de runtime com campos canônicos pt-BR e compatibilidade.
- suporte síncrono de bytecode para:
  - funções e chamadas,
  - variáveis, aritmética e comparação,
  - saltos/controle de fluxo,
  - listas/mapas/indexação,
  - builtin `exibir`,
  - exceções (`THROW`, `PUSH_TRY`, `END_*`),
  - `AWAIT`, criação/cancelamento de tarefas e timeout básico,
  - `IMPORT_NAME` para módulos `.tbc`.

Pendências conhecidas:

- o stub `dist/native/trama-native-stub` existe apenas como artefato histórico/de diagnóstico mínimo.
- a CLI Python de desenvolvimento reporta `backend_runtime=python_legado` e `requer_python_host=sim`.
- novas capacidades de runtime devem ser validadas no binário `dist/native/trama-native` antes de serem documentadas como 100% nativas.

## Fases técnicas

- Fase 1: especificação estável de bytecode/ABI.
- Fase 2: VM/CLI nativas.
- Fase 3: compilador oficial sem ponte Python no caminho do usuário.
- Fase 4: `.deb` e operação 100% nativos.
