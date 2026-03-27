# Manual Completo da linguagem trama (até v0.4)

Este manual consolida, em um único documento, tudo que a linguagem `trama` suporta da `v0.1` até a `v0.4`.

## 1. Visão geral

A `trama` é uma linguagem em português (pt-BR), de uso geral, com:

- compilação para bytecode próprio
- execução em VM própria
- sintaxe simples e legível
- foco em evolução para backend

Pipeline:

`fonte (.trm)` -> `lexer` -> `parser` -> `AST` -> `semântica` -> `compilador` -> `bytecode` -> `VM`

## 2. Regra oficial de variações sem acentuação

A linguagem **normaliza palavras-chave**, então escreve-se com ou sem acento e o comportamento é o mesmo.

Exemplos equivalentes:

- `função` = `funcao`
- `senão` = `senao`
- `assíncrona` = `assincrona`

Também é case-insensitive para keywords:

- `FUNÇÃO`, `Funcao`, `Se`, `SENAO`, `ASSINCRONA`, etc.

## 3. Palavras-chave (até v0.4)

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
- `assíncrona`
- `aguarde`

## 4. Tipos de valor

- inteiro (`10`)
- real (`10.5`)
- texto (`"olá"`)
- lógico (`verdadeiro`, `falso`)
- nulo (`nulo`)
- lista (`[1, 2, 3]`)
- mapa/dicionário (`{"nome": "ana"}`)

## 5. Operadores e estruturas

### 5.1 Operadores

- aritméticos: `+`, `-`, `*`, `/`
- comparação: `==`, `!=`, `>`, `>=`, `<`, `<=`
- indexação: `alvo[indice]`

### 5.2 Comentários

- `# comentário`
- `// comentário`

### 5.3 Strings e escapes

Strings com aspas duplas:

- `\"`, `\\`, `\n`, `\t`, `\r`

### 5.4 Controle de fluxo

- `se/senão`
- `enquanto`
- `pare`
- `continue`

### 5.5 Funções

- declaração com `função`
- retorno com `retorne`
- funções aninhadas (closures)

### 5.6 Exceções

- `tente/pegue/finalmente`
- `lance`

### 5.7 Módulos

- `importe modulo como alias`
- `importe "caminho/mod.trm" como alias`

### 5.8 Assíncrono (v0.3+)

- `assíncrona função ...`
- `aguarde ...`
- tarefas e timeout na stdlib

## 6. Regras semânticas importantes

- `retorne` só dentro de função
- `pare` e `continue` só dentro de laço
- validação de aridade de funções
- `aguarde` só dentro de função assíncrona
- `tente` exige `pegue` e/ou `finalmente`

## 7. Biblioteca padrão (stdlib) até v0.4

### 7.1 Saída e log

- `exibir(...)`
- `log(nivel, mensagem)`
- `log_info(mensagem)`
- `log_erro(mensagem)`

### 7.2 JSON

- `json_parse(texto)`
- `json_parse_seguro(texto)` -> `{ok, erro, valor}`
- `json_stringify(valor)`
- `json_stringify_pretty(valor)`

### 7.3 Assíncrono e tarefas

- `dormir(segundos)`
- `criar_tarefa(awaitable)`
- `cancelar_tarefa(tarefa)`
- `com_timeout(awaitable, segundos)`

### 7.4 FS

- `ler_texto(caminho)`
- `escrever_texto(caminho, conteudo)`
- `arquivo_existe(caminho)`
- `listar_diretorio(caminho)`
- `ler_texto_async(caminho)`
- `escrever_texto_async(caminho, conteudo)`

### 7.5 HTTP client

- `http_get(url, headers?)`
- `http_post(url, body?, headers?)`

Retorno padrão:

- `status`
- `headers`
- `corpo`
- `json`

### 7.6 ENV e config

- `env_obter(nome, padrao?)`
- `env_todos(prefixo?)`
- `config_carregar(padrao, prefixo="TRAMA_")`

### 7.7 Tempo

- `agora_iso()`
- `timestamp()`

## 8. CLI

- `trama executar arquivo.trm`
- `trama bytecode arquivo.trm`
- `trama compilar arquivo.trm -o arquivo.tbc`
- `trama repl` (ainda não implementada)

## 9. Exemplo completo (até v0.4)

```trama
assíncrona função principal()
    cfg = config_carregar({"host": "127.0.0.1", "port": 8080}, "TRAMA_")
    log_info("iniciando")

    resp = aguarde http_get("https://httpbin.org/get")

    se resp["status"] == 200
        arquivo = "saida.json"
        aguarde escrever_texto_async(arquivo, json_stringify_pretty(resp["json"]))
        texto = aguarde ler_texto_async(arquivo)
        exibir(texto != nulo)
    senao
        log_erro("falha na requisição")
    fim
fim
```

## 10. Limitações atuais (ainda não concluídas)

Ainda não está pronto, até v0.4:

- servidor web nativo
- roteador/middlewares/CORS/request-response backend completo
- validação de payload padrão de framework
- healthcheck e serving de estáticos nativos de servidor
- banco de dados/ORM nativo

Esses pontos estão no roadmap a partir da `v0.5`.
