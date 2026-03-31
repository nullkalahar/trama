# Matriz de Cobertura: Linguagem -> bytecode_v1 + ABI v1

Status de referência para conclusão da Fase 1 (v2.0).

## Legenda

- `suportado`: implementado e coberto na VM atual.
- `parcial`: existe suporte inicial, mas com limitações conhecidas.
- `fora do escopo v1`: planejado para versão posterior.

## Matriz

| Recurso da linguagem | Bytecode/ABI v1 | Status |
|---|---|---|
| Literais (`inteiro`, `real`, `texto`, `lógico`, `nulo`) | `LOAD_CONST` | suportado |
| Variáveis e atribuição | `LOAD_NAME`, `STORE_NAME` | suportado |
| Aritmética básica | `BINARY_ADD/SUB/MUL/DIV`, `NEGATE` | suportado |
| Comparação (`==`, `!=`, `>`, `>=`, `<`, `<=`) | `COMPARE_OP` | suportado |
| Controle de fluxo (`se/senão`) | `JUMP_IF_FALSE`, `JUMP` | suportado |
| Laços (`enquanto`) | `JUMP_IF_FALSE`, `JUMP` | suportado |
| `pare` / `continue` | patch de saltos em compilação | suportado |
| Funções | `MAKE_FUNCTION`, `CALL`, `RETURN_VALUE` | suportado |
| Closures léxicas | env encadeado na VM | suportado |
| Listas e mapas | `BUILD_LIST`, `BUILD_MAP` | suportado |
| Indexação | `BINARY_SUBSCR` | suportado |
| Import de módulos Trama | `IMPORT_NAME` | suportado |
| Exceções (`tente/pegue/finalmente`, `lance`) | `PUSH_TRY`, `THROW`, `END_*` | suportado |
| Assíncrono (`assíncrona`, `aguarde`) | `is_async`, `AWAIT` | suportado |
| Conformidade estrita de opcodes em loader | `validate_program_dict(validar_opcodes=True)` | suportado |
| Metadados canônicos (`formato`, `abi_vm`, `versao_serializacao`) | validação de `metadados` | suportado |
| Bytecode binário compacto (não JSON) | n/a em v1 | fora do escopo v1 |
| JIT/AOT nativo | n/a em v1 | fora do escopo v1 |
| Tipagem estática forte no bytecode | n/a em v1 | fora do escopo v1 |

## Limitações conhecidas (não bloqueiam Fase 1)

- metadados ainda opcionais para manter compatibilidade com `.tbc` já gerado;
- validação de opcode é modo explícito de conformidade (não forçada em todo caminho de execução);
- runtime nativo da fase 2 ainda em evolução para paridade total.
