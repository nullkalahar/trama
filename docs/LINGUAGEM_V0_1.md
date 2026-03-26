# Linguagem trama v0.1

Este documento descreve exatamente o que a linguagem `trama` suporta na versão `0.1`.

## Regra de manutenção

A cada nova versão (`v0.2`, `v0.3`, ...), este documento deve ser atualizado e versionado junto com o código.

Padrão recomendado:

- manter este arquivo como referência da `v0.1`;
- criar `docs/LINGUAGEM_V0_2.md`, `docs/LINGUAGEM_V0_3.md`, etc., para as versões seguintes;
- atualizar o `README.md` apontando para a documentação da versão mais recente.

## Palavras-chave

Palavras-chave oficiais da `v0.1`:

- `função`
- `retorne`
- `se`
- `senão`
- `enquanto`
- `para` (reservada)
- `em` (reservada)
- `verdadeiro`
- `falso`
- `nulo`
- `fim`
- `pare`
- `continue`

## Equivalência de acentuação

A linguagem aceita palavras-chave com e sem acento como equivalentes.

Exemplos válidos e equivalentes:

- `função` == `funcao`
- `senão` == `senao`

As keywords também são case-insensitive (ex.: `FUNÇÃO`, `Se`, `SENAO`).

## Tipos de valor

- número inteiro (`10`)
- número real (`10.5`)
- texto (`"olá"`)
- lógico (`verdadeiro`, `falso`)
- nulo (`nulo`)

## Operadores

Aritméticos:

- `+`, `-`, `*`, `/`

Comparação:

- `==`, `!=`, `>`, `>=`, `<`, `<=`

## Comentários

Comentários de linha:

- `# comentário`
- `// comentário`

## Strings

Strings usam aspas duplas (`"..."`) e suportam escapes:

- `\"`
- `\\`
- `\n`
- `\t`
- `\r`

## Estruturas suportadas

## Função

```trama
função soma(a, b)
    retorne a + b
fim
```

## Condicional

```trama
se verdadeiro
    exibir("ok")
senao
    exibir("falha")
fim
```

## Laço

```trama
enquanto x < 10
    x = x + 1
    se x == 5
        pare
    fim
fim
```

## Chamada de função

```trama
resultado = soma(10, 20)
exibir(resultado)
```

## Builtins disponíveis

- `exibir(...)`

## Regras semânticas da v0.1

- `retorne` só pode ser usado dentro de função;
- `pare` e `continue` só podem ser usados dentro de laço;
- aridade de função é validada em tempo de compilação;
- funções aninhadas ainda não são suportadas na `v0.1`.

## O que ainda não pode na v0.1

- classes
- módulos/imports
- exceções avançadas
- concorrência
- sistema de tipos estático

## CLI da v0.1

- `trama executar arquivo.trm`
- `trama bytecode arquivo.trm`
- `trama compilar arquivo.trm -o arquivo.tbc`

## Exemplo completo

```trama
função soma(a, b)
    retorne a + b
fim

função principal()
    valor = soma(10, 20)

    se valor >= 30
        exibir("resultado:", valor)
    senao
        exibir("erro")
    fim
fim
```
