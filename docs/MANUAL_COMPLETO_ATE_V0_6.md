# Manual Completo da linguagem trama (até v0.6)

Este manual consolida o estado real da linguagem `trama` da `v0.1` até a `v0.6`.
O foco é documentar exatamente o que já funciona hoje.

## 1. Visão geral

- paradigma: linguagem geral com foco em simplicidade para backend
- execução: código `.trm` -> compilador -> bytecode -> VM
- CLI principal: `trama executar`, `trama bytecode`, `trama compilar`

## 2. Regras de escrita (pt-BR com variações)

A `trama` normaliza palavras-chave para minúsculas sem acento.

Isso significa:

- `função` = `funcao`
- `senão` = `senao`
- `assíncrona` = `assincrona` = `async`
- `aguarde` = `await`

Keywords também são case-insensitive:

- `FUNÇÃO`, `Funcao`, `Se`, `SENAO`, `ASSINCRONA` etc.

## 3. Palavras-chave oficiais (até v0.6)

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
- `tente`
- `pegue`
- `finalmente`
- `lance`
- `importe`
- `como`
- `assíncrona`
- `aguarde`

## 4. Tipos e literais

- número inteiro: `10`
- número real: `10.5`
- texto: `"olá"`
- lógico: `verdadeiro`, `falso`
- nulo: `nulo`
- lista: `[1, 2, 3]`
- mapa: `{"nome": "Ana", "idade": 20}`

## 5. Operadores suportados

- aritméticos: `+`, `-`, `*`, `/`
- comparação: `==`, `!=`, `>`, `>=`, `<`, `<=`
- unário: `-valor`
- indexação: `lista[0]`, `mapa["chave"]`

## 6. Sintaxe base

### 6.1 Atribuição

```trm
nome = "Lia"
idade = 21
```

### 6.2 Condicional

```trm
se idade >= 18
    exibir("maior")
senao
    exibir("menor")
fim
```

### 6.3 Laço `enquanto`

```trm
i = 0
enquanto i < 3
    exibir(i)
    i = i + 1
fim
```

### 6.4 Controle de laço

```trm
enquanto verdadeiro
    pare
fim
```

### 6.5 Funções

```trm
função soma(a, b)
    retorne a + b
fim
```

### 6.6 Funções assíncronas

```trm
assíncrona função esperar_um_pouco()
    aguarde dormir(0.1)
    retorne "ok"
fim
```

### 6.7 Imports

```trm
importe "utils.trm" como utils
```

Também aceita:

```trm
importe utils como u
```

### 6.8 Exceções

```trm
tente
    lance "falha"
pegue erro
    exibir("capturado:", erro)
finalmente
    exibir("encerrando")
fim
```

## 7. Regras semânticas importantes

- `retorne` só pode ser usado dentro de função
- `aguarde` só pode ser usado dentro de função assíncrona
- aridade de função é validada
- erros mostram contexto de arquivo/linha/coluna quando disponível

## 8. Biblioteca padrão (stdlib)

## 8.1 Saída e logs

- `exibir(*args)`
- `log(nivel, mensagem)`
- `log_info(mensagem)`
- `log_erro(mensagem)`

## 8.2 JSON

- `json_parse(texto)`
- `json_parse_seguro(texto)` -> `{ok, erro, valor}`
- `json_stringify(valor)`
- `json_stringify_pretty(valor)`

## 8.3 Async e tarefas

- `criar_tarefa(awaitable)`
- `cancelar_tarefa(task)`
- `dormir(segundos)` (async)
- `com_timeout(awaitable, segundos)` (async)

## 8.4 Arquivos

- `ler_texto(caminho)`
- `escrever_texto(caminho, conteudo)`
- `arquivo_existe(caminho)`
- `listar_diretorio(caminho)`
- `ler_texto_async(caminho)` (async)
- `escrever_texto_async(caminho, conteudo)` (async)

## 8.5 HTTP client, ambiente e tempo

- `http_get(url, headers?)` (async)
- `http_post(url, body?, headers?)` (async)
- `env_obter(nome, padrao?)`
- `env_todos(prefixo?)`
- `config_carregar(padrao, prefixo?)`
- `agora_iso()`
- `timestamp()`

## 8.6 Web server (v0.5)

- `web_criar_app()`
- `web_adicionar_rota_json(app, metodo, caminho, corpo, status?)`
- `web_adicionar_rota_echo_json(app, metodo, caminho, campos_obrigatorios?)`
- `web_usar_middleware(app, nome)` (`log_requisicao`, `request_id`)
- `web_configurar_cors(app, origem?, metodos?, headers?)`
- `web_ativar_healthcheck(app, caminho?)`
- `web_servir_estaticos(app, prefixo, diretorio)`
- `web_iniciar(app, host?, porta?)` (async)
- `web_parar(handle)` (async)

## 8.7 Banco de dados (v0.6)

### Conexão e DSN

- SQLite: `sqlite:///caminho/arquivo.db`
- PostgreSQL nativo: `postgres://...` ou `postgresql://...` via `asyncpg`

Instalação recomendada para desenvolvimento com PostgreSQL:

```bash
pip install -e .[dev,db]
```

### API de banco (técnica)

- `pg_conectar(dsn)` (async)
- `pg_fechar(conn)` (async)
- `pg_executar(conn, sql, params?)` (async)
- `pg_consultar(conn, sql, params?)` (async)
- `pg_transacao_iniciar(conn)` (async)
- `pg_transacao_commit(tx)` (async)
- `pg_transacao_rollback(tx)` (async)
- `pg_tx_executar(tx, sql, params?)` (async)
- `pg_tx_consultar(tx, sql, params?)` (async)

### API oficial pt-BR (equivalente)

- `banco_conectar`, `banco_fechar`, `banco_executar`, `banco_consultar`
- `transacao_iniciar`, `transacao_confirmar`, `transacao_cancelar`
- `transacao_executar`, `transacao_consultar`

### Query builder

- `qb_select(tabela, colunas?)`
- `qb_where_eq(query, campo, valor)`
- `qb_order_by(query, campo, direcao?)`
- `qb_limite(query, limite)`
- `qb_sql(query)`
- `qb_consultar(conn, query)` (async)

Aliases pt-BR:

- `consulta_selecionar`, `consulta_onde_igual`, `consulta_ordenar_por`
- `consulta_limite`, `consulta_sql`, `consulta_executar`

### ORM inicial

- `orm_inserir(conn, tabela, dados)` (async)
- `orm_atualizar(conn, tabela, dados, where)` (async)
- `orm_buscar_por_id(conn, tabela, id)` (async)

Aliases pt-BR:

- `modelo_inserir`, `modelo_atualizar`, `modelo_buscar_por_id`

### Migração e seed idempotentes

- `migracao_aplicar(conn, nome, sql)` (async)
- `seed_aplicar(conn, nome, sql)` (async)
- alias pt-BR: `semente_aplicar`

### Observação sobre placeholders SQL

Você pode escrever SQL com `?` como placeholder:

```trm
aguarde banco_executar(conn, "INSERT INTO usuarios (nome) VALUES (?)", ["Ana"])
```

No PostgreSQL, a runtime converte internamente para `$1`, `$2`, etc.

## 9. Exemplo completo (backend com banco)

```trm
assíncrona função principal()
    conn = aguarde banco_conectar("postgresql://usuario:senha@localhost:5432/app")

    aguarde migracao_aplicar(
        conn,
        "001_usuarios",
        "CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nome TEXT NOT NULL);"
    )

    id = aguarde modelo_inserir(conn, "usuarios", {"nome": "Bia"})
    exibir("novo id:", id)

    q = consulta_selecionar("usuarios", ["id", "nome"])
    q = consulta_onde_igual(q, "id", id)
    dados = aguarde consulta_executar(conn, q)
    exibir(json_stringify_pretty(dados))

    tx = aguarde transacao_iniciar(conn)
    aguarde transacao_executar(tx, "UPDATE usuarios SET nome = ? WHERE id = ?", ["Bia Lima", id])
    aguarde transacao_confirmar(tx)

    aguarde banco_fechar(conn)
fim
```

## 10. CLI

Executar programa:

```bash
trama executar arquivo.trm
```

Ver bytecode:

```bash
trama bytecode arquivo.trm
```

Compilar para `.tbc`:

```bash
trama compilar arquivo.trm -o programa.tbc
```

REPL:

- comando existe, mas ainda não implementado

## 11. Limitações atuais (até v0.6)

- sem classes
- sem sistema de tipos estático
- sem gerenciador de pacotes da linguagem
- sem compilador escrito em `trama` (bootstrap ainda no roadmap)
- sem runtime frontend (planejado para v1.5+)

## 12. Política de atualização do manual

Este manual é obrigatório e deve ser atualizado a cada release.
Regra de versão:

- nova funcionalidade em release `vX.Y` exige atualização deste documento
- exemplos devem refletir a sintaxe/stdlib real implementada
