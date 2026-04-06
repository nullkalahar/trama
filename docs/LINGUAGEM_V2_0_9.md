# Trama v2.0.9 - Runtime 100% nativo (fechamento do ciclo)

A v2.0.9 fecha o ciclo de autossuficiencia no caminho critico de execucao/compilacao com backend nativo em C.

## Objetivo

Eliminar dependencias externas no fluxo principal de runtime/compilacao e consolidar paridade funcional no backend nativo.

## Entregas tecnicas

1. Comandos nativos sem ponte no caminho critico
- `trama-native executar`
- `trama-native compilar`
- `trama-native executar-tbc`
- aliases de compatibilidade mantidos: `run`, `build`, `run-tbc`

2. Compilador nativo `.trm -> .tbc`
- pipeline nativo com parser/compilador oficial para fonte `.trm`
- geracao de bytecode JSON compativel com contrato `bytecode_v1`
- validacao de formato no carregamento do `.tbc`

3. Import nativo de modulo `.trm`
- `importe "mod.trm" como m` com resolucao deterministica por caminho
- autocompilacao nativa de modulo importado quando `mod.tbc` nao existir

4. Async avancado com concorrencia
- tarefas concorrentes por thread (`criar_tarefa`)
- `aguarde` em tarefa/awaitable com timeout (`com_timeout`)
- cancelamento cooperativo (`cancelar_tarefa`)
- espera nao bloqueante simples (`dormir`)

5. Melhorias de VM nativa
- dispatch estavel para await/tarefa
- cache de funcoes importadas por modulo em runtime
- reducao de ponte no fluxo principal e diagnostico explicito de backend

6. Build/release nativo
- build nativo oficial com `pthread` e `libm`
- empacotamento `.deb` priorizando binario nativo
- script consolidado de release nativo (`scripts/build_release_nativo.sh`)

## API canonica pt-BR e compatibilidade

Forma oficial:
- `criar_tarefa`
- `com_timeout`
- `cancelar_tarefa`
- `dormir`

Aliases de compatibilidade:
- `create_task`
- `with_timeout`
- `cancel_task`
- `sleep`

## Diagnostico oficial

`trama-native --diagnostico-runtime` agora reporta:
- `backend_runtime=nativo_c_vm`
- `backend_compilador=nativo_c_compilador`
- `requer_python_host=nao`

## Testes obrigatorios cobertos

- unitario/integracao do runtime nativo:
  - `tests/test_native_runtime_v20.py`
  - `tests/test_native_runtime_v209.py`
- cobertura de v2.0.9:
  - compilar e executar `.trm` sem ponte
  - import nativo de modulo `.trm` com autocompilacao para `.tbc`
  - concorrencia async (tarefas, timeout, cancelamento)
  - diagnostico 100% nativo

## DoD v2.0.9 atendido

- uso da linguagem sem runtime externo no caminho critico: atendido no binario nativo (`executar`, `compilar`, `executar-tbc`).
- paridade funcional consolidada no backend nativo: atendida no escopo oficial v2.0.9 com testes automatizados.
