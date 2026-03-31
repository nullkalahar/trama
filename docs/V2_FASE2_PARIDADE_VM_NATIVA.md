# v2.0 Fase 2 - Paridade VM/CLI Nativa (auditoria real)

Status: **em andamento**.

Este documento registra a paridade real entre a VM Python (`src/trama/vm.py`) e a VM nativa (`native/trama_native.c`), sem marcar falso concluído.

## Matriz por opcode (ABI v1)

| Opcode | Status nativo | Observação |
|---|---|---|
| `LOAD_CONST` | suportado | números, texto e nulo |
| `LOAD_NAME` | suportado | escopo léxico básico |
| `STORE_NAME` | suportado | gravação em escopo |
| `POP_TOP` | suportado | remove topo |
| `NEGATE` | suportado | somente número |
| `BINARY_ADD` | suportado | número+número e texto+texto |
| `BINARY_SUB` | suportado | número |
| `BINARY_MUL` | suportado | número |
| `BINARY_DIV` | suportado | número |
| `COMPARE_OP` | suportado | número e texto |
| `BINARY_SUBSCR` | suportado | lista/mapa |
| `BUILD_LIST` | suportado | contagem por pilha |
| `BUILD_MAP` | suportado | pares chave/valor |
| `JUMP` | suportado | salto absoluto |
| `JUMP_IF_FALSE` | suportado | truthy/falsy |
| `MAKE_FUNCTION` | suportado | closure base |
| `CALL` | suportado | função e builtin `exibir` |
| `RETURN_VALUE` | suportado | retorno de função |
| `HALT` | suportado | fim do frame |
| `THROW` | suportado | propagação de exceção em runtime |
| `PUSH_TRY` | suportado | handlers de `tente/pegue/finalmente` |
| `END_TRY_BLOCK` | suportado | fechamento de bloco `try` |
| `END_CATCH_BLOCK` | suportado | fechamento de bloco `catch` |
| `BEGIN_FINALLY` | suportado | início de `finally` |
| `END_FINALLY` | suportado | repropagação de exceção pendente |
| `IMPORT_NAME` | parcial | import nativo de módulos `.tbc` |
| `AWAIT` | parcial | await sequencial de função assíncrona |

## Matriz por recurso da linguagem

| Recurso | Status nativo | Observação |
|---|---|---|
| Variáveis e expressões básicas | suportado | caminho `executar-tbc` |
| Funções/closures | suportado | suporte base |
| Controle de fluxo (`se`, `enquanto`) | suportado | via `JUMP*` |
| Coleções (lista/mapa/indexação) | suportado | suporte base |
| Exceções (`tente/pegue/finalmente`) | suportado | fluxo de throw/catch/finally funcional |
| Import de módulos | parcial | suporta import de `.tbc` |
| Assíncrono (`assíncrona`/`aguarde`) | parcial | sem scheduler concorrente |
| `trama executar` nativo | parcial | usa ponte por binário standalone |
| `trama compilar` nativo | parcial | usa ponte por binário standalone |
| `trama executar-tbc` nativo | suportado | já funcional |

## Conclusão de auditoria da fase 2.A

- concluído: diagnóstico real de paridade documentado;
- não concluído: fase 2 como um todo (há lacunas obrigatórias abertas: import `.trm` direto, backend de compilação nativo e async avançado).
