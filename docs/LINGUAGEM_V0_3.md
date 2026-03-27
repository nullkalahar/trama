# Linguagem trama v0.3

Este documento descreve o que a linguagem `trama` suporta na versão `0.3`.

## Novidades da v0.3

- runtime assíncrono oficial na VM
- `assíncrona` e `aguarde` como forma pt-BR de `async/await`
- tarefas com timeout e cancelamento
- I/O não bloqueante de arquivo

## Palavras-chave novas

- `assíncrona` (`assincrona` e `async` equivalentes)
- `aguarde` (`await` equivalente)

As equivalências com/sem acento e case-insensitive continuam valendo.

## Sintaxe assíncrona

### Função assíncrona

```trama
assíncrona função buscar()
    aguarde dormir(0.1)
    retorne 42
fim
```

### Aguardar resultado

```trama
assíncrona função principal()
    valor = aguarde buscar()
    exibir(valor)
fim
```

## Builtins assíncronas e de tarefas

- `dormir(segundos)`
- `criar_tarefa(awaitable)`
- `cancelar_tarefa(tarefa)`
- `com_timeout(awaitable, segundos)`
- `ler_texto_async(caminho)`
- `escrever_texto_async(caminho, conteudo)`

## Exemplo de tarefas

```trama
assíncrona função trabalho()
    aguarde dormir(0.05)
    retorne "ok"
fim

assíncrona função principal()
    t = criar_tarefa(trabalho())
    valor = aguarde com_timeout(t, 1.0)
    exibir(valor)
fim
```

## Exemplo de I/O não bloqueante

```trama
assíncrona função principal()
    aguarde escrever_texto_async("saida.txt", "olá")
    texto = aguarde ler_texto_async("saida.txt")
    exibir(texto)
fim
```

## Compatibilidade

Tudo da `v0.2` continua disponível:

- exceções (`tente/pegue/finalmente`, `lance`)
- módulos (`importe`)
- closures/escopo léxico
- coleções e JSON
