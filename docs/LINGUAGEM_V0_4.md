# Linguagem trama v0.4

Este documento resume o que foi adicionado na `v0.4`.

## Objetivo da versão

Fechar a base de stdlib backend mínima para preparar o servidor nativo da `v0.5`.

## Novos recursos da stdlib

### HTTP client

- `http_get(url, headers?)`
- `http_post(url, body?, headers?)`

Retorno padrão:

- `status` (inteiro)
- `headers` (mapa)
- `corpo` (texto)
- `json` (valor parseado ou `nulo`)

Uso:

```trama
assíncrona função principal()
    resp = aguarde http_get("https://api.exemplo.com/health")
    exibir(resp["status"])
fim
```

### FS (arquivo/diretório)

- `ler_texto(caminho)`
- `escrever_texto(caminho, conteudo)`
- `arquivo_existe(caminho)`
- `listar_diretorio(caminho)`

Além das versões assíncronas já existentes:

- `ler_texto_async(caminho)`
- `escrever_texto_async(caminho, conteudo)`

### ENV e configuração por ambiente

- `env_obter(nome, padrao?)`
- `env_todos(prefixo?)`
- `config_carregar(padrao, prefixo="TRAMA_")`

`config_carregar` aplica override com variáveis de ambiente que começam com o prefixo.

Exemplo:

- `TRAMA_PORT=8080` sobrescreve `config["port"]`

### TIME

- `agora_iso()`
- `timestamp()`

### LOG

- `log(nivel, mensagem)`
- `log_info(mensagem)`
- `log_erro(mensagem)`

Formato padrão de saída:

`[timestamp] [NIVEL] mensagem`

## JSON robusto

- `json_parse_seguro(texto)` -> retorna mapa `{ok, erro, valor}`
- `json_stringify_pretty(valor)` -> JSON formatado com indentação e ordenação de chaves

## Compatibilidade

Tudo da `v0.3` continua suportado, incluindo:

- `assíncrona/aguarde`
- tarefas (`criar_tarefa`, `cancelar_tarefa`, `com_timeout`)
- exceções, módulos, closures e coleções
