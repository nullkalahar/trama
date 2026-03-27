# Linguagem trama v0.5

A `v0.5` entrega o núcleo web nativo da linguagem.

## Objetivo da versão

Permitir criar APIs e serviços HTTP com recursos mínimos de backend direto em `trama`.

## Recursos novos

- servidor web nativo
- rotas por método e caminho
- middlewares (`request_id`, `log_requisicao`)
- CORS configurável
- request/response JSON padrão
- validação de payload em rotas de eco
- erros padronizados com código/mensagem/detalhes
- healthcheck
- serving de arquivos estáticos

## API web da stdlib

- `web_criar_app()`
- `web_adicionar_rota_json(app, metodo, caminho, corpo, status?)`
- `web_adicionar_rota_echo_json(app, metodo, caminho, campos_obrigatorios?)`
- `web_usar_middleware(app, nome)`
- `web_configurar_cors(app, origem?, metodos?, headers?)`
- `web_ativar_healthcheck(app, caminho?)`
- `web_servir_estaticos(app, prefixo, diretorio)`
- `web_iniciar(app, host?, porta?)`
- `web_parar(handle)`

## Formato de erros padronizados

```json
{
  "ok": false,
  "erro": {
    "codigo": "VALIDACAO_FALHOU",
    "mensagem": "Campos obrigatórios ausentes.",
    "detalhes": {"faltando": ["nome"]}
  }
}
```

## Rotas prontas na infraestrutura

- healthcheck: caminho configurável (default `/health`)
- estáticos: prefixo configurável (ex.: `/static`)

## Exemplo completo

```trama
assíncrona função principal()
    app = web_criar_app()

    web_adicionar_rota_json(app, "GET", "/ola", {"mensagem": "ok"}, 200)
    web_adicionar_rota_echo_json(app, "POST", "/echo", ["nome"])

    web_usar_middleware(app, "request_id")
    web_usar_middleware(app, "log_requisicao")
    web_configurar_cors(app, "*")

    web_ativar_healthcheck(app, "/healthz")
    web_servir_estaticos(app, "/static", "./public")

    servidor = aguarde web_iniciar(app, "127.0.0.1", 8080)
    exibir("rodando em:", servidor["base_url"])

    aguarde dormir(2)
    aguarde web_parar(servidor)
fim
```
