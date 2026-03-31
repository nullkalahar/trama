# ABI da VM v1 (Contrato Formal de Execução)

Este documento define o contrato canônico da VM para `bytecode_v1`.

## 1. Modelo de execução

- VM stack-based;
- frame = (`ip`, `env`, `stack`, `handlers`);
- ambiente léxico encadeado para closures.

## 2. Contrato de frame

- `ip`: índice da próxima instrução;
- `env`: escopo local com referência ao escopo pai;
- `stack`: pilha de operandos e resultados;
- `handlers`: pilha de handlers de exceção (`tente/pegue/finalmente`).

## 3. Convenções operacionais

- `CALL` consome `callee` + `argc` argumentos da pilha;
- `RETURN_VALUE` retorna topo da pilha (ou `null` se vazia);
- `THROW` propaga exceção de usuário até handler ativo;
- sem handler ativo, exceção vira erro de runtime.

## 4. Opcodes v1 e comportamento esperado

### Controle e fluxo

- `HALT`: encerra execução do frame principal;
- `JUMP`: salto incondicional para `arg` (índice);
- `JUMP_IF_FALSE`: avalia topo da pilha e salta se falso;
- `RETURN_VALUE`: retorna valor do frame atual.

### Pilha e ambiente

- `LOAD_CONST`: empilha constante;
- `LOAD_NAME`: resolve símbolo no ambiente;
- `STORE_NAME`: grava símbolo no ambiente;
- `POP_TOP`: remove topo da pilha.

### Operações

- `NEGATE`
- `BINARY_ADD`, `BINARY_SUB`, `BINARY_MUL`, `BINARY_DIV`
- `COMPARE_OP`
- `BINARY_SUBSCR`

### Coleções

- `BUILD_LIST`
- `BUILD_MAP`

### Funções, chamadas e import

- `MAKE_FUNCTION`
- `CALL`
- `IMPORT_NAME`

### Exceções

- `THROW`
- `PUSH_TRY`
- `END_TRY_BLOCK`
- `END_CATCH_BLOCK`
- `BEGIN_FINALLY`
- `END_FINALLY`

### Assíncrono

- `AWAIT`

## 5. Async/await

- função assíncrona: `is_async=true`;
- chamada de função assíncrona retorna aguardável;
- `AWAIT` deve falhar explicitamente para valor não aguardável.

## 6. Import ABI

- `IMPORT_NAME` recebe referência de módulo (`.trm` ou resolução relativa);
- retorno esperado: mapa de símbolos exportados do módulo.

## 7. Erros canônicos de ABI

Implementações compatíveis devem emitir erro explícito para:

- opcode desconhecido;
- pilha insuficiente para opcode;
- aridade inválida em chamada;
- valor não aguardável em `AWAIT`;
- estrutura de `PUSH_TRY` inválida.

## 8. Limites e comportamento definido

- `BUILD_LIST` e `BUILD_MAP` devem validar contagem contra tamanho da pilha;
- índices inválidos em `BINARY_SUBSCR` devem resultar em exceção tratável;
- comparadores inválidos em `COMPARE_OP` devem falhar com erro explícito.

## 9. Paridade de implementação

Duas VMs são compatíveis com `vm_abi_v1` se, para o mesmo `.tbc` válido:

1. produzem mesmo resultado observável (saída e retorno),
2. preservam semântica de exceção,
3. aceitam mesma estrutura de bytecode v1.
