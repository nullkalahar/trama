# BYTECODE_V1 (Especificação Formal Canônica)

Status: **congelado para compatibilidade v1**.

Este documento define o contrato formal de serialização `.tbc` da Trama para execução pela VM.

## 1. Encoding e envelope

- formato de arquivo: JSON UTF-8;
- objeto raiz obrigatório com:
  - `entry: FunctionCode`
  - `functions: object<string, FunctionCode>`
- campo opcional de controle:
  - `metadados: BytecodeMetadadosV1`

Exemplo mínimo válido:

```json
{
  "entry": {
    "name": "__entry__",
    "params": [],
    "is_async": false,
    "instructions": [
      { "op": "HALT", "arg": null }
    ]
  },
  "functions": {}
}
```

Exemplo com metadados canônicos v1:

```json
{
  "metadados": {
    "formato": "bytecode_v1",
    "abi_vm": "vm_abi_v1",
    "versao_serializacao": 1
  },
  "entry": {
    "name": "__entry__",
    "params": [],
    "is_async": false,
    "instructions": [
      { "op": "HALT", "arg": null }
    ]
  },
  "functions": {}
}
```

## 2. Schema lógico

### `BytecodeMetadadosV1` (opcional para transição, recomendado para validação estrita)

- `formato: "bytecode_v1"`
- `abi_vm: "vm_abi_v1"`
- `versao_serializacao: 1`

### `FunctionCode`

Campos obrigatórios:

- `name: string`
- `params: string[]`
- `is_async: boolean`
- `instructions: Instruction[]`

Observações:

- `name` é nome lógico da função (debug/observabilidade);
- chave do mapa `functions` representa `code_name` interno estável na compilação.

### `Instruction`

Campos obrigatórios:

- `op: string`
- `arg: any | null`

Contrato:

- bytecode é stack-based;
- semântica de cada opcode está em [`docs/ABI_VM_V1.md`](ABI_VM_V1.md).

## 3. Regras de serialização/deserialização

1. `program_to_dict` produz envelope com `entry` e `functions`.
2. `program_from_dict` deve conseguir reconstruir programa válido.
3. roundtrip JSON canônico:
   - `program_to_dict(program_from_dict(payload)) == payload_normalizado`
4. payload malformado deve falhar com erro explícito de validação.

## 4. Versionamento e compatibilidade

Regras obrigatórias v1:

1. Campos obrigatórios do envelope e de `FunctionCode` são estáveis.
2. Semântica dos opcodes v1 não muda de forma incompatível.
3. Novos opcodes só entram sem quebrar programas v1.
4. `bytecode_v2` só pode ser introduzido em documento separado.
5. Implementações devem emitir erro explícito para opcode não suportado.

## 5. Validação formal na implementação

A implementação oficial expõe validação via `validate_program_dict`:

- valida estrutura do envelope;
- valida campos obrigatórios de função/instrução;
- valida metadados quando presentes;
- valida opcodes (`validar_opcodes=True`) para conformidade estrita.

## 6. Cobertura de recursos

Matriz formal de cobertura:

- [`docs/MATRIZ_COBERTURA_BYTECODE_ABI_V1.md`](MATRIZ_COBERTURA_BYTECODE_ABI_V1.md)
