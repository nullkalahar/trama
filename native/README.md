# Núcleo Nativo (v2.0)

Este diretório concentra a implementação nativa da Trama para eliminar Python no caminho do usuário final.

## Estado atual

- `runtime_stub.c`: stub nativo inicial com diagnóstico de backend.
- `trama_native.c`: VM/CLI nativa base com suporte a `executar-tbc`.
- build local via `scripts/build_native_stub.sh`.

## Objetivo final

Substituir gradualmente os caminhos Python por binário nativo que suporte:

1. `trama executar arquivo.trm`
2. `trama compilar arquivo.trm -o arquivo.tbc`
3. `trama executar-tbc arquivo.tbc`

sem Python instalado no host do usuário.

## Capacidades da VM nativa base (v2.0 inicial)

- `executar-tbc` sem Python no host.
- alias de compatibilidade: `run-tbc`.
- diagnóstico de runtime com campos canônicos pt-BR e compatibilidade.
- suporte síncrono de bytecode para:
  - funções e chamadas,
  - variáveis, aritmética e comparação,
  - saltos/controle de fluxo,
  - listas/mapas/indexação,
  - builtin `exibir`,
  - exceções (`THROW`, `PUSH_TRY`, `END_*`),
  - `AWAIT` (sequencial),
  - `IMPORT_NAME` para módulos `.tbc`.

- comandos `executar` e `compilar` disponíveis por ponte de compatibilidade via binário standalone (`trama`), sem invocar `python` diretamente.

Pendências conhecidas:

- backend de compilação/execução de `.trm` ainda não é 100% nativo (ponte standalone).
- import nativo de `.trm` (compilação on-the-fly) ainda pendente.
- async avançado (scheduler concorrente completo) ainda pendente.

## Fases técnicas

- Fase 1: especificação estável de bytecode/ABI.
- Fase 2: VM/CLI nativas.
- Fase 3: compilador oficial sem ponte Python no caminho do usuário.
- Fase 4: `.deb` e operação 100% nativos.
