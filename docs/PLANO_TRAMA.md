# Plano de Criação e Implementação da Linguagem `trama`

## 1. Visão do Projeto

A `trama` será uma linguagem de propósito geral, com sintaxe em português (pt-BR), tipagem simples no estilo Python (dinâmica e prática), e foco em boa ergonomia para backend.

Pipeline de execução:

`fonte (.trm)` -> `lexer` -> `parser` -> `AST` -> `análise semântica` -> `compilador` -> `bytecode` -> `VM` -> `execução`

## 2. Decisões de Design (v0.1)

- **Nome da linguagem:** `trama`
- **Paradigma inicial:** imperativo com funções
- **Tipagem:** simples/dinâmica (estilo Python)
- **Objetivo inicial:** linguagem geral com bom uso em backend
- **Implementação inicial:** Python (compilador + VM)

## 3. Sintaxe Base

Estilo legível entre Python/Pascal, com fechamento explícito por `fim`.

Exemplo:

```trama
função principal()
    nome = "Lucas"
    exibir("Olá, " + nome)
fim
```

## 4. Palavras-chave Oficiais (MVP)

- `função`
- `retorne`
- `se`
- `senão`
- `enquanto`
- `para`
- `em`
- `verdadeiro`
- `falso`
- `nulo`
- `fim`
- `pare`
- `continue`

### 4.1 Equivalência de acentuação (regra oficial)

A `trama` aceitará palavras-chave com ou sem acento como equivalentes.

Exemplos:

- `função` == `funcao`
- `senão` == `senao`

Estratégia do lexer:

- normalizar lexemas para minúsculas sem diacríticos na identificação de palavras-chave;
- preservar o lexema original para mensagens de erro e debug.

## 5. Escopo da Versão 0.1

Suportar apenas:

- variáveis
- números
- textos
- operações matemáticas
- comparações
- `se/senão`
- `enquanto`
- funções
- chamada de função
- builtin `exibir`
- CLI funcional (`trama executar`, `trama bytecode`, `trama compilar`)
- pacote Python instalável
- binário standalone obrigatório (sem dependência de Python no alvo)
- pacote Debian (`.deb`) instalável localmente
- publicação em repositório APT assinado para permitir `apt install trama`

Fora do escopo inicial:

- classes
- módulos avançados
- concorrência
- exceções avançadas
- sistema de tipos estático

## 6. Gramática Mínima (Referência)

```ebnf
programa       -> declaracao*
declaracao     -> funcao_decl | variavel_decl | comando
funcao_decl    -> "função" IDENT "(" parametros? ")" bloco "fim"
variavel_decl  -> IDENT "=" expressao
comando        -> se_decl | enquanto_decl | expr_decl | retorno_decl
se_decl        -> "se" expressao bloco ("senão" bloco)? "fim"
enquanto_decl  -> "enquanto" expressao bloco "fim"
retorno_decl   -> "retorne" expressao?
bloco          -> declaracao*
expressao      -> igualdade
```

> Observação: como a tipagem será simples, a declaração com `:` e tipo explícito fica para versão futura.

## 7. Arquitetura de Implementação

## 7.1 Lexer

Responsável por transformar texto em tokens.

Tokens iniciais:

- `IDENT`
- `NUMERO`
- `TEXTO`
- `FUNCAO`, `RETORNE`, `SE`, `SENAO`, `ENQUANTO`, `PARA`, `EM`, `FIM`
- `VERDADEIRO`, `FALSO`, `NULO`, `PARE`, `CONTINUE`
- `ABRE_PAREN`, `FECHA_PAREN`, `VIRGULA`
- `IGUAL`, `MAIS`, `MENOS`, `ASTERISCO`, `BARRA`
- `IGUAL_IGUAL`, `DIFERENTE`, `MAIOR`, `MENOR`, `MAIOR_IGUAL`, `MENOR_IGUAL`
- `NOVA_LINHA`, `EOF`

Regras iniciais:

- ignorar espaços/tabs
- suportar comentários (ex.: `# comentário`)
- preservar linha/coluna para mensagens de erro

## 7.2 Parser

Construção da AST com parser recursivo descendente.

Nós de AST (MVP):

- `Programa`
- `FuncaoDecl`
- `VarAssign`
- `IfStmt`
- `WhileStmt`
- `ReturnStmt`
- `ExprStmt`
- `CallExpr`
- `BinaryExpr`
- `UnaryExpr`
- `Literal`
- `Identifier`

## 7.3 Análise Semântica

Checagens mínimas:

- uso de variável não declarada (se adotado escopo explícito)
- `retorne` fora de função
- aridade de função em chamadas
- validações básicas de controle de fluxo (`pare/continue` dentro de laço)

## 7.4 Bytecode

Formato inicial simples (lista de instruções).

Instruções sugeridas:

- `LOAD_CONST idx`
- `LOAD_NAME nome`
- `STORE_NAME nome`
- `BINARY_ADD`, `BINARY_SUB`, `BINARY_MUL`, `BINARY_DIV`
- `COMPARE_OP op`
- `JUMP alvo`
- `JUMP_IF_FALSE alvo`
- `CALL argc`
- `RETURN_VALUE`
- `POP_TOP`
- `HALT`

## 7.5 Máquina Virtual (VM)

Componentes:

- pilha de operandos
- tabela de variáveis (ambiente)
- tabela de funções
- contador de programa (`ip`)

Recursos do runtime:

- builtin `exibir`
- valores dinâmicos (`int`, `float`, `str`, `bool`, `None`)
- mensagem de erro com linha/trecho

## 8. Estrutura de Pastas Recomendada

```text
trama/
  docs/
  src/
    trama/
      __init__.py
      token.py
      lexer.py
      ast_nodes.py
      parser.py
      semantic.py
      bytecode.py
      compiler.py
      vm.py
      builtins.py
      cli.py
  tests/
    test_lexer.py
    test_parser.py
    test_semantic.py
    test_vm.py
  examples/
    ola_mundo.trm
    condicional.trm
    funcoes.trm
  pyproject.toml
  README.md
```

## 9. CLI Inicial

Comandos sugeridos:

- `trama executar arquivo.trm`
- `trama compilar arquivo.trm -o arquivo.tbc`
- `trama bytecode arquivo.trm` (mostra instruções)
- `trama repl` (fase 2)

## 10. Roadmap de Entregas

## Marco 1 - Núcleo Léxico/Sintático

- lexer funcional
- parser funcional
- AST serializável para debug
- testes básicos de parsing

## Marco 2 - Execução Básica

- compilador AST -> bytecode
- VM com expressões, variáveis e `exibir`
- suporte a `se/senão` e `enquanto`

## Marco 3 - Funções

- declaração/chamada de função
- `retorne`
- escopo local simples

## Marco 4 - Backend-Ready Inicial

- organização de módulos simples (importação local)
- libs padrão mínimas (texto, tempo, arquivo)
- melhoria de erros e observabilidade

## Marco 5 - Empacotamento e Distribuição v0.1

- empacotamento Python para instalação local
- geração de binário standalone obrigatório
- geração de pacote Debian (`.deb`)
- criação/publicação de repositório APT com assinatura GPG
- instalação de validação com `apt install trama`

## 11. Estratégia de Testes

- **Lexer:** snapshots de tokens por arquivo de entrada
- **Parser:** snapshots de AST
- **VM:** testes de saída e estado final
- **Integração:** executar `.trm` reais em `examples/`

Casos obrigatórios:

- precedência correta (`1 + 2 * 3`)
- curto-circuito em booleanos (quando implementado)
- `retorne` em caminhos condicionais
- laço com `pare` e `continue`

## 12. Exemplo Inicial da Linguagem

```trama
função soma(a, b)
    retorne a + b
fim

função principal()
    nome = "trama"
    resultado = soma(10, 20)

    se resultado >= 30
        exibir("ok: " + nome)
    senão
        exibir("falhou")
    fim
fim
```

## 13. Próximos Passos Imediatos

1. Criar esqueleto de pastas (`src/trama`, `tests`, `examples`).
2. Implementar `token.py` e `lexer.py`.
3. Escrever testes de lexer primeiro.
4. Implementar parser com AST mínima.
5. Fechar ciclo completo com um programa simples compilando e rodando na VM.

---

Este documento define a base da `trama` para evoluir de MVP para uma linguagem geral com foco real em backend, sem perder simplicidade na curva inicial.
