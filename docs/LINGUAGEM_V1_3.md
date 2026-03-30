# Linguagem Trama v1.3

## Objetivo

Entregar camada de tempo real robusta para backend em pt-BR canônico:

- WebSocket nativo com autenticação JWT;
- salas/canais com presença;
- eventos de `typing` e `read_receipt`;
- broadcast seletivo (canal/sala/usuário/conexão);
- fallback de transporte via HTTP;
- limites e proteção operacional.

## API canônica pt-BR

Principais builtins:

- `web_tempo_real_rota(app, caminho, handler, opcoes?)`
- `web_tempo_real_ativar_fallback(app, prefixo?, timeout_segundos?)`
- `web_tempo_real_definir_limites(app, limites)`
- `web_tempo_real_emitir_sala(app, canal, sala, evento, dados?)`
- `web_tempo_real_emitir_usuario(app, canal, id_usuario, evento, dados?)`
- `web_tempo_real_emitir_conexao(app, canal, id_conexao, evento, dados?)`
- `web_tempo_real_status(app, canal?)`

Aliases de compatibilidade:

- `web_socket_rota`, `web_websocket_rota`, `web_realtime_rota`
- `web_realtime_ativar_fallback`, `web_realtime_definir_limites`
- `web_realtime_emitir_sala`, `web_realtime_emitir_usuario`, `web_realtime_emitir_conexao`
- `web_realtime_status`

## Handler de tempo real

`handler(req)` recebe mapa com:

- `evento`: `conectar`, `mensagem`, `desconectar`
- `mensagem`/`payload` em evento de mensagem
- contexto de correlação: `id_requisicao`, `id_traco`, `id_usuario`
- aliases: `request_id`, `trace_id`, `user_id`
- `id_conexao`/`connection_id`, `canal`/`channel`, `ip`, `salas`

Resposta opcional do handler para roteamento:

- `{"destino": "sala", "sala": "nome", "evento": "x", "dados": {...}}`
- `{"destino": "usuario", "id_usuario": "u1", "evento": "x", "dados": {...}}`
- `{"destino": "conexao", "id_conexao": "c1", "evento": "x", "dados": {...}}`
- `{"destino": "canal", "evento": "x", "dados": {...}}`
- `{"aceitar": verdadeiro/falso}` no `conectar`

## Eventos nativos

Mensagens `tipo` reconhecidas no runtime:

- `ping`
- `entrar_sala`
- `sair_sala`
- `typing`
- `read_receipt`
- `broadcast_sala`
- `broadcast_usuario`
- `broadcast_conexao`

## Fallback de transporte

Com `web_tempo_real_ativar_fallback`, endpoints HTTP:

- `POST <prefixo>/conectar`
- `POST <prefixo>/enviar`
- `GET  <prefixo>/receber`
- `POST <prefixo>/desconectar`
- `GET  <prefixo>/status`

## Limites e proteção

`web_tempo_real_definir_limites` aceita:

- `max_conexoes_total`
- `max_conexoes_por_ip`
- `max_conexoes_por_usuario`
- `max_conexoes_por_sala`
- `max_payload_bytes`
- `max_mensagens_por_janela`
- `janela_rate_segundos`
- `heartbeat_segundos`

## Observabilidade da camada realtime

Métricas de runtime registradas em `runtime.eventos_total` com componente `tempo_real` para:

- abertura/fechamento de conexão
- broadcast
- processamento de mensagem
- erro de conexão

## Exemplo mínimo

```trama
função chat(req)
    retorne {"aceitar": verdadeiro}
fim

assíncrona função principal()
    app = web_criar_app()
    web_tempo_real_rota(app, "/ws/chat", chat, {"jwt_segredo": "segredo"})
    web_tempo_real_ativar_fallback(app, "/tempo-real/fallback", 2)
    servidor = aguarde web_iniciar(app, "127.0.0.1", 8080)
    aguarde web_parar(servidor)
fim
```

## Expressões multilinha

Trama aceita expressões multilinha em contextos delimitados:

- chamada de função com argumentos em múltiplas linhas;
- literais de lista em múltiplas linhas;
- literais de mapa em múltiplas linhas;
- indexação encadeada com quebra de linha controlada.

Exemplo:

```trama
função principal()
    dados = {
        "nums": [
            1,
            2
        ]
    }

    exibir(
        dados["nums"][0]
    )
fim
```
