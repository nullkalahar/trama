# Linguagem Trama v2.0.3 (Realtime distribuido em escala)

A v2.0.3 evolui o runtime de tempo real para operacao distribuida com ordenacao por canal, ACK/NACK/retry/reenvio, reconexao por cursor e observabilidade de entrega.

## Objetivo

- sincronizar presenca e salas entre multiplas instancias;
- distribuir broadcast entre nos via backplane;
- garantir entrega auditavel com ack/nack/reenvio;
- suportar reconexao com replay por cursor;
- proteger contra abuso por limites de conexao e taxa.

## API canonica pt-BR

- `web_tempo_real_rota(app, caminho, handler_fn, opcoes?)`
- `web_tempo_real_ativar_fallback(app, prefixo?, timeout_segundos?)`
- `web_tempo_real_definir_limites(app, limites)`
- `web_tempo_real_configurar_distribuicao(app, opcoes?)`
- `web_tempo_real_sincronizar_distribuicao(app)`
- `web_tempo_real_configurar_backplane(app, disponivel?)`
- `web_tempo_real_publicar(app, canal, evento, dados?, opcoes?)`
- `web_tempo_real_confirmar_ack(app, canal, id_mensagem, id_conexao, status?)`
- `web_tempo_real_reenviar_pendentes(app, canal, id_mensagem?)`
- `web_tempo_real_status(app, canal?)`

Aliases de compatibilidade:

- `web_realtime_*` (mantidos por retrocompatibilidade).

## Distribuicao entre instancias

`web_tempo_real_configurar_distribuicao` aceita:

- `ativar` (bool): habilita modo distribuido.
- `grupo` (texto): dominio logico compartilhado entre nos.
- `id_instancia` (texto): identificador estavel da instancia.
- `auto_sincronizar` (bool): sincroniza eventos remotos automaticamente.
- `backplane`: `memoria` (testes/single-processo) ou `redis` (producao multi-processo).
- `redis_url` e `chave_prefixo_redis` (quando `backplane="redis"`).

## Presenca e salas distribuidas

Eventos de presenca/salas sao propagados no backplane:

- `conectar` / `desconectar`;
- `entrar` / `sair` sala.

`web_tempo_real_status` expoe:

- conexoes locais e remotas por canal;
- salas locais e remotas;
- backlog local por canal/sala.

## Entrega ordenada com ACK/NACK/reenvio

Cada mensagem publicada recebe:

- `id_mensagem`;
- `cursor` (ordem global por canal no contexto distribuido);
- `exigir_ack`.

Fluxo:

1. publicacao (`web_tempo_real_publicar`)
2. confirmacao (`web_tempo_real_confirmar_ack(..., "ack")`)
3. negativa (`status="nack"`) com retry controlado
4. reenvio explicito (`web_tempo_real_reenviar_pendentes`)

## Reconexao por cursor

Fallback HTTP suporta reconexao com cursor:

- `POST /tempo-real/fallback/conectar?cursor_ultimo=<n>`
- `GET /tempo-real/fallback/receber?id_conexao=<id>&cursor_desde=<n>`

Resposta de `receber` inclui `cursor_ate` para checkpoint do cliente.

## Limites e protecao de abuso

`web_tempo_real_definir_limites` suporta (alem dos limites anteriores):

- `max_mensagens_por_janela_usuario`
- `max_mensagens_por_janela_sala`
- `janela_replay_segundos`
- `max_eventos_historico_canal`

## Fallback quando backplane indisponivel

Quando o backplane falha:

- o no continua atendendo conexoes locais;
- mensagens locais continuam fluindo sem corromper estado local;
- runtime marca degradacao e incrementa metrica de falha.

## Metricas auditaveis

`web_tempo_real_status(...)["metricas"]` inclui:

- `entregues`, `ack`, `nack`, `retries`, `reenvios`;
- `reconexoes`, `desconexoes`;
- `falhas_backplane`, `degradacao_eventos`;
- latencias medias de entrega e reconexao;
- `eventos_remotos_aplicados`.

## Testes de referencia da versao

- `tests/test_realtime_v203.py`
- `tests/test_vm.py::test_v203_tempo_real_distribuido_em_vm`

Nota sobre redis em testes:

- o teste de integracao redis usa `TRAMA_TEST_REDIS_URL` quando informado;
- sem essa variavel, tenta usar `redis-server` local;
- se nenhum dos dois estiver disponivel, o caso redis e marcado como `skip` (sem mascarar falhas dos demais cenarios obrigatorios).
