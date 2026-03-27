# Linguagem trama v0.2

Este documento descreve exatamente o que a linguagem `trama` suporta na versão `0.2`.

## Regra de manutenção

A cada nova versão (`v0.3`, `v0.4`, ...), este documento deve ser atualizado e versionado junto com o código.

## Palavras-chave

Palavras-chave oficiais da `v0.2`:

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
- `tente`
- `pegue`
- `finalmente`
- `lance`
- `importe`
- `como`

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
- lista (`[1, 2, 3]`)
- mapa (`{"nome": "ana", "idade": 20}`)

## Operadores

Aritméticos:

- `+`, `-`, `*`, `/`

Comparação:

- `==`, `!=`, `>`, `>=`, `<`, `<=`

Indexação:

- `alvo[indice]`

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

### Função e closure

```trama
função principal()
    base = 10

    função soma_local(x)
        retorne x + base
    fim

    exibir(soma_local(5))
fim
```

### Condicional

```trama
se verdadeiro
    exibir("ok")
senao
    exibir("falha")
fim
```

### Laço

```trama
enquanto x < 10
    x = x + 1
    se x == 5
        pare
    fim
fim
```

### Exceções

```trama
tente
    lance "falhou"
pegue erro
    exibir("tratado:", erro)
finalmente
    exibir("sempre executa")
fim
```

### Módulos

```trama
importe util como u

função principal()
    exibir(u["dobro"](21))
fim
```

### Coleções

```trama
função principal()
    dados = {"nome": "ana", "nums": [1, 2, 3]}
    exibir(dados["nome"])
    exibir(dados["nums"][1])
fim
```

## Builtins disponíveis

- `exibir(...)`
- `json_parse(texto_json)`
- `json_stringify(valor)`

## Regras semânticas da v0.2

- `retorne` só pode ser usado dentro de função.
- `pare` e `continue` só podem ser usados dentro de laço.
- aridade de função é validada em tempo de compilação.
- funções aninhadas são suportadas.
- bloco `tente` exige `pegue` e/ou `finalmente`.

## CLI da v0.2

- `trama executar arquivo.trm`
- `trama bytecode arquivo.trm`
- `trama compilar arquivo.trm -o arquivo.tbc`

## Exemplo completo

```trama
importe mathx como m

função principal()
    tente
        dados = {"valor": m["dobro"](10), "ok": verdadeiro}
        txt = json_stringify(dados)
        obj = json_parse(txt)
        exibir(obj["valor"])
    pegue erro
        exibir("erro:", erro)
    finalmente
        exibir("fim")
    fim
fim
```
