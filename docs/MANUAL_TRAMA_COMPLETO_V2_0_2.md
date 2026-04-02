# Manual Completo Trama (até v2.0.2)

Este manual consolida, em um só lugar, o estado prático da linguagem Trama até a versão v2.0.2.

Objetivo do documento:
- servir como guia único de onboarding;
- detalhar o que já está disponível para uso real;
- registrar contratos canônicos pt-BR e compatibilidades;
- apoiar desenvolvimento backend com previsibilidade.

## 1. Identidade da linguagem

A Trama é uma linguagem de programação nativa em português do Brasil (pt-BR), com:
- fonte `.trm`;
- compilação para bytecode `.tbc`;
- execução em VM própria.

Regras oficiais de linguagem:
- forma canônica é pt-BR;
- palavras-chave em português são oficiais;
- variações sem acento são aceitas;
- keywords são case-insensitive;
- identificadores canônicos usam `snake_case`.

Exemplos de equivalência:
- `função` = `funcao`
- `senão` = `senao`
- `assíncrona` = `assincrona`
- `aguarde` = `await` (compatibilidade)

## 2. Arquitetura de execução

Pipeline da linguagem:

`fonte (.trm) -> lexer -> parser -> AST -> semântica -> compilador -> bytecode (.tbc) -> VM`

Há dois caminhos principais:
- execução de fonte (`trama executar arquivo.trm`);
- execução de bytecode (`trama executar-tbc arquivo.tbc`).

## 3. Sintaxe e núcleo da linguagem

### 3.1 Tipos e estruturas
- números inteiros e reais;
- texto;
- lógico (`verdadeiro`, `falso`);
- `nulo`;
- listas (`[]`);
- mapas (`{}`) com indexação por chave;
- indexação (`obj[chave]`).

### 3.2 Controle de fluxo
- `se` / `senão`;
- `enquanto`;
- `pare`;
- `continue`;
- `retorne`.

### 3.3 Funções e escopo
- `função nome(...) ... fim`;
- funções aninhadas;
- closures;
- autoexecução de `principal()` quando presente.

### 3.4 Erros e exceções
- `tente` / `pegue` / `finalmente`;
- `lance` para lançar exceção;
- tratamento com contexto de execução em VM.

### 3.5 Módulos e import
- `importe modulo como alias`;
- import por caminho de módulo Trama;
- import de `.tbc` no caminho de runtime nativo fase 2.

### 3.6 Assíncrono
- `assíncrona função`;
- `aguarde`;
- utilitários: criação/cancelamento de tarefa e timeout.

## 4. CLI e fluxo de trabalho

Comandos relevantes:
- `trama executar`
- `trama compilar`
- `trama executar-tbc`
- `trama testar`
- `trama lint`
- `trama formatar`
- `trama cobertura`
- `trama template-backend`
- `trama paridade-selfhost`
- `trama --diagnostico-runtime`

Distribuição:
- binário standalone;
- pacote `.deb`;
- scripts de build/release em `scripts/`.

## 5. Runtime backend (capacidade consolidada)

### 5.1 HTTP programável
- app HTTP nativo;
- rotas dinâmicas por método;
- objetos `requisicao`/`resposta`;
- middlewares `pre` e `pos`;
- handler global de erro;
- CORS;
- healthcheck (`saude`, `pronto`, `vivo`);
- servir estáticos.

### 5.2 Contrato de API
- rotas com contrato de resposta (`web_rota_contrato`);
- validação de envelope canônico (`ok`, `dados`, `erro`, `meta`);
- versionamento base de API por prefixo (`web_api_versionar`).

### 5.3 DTO/validação/contrato (v2.0.2)
- `web_rota_dto` para DTO declarativo por rota;
- validação profunda em `corpo`, `consulta`, `parametros`, `formulario`;
- coerção de tipos (`coagir`);
- sanitização de texto (`trim`, colapsar espaços, caixa, remoção de acento/html);
- defaults (`padrao`), obrigatoriedade, enum, limites numéricos e de tamanho;
- listas/objetos aninhados com validação recursiva;
- erro de validação por campo:
  - `codigo`
  - `campo`
  - `mensagem`
  - `detalhes`
- contrato de entrada (`contrato_entrada.campos_permitidos`) para remoção de campos proibidos;
- contrato de resposta versionado:
  - `contrato_resposta.versoes`
  - `versao_padrao`
  - `retrocompativel`
- headers de rastreio de versão de contrato:
  - `X-Contrato-Versao-Solicitada`
  - `X-Contrato-Versao-Aplicada`
- geração de exemplos para teste com `dto_gerar_exemplos`.

### 5.4 Segurança
- JWT (`jwt_criar`, `jwt_verificar`);
- hash/verificação de senha (`senha_hash`, `senha_verificar`);
- RBAC com papéis/permissões;
- autenticação/autorização por rota.

### 5.5 Jobs e webhooks
- filas em memória;
- retries, timeout e backoff;
- idempotência por chave;
- DLQ básica;
- webhook com retry.

### 5.6 Banco de dados
- conexão SQL (`sqlite`, `postgres`, `postgresql`);
- execução/consulta/transações;
- query builder;
- ORM;
- migrações idempotentes;
- migrações versionadas com compatibilidade/dry-run/rollback;
- schema diff/preview/aplicação;
- seeds por ambiente;
- trilha de migração.

### 5.7 Storage e mídia
- storage local;
- storage S3 compatível;
- upload/download/list/delete/url;
- pipeline de mídia (gzip/hash e imagem quando disponível).

### 5.8 Realtime
- rota de tempo real;
- websocket/fallback;
- salas/canais;
- presença;
- ack/nack/reenvio;
- limites por conexão/mensagem.

### 5.9 Observabilidade e operação
- logs estruturados;
- métricas de runtime (HTTP/DB/cache/jobs/etc.);
- tracing com correlação (`id_requisicao`, `id_traco`, `id_usuario`);
- endpoints de observabilidade e alertas;
- utilitários de saúde e scripts operacionais.

### 5.10 Domínio social/admin/sync
- comunidades/canais/cargos/membros;
- moderação;
- campanhas administrativas;
- auditoria administrativa;
- sync incremental e cache offline.

## 6. Contratos canônicos pt-BR

Princípio geral:
- nomes canônicos em pt-BR são padrão oficial;
- aliases em inglês são compatibilidade transitória.

Exemplos importantes:
- `banco_*`, `consulta_*`, `modelo_*`, `transacao_*`;
- `semente_aplicar` como alias pt-BR;
- `web_tempo_real_*` como forma canônica para realtime;
- `web_realtime_*`/`web_websocket_*` como compatibilidade.

## 7. Exemplos rápidos

### 7.1 DTO por rota

```trama
função criar(req)
    retorne {"status": 201, "json": {"ok": verdadeiro, "dados": req["corpo"]}}
fim

assíncrona função principal()
    app = web_criar_app()
    dto = {
        "corpo": {
            "tipo": "objeto",
            "campos": {
                "nome": {"tipo": "texto", "obrigatorio": verdadeiro, "sanitizar": {"trim": verdadeiro}},
                "idade": {"tipo": "inteiro", "coagir": verdadeiro}
            }
        }
    }
    web_rota_dto(app, "POST", "/api/v1/usuarios", criar, dto)
fim
```

### 7.2 Contrato versionado

```trama
contrato = {
    "versao_padrao": "v2",
    "versoes": {
        "v1": {"envelope": verdadeiro, "campos_obrigatorios": ["ok", "dados", "erro", "meta"]},
        "v2": {"envelope": verdadeiro, "campos_obrigatorios": ["ok", "dados", "erro", "meta", "links"]}
    },
    "retrocompativel": {"legacy": "v1"}
}
```

### 7.3 Geração de exemplos

```trama
exemplos = dto_gerar_exemplos(dto, "corpo")
exibir(exemplos["validos"][0])
exibir(exemplos["invalidos"][0])
```

## 8. Testes locais recomendados

### 8.1 Suíte local .trm v2.0.2

- caminho: `.local/tests/v2_0_2_dto_contrato_trm/`
- runner: `.local/tests/v2_0_2_dto_contrato_trm/run_local_v202_trm.sh`
- cobre:
  - validação DTO;
  - coerção/sanitização;
  - erros por campo;
  - contrato versionado/retrocompatível;
  - aliases de compatibilidade;
  - DTO em `parametros` e `consulta`.

### 8.2 Suíte oficial Python

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

## 9. Catálogo de builtins (snapshot completo)

Fonte: `src/trama/semantic.py`.

Total atual: 271 builtins/aliases com assinatura semântica.


### 9.1 Lista alfabética completa

- `admin_auditoria_listar`
- `admin_auditoria_registrar`
- `agora_iso`
- `alertas_avaliar`
- `armazenamento_criar_local`
- `armazenamento_criar_s3`
- `armazenamento_ler`
- `armazenamento_listar`
- `armazenamento_local_criar`
- `armazenamento_remover`
- `armazenamento_s3_criar`
- `armazenamento_salvar`
- `armazenamento_url`
- `arquivo_existe`
- `banco_conectar`
- `banco_consultar`
- `banco_executar`
- `banco_fechar`
- `cache_aquecer`
- `cache_definir`
- `cache_existe`
- `cache_invalida_padrao`
- `cache_invalidar_padrao`
- `cache_limpar`
- `cache_obter`
- `cache_offline_listar`
- `cache_offline_obter`
- `cache_offline_salvar`
- `cache_remover`
- `cache_stats`
- `campaign_create`
- `campaign_run`
- `campaign_schedule`
- `campaign_status`
- `campanha_agendar`
- `campanha_criar`
- `campanha_executar`
- `campanha_listar`
- `campanha_status`
- `canal_criar`
- `cancelar_tarefa`
- `cargo_criar`
- `channel_create`
- `circuito_resetar`
- `circuito_status`
- `com_timeout`
- `community_create`
- `community_get`
- `compilar_trama_arquivo`
- `compilar_trama_fonte`
- `compilar_trama_para_arquivo`
- `comunidade_criar`
- `comunidade_listar`
- `comunidade_obter`
- `comunidade_permissao_tem`
- `config_carregar_ambiente`
- `config_carregar`
- `config_validar`
- `consulta_executar`
- `consulta_limite`
- `consulta_onde_igual`
- `consulta_ordenar_por`
- `consulta_selecionar`
- `consulta_sql`
- `criar_tarefa`
- `dormir`
- `dto_gerar_exemplos`
- `dto_validar`
- `env_obter`
- `env_todos`
- `escrever_texto_async`
- `escrever_texto`
- `exibir`
- `fila_criar`
- `fila_enfileirar`
- `fila_processar`
- `fila_status`
- `http_get`
- `http_obter`
- `http_post`
- `http_postar`
- `json_parse_seguro`
- `json_parse`
- `json_stringify_pretty`
- `json_stringify`
- `jwt_criar`
- `jwt_verificar`
- `ler_texto_async`
- `ler_texto`
- `lista_adicionar`
- `listar_diretorio`
- `log_erro`
- `log_estruturado_json`
- `log_estruturado`
- `log_info`
- `log`
- `mapa_chaves`
- `mapa_definir`
- `mapa_obter`
- `member_join`
- `member_leave`
- `membro_atribuir_cargo`
- `membro_entrar`
- `membro_sair`
- `metrica_inc`
- `metrica_incrementar`
- `metrica_observar`
- `metricas_reset`
- `metricas_snapshot`
- `midia_comprimir_gzip`
- `midia_converter_imagem`
- `midia_descomprimir_gzip`
- `midia_gzip_comprimir`
- `midia_gzip_descomprimir`
- `midia_ler_arquivo`
- `midia_pipeline`
- `midia_redimensionar_imagem`
- `midia_salvar_arquivo`
- `midia_sha256`
- `migracao_aplicar_versionada_v2`
- `migracao_aplicar_versionada`
- `migracao_aplicar`
- `migracao_compatibilidade_validar`
- `migracao_desfazer_ultima`
- `migracao_listar`
- `migracao_reverter_ultima`
- `migracao_status`
- `migracao_trilha_listar`
- `migracao_trilha`
- `migracao_validar_compatibilidade`
- `migracao_versionada_aplicar_v2`
- `migracao_versionada_aplicar`
- `modelo_atualizar`
- `modelo_buscar_por_id`
- `modelo_inserir`
- `modelo_listar`
- `moderacao_acao`
- `moderacao_listar`
- `moderation_action`
- `moderation_list`
- `observabilidade_resumo`
- `orm_atualizar`
- `orm_buscar_por_id`
- `orm_inserir`
- `orm_listar`
- `orm_modelo`
- `orm_relacao_muitos_para_muitos`
- `orm_relacao_um_para_muitos`
- `orm_relacao_um_para_um`
- `papel_atribuir`
- `papel_criar_modelo`
- `papel_listar_usuario`
- `papel_tem`
- `permissao_tem`
- `pg_conectar`
- `pg_consultar`
- `pg_executar`
- `pg_fechar`
- `pg_transacao_commit`
- `pg_transacao_iniciar`
- `pg_transacao_rollback`
- `pg_tx_consultar`
- `pg_tx_executar`
- `qb_consultar`
- `qb_limite`
- `qb_order_by`
- `qb_select`
- `qb_sql`
- `qb_where_eq`
- `rbac_atribuir`
- `rbac_criar`
- `rbac_papeis_usuario`
- `rbac_tem_papel`
- `rbac_tem_permissao`
- `resiliencia_executar`
- `role_create`
- `schema_aplicar_diff`
- `schema_constraint_check`
- `schema_constraint_fk`
- `schema_constraint_unica`
- `schema_definir_tabela`
- `schema_definir`
- `schema_diff`
- `schema_inspecionar`
- `schema_preview_plano`
- `seed_aplicar_ambiente`
- `seed_aplicar`
- `segredo_ler`
- `segredo_mascarar`
- `segredo_obter`
- `semente_aplicar_ambiente`
- `semente_aplicar`
- `senha_gerar_hash`
- `senha_hash`
- `senha_validar`
- `senha_verificar`
- `sync_conflict_resolve`
- `sync_consume`
- `sync_consumir`
- `sync_cursor_atual`
- `sync_register_event`
- `sync_registrar_evento`
- `sync_resolver_conflito`
- `tamanho`
- `timestamp`
- `token_criar`
- `token_verificar`
- `traca_evento`
- `traca_finalizar`
- `traca_iniciar`
- `tracas_reset`
- `tracas_snapshot`
- `traco_evento`
- `traco_finalizar`
- `traco_iniciar`
- `tracos_reset`
- `tracos_snapshot`
- `trama_compilar_arquivo`
- `trama_compilar_fonte`
- `trama_compilar_para_arquivo`
- `transacao_cancelar`
- `transacao_confirmar`
- `transacao_consultar`
- `transacao_executar`
- `transacao_iniciar`
- `web_adicionar_rota_echo_json`
- `web_adicionar_rota_json`
- `web_api_versao`
- `web_api_versionar`
- `web_ativar_healthcheck`
- `web_ativar_observabilidade`
- `web_configurar_cors`
- `web_criar_app`
- `web_iniciar`
- `web_limite_taxa`
- `web_middleware`
- `web_observabilidade_ativar`
- `web_parar`
- `web_rate_limit`
- `web_realtime_ativar_fallback`
- `web_realtime_confirmar_ack`
- `web_realtime_definir_limites`
- `web_realtime_emitir_conexao`
- `web_realtime_emitir_sala`
- `web_realtime_emitir_usuario`
- `web_realtime_publicar`
- `web_realtime_reenviar_pendentes`
- `web_realtime_rota`
- `web_realtime_status`
- `web_rota_com_contrato`
- `web_rota_com_dto`
- `web_rota_contrato`
- `web_rota_dto`
- `web_rota`
- `web_saude_paths`
- `web_servir_estaticos`
- `web_socket_rota`
- `web_tempo_real_ativar_fallback`
- `web_tempo_real_confirmar_ack`
- `web_tempo_real_definir_limites`
- `web_tempo_real_emitir_conexao`
- `web_tempo_real_emitir_sala`
- `web_tempo_real_emitir_usuario`
- `web_tempo_real_publicar`
- `web_tempo_real_reenviar_pendentes`
- `web_tempo_real_rota`
- `web_tempo_real_status`
- `web_tratador_erro`
- `web_usar_middleware`
- `web_websocket_rota`
- `webhook_enviar`

### 9.2 Agrupamento por prefixo

- `admin` (2): `admin_auditoria_listar` `admin_auditoria_registrar` 
- `agora` (1): `agora_iso` 
- `alertas` (1): `alertas_avaliar` 
- `armazenamento` (9): `armazenamento_criar_local` `armazenamento_criar_s3` `armazenamento_ler` `armazenamento_listar` `armazenamento_local_criar` `armazenamento_remover` `armazenamento_s3_criar` `armazenamento_salvar` `armazenamento_url` 
- `arquivo` (1): `arquivo_existe` 
- `banco` (4): `banco_conectar` `banco_consultar` `banco_executar` `banco_fechar` 
- `cache` (12): `cache_aquecer` `cache_definir` `cache_existe` `cache_invalida_padrao` `cache_invalidar_padrao` `cache_limpar` `cache_obter` `cache_offline_listar` `cache_offline_obter` `cache_offline_salvar` `cache_remover` `cache_stats` 
- `campaign` (4): `campaign_create` `campaign_run` `campaign_schedule` `campaign_status` 
- `campanha` (5): `campanha_agendar` `campanha_criar` `campanha_executar` `campanha_listar` `campanha_status` 
- `canal` (1): `canal_criar` 
- `cancelar` (1): `cancelar_tarefa` 
- `cargo` (1): `cargo_criar` 
- `channel` (1): `channel_create` 
- `circuito` (2): `circuito_resetar` `circuito_status` 
- `com` (1): `com_timeout` 
- `community` (2): `community_create` `community_get` 
- `compilar` (3): `compilar_trama_arquivo` `compilar_trama_fonte` `compilar_trama_para_arquivo` 
- `comunidade` (4): `comunidade_criar` `comunidade_listar` `comunidade_obter` `comunidade_permissao_tem` 
- `config` (3): `config_carregar` `config_carregar_ambiente` `config_validar` 
- `consulta` (6): `consulta_executar` `consulta_limite` `consulta_onde_igual` `consulta_ordenar_por` `consulta_selecionar` `consulta_sql` 
- `criar` (1): `criar_tarefa` 
- `dormir` (1): `dormir` 
- `dto` (2): `dto_gerar_exemplos` `dto_validar` 
- `env` (2): `env_obter` `env_todos` 
- `escrever` (2): `escrever_texto` `escrever_texto_async` 
- `exibir` (1): `exibir` 
- `fila` (4): `fila_criar` `fila_enfileirar` `fila_processar` `fila_status` 
- `http` (4): `http_get` `http_obter` `http_post` `http_postar` 
- `json` (4): `json_parse` `json_parse_seguro` `json_stringify` `json_stringify_pretty` 
- `jwt` (2): `jwt_criar` `jwt_verificar` 
- `ler` (2): `ler_texto` `ler_texto_async` 
- `lista` (1): `lista_adicionar` 
- `listar` (1): `listar_diretorio` 
- `log` (5): `log` `log_erro` `log_estruturado` `log_estruturado_json` `log_info` 
- `mapa` (3): `mapa_chaves` `mapa_definir` `mapa_obter` 
- `member` (2): `member_join` `member_leave` 
- `membro` (3): `membro_atribuir_cargo` `membro_entrar` `membro_sair` 
- `metrica` (3): `metrica_inc` `metrica_incrementar` `metrica_observar` 
- `metricas` (2): `metricas_reset` `metricas_snapshot` 
- `midia` (10): `midia_comprimir_gzip` `midia_converter_imagem` `midia_descomprimir_gzip` `midia_gzip_comprimir` `midia_gzip_descomprimir` `midia_ler_arquivo` `midia_pipeline` `midia_redimensionar_imagem` `midia_salvar_arquivo` `midia_sha256` 
- `migracao` (13): `migracao_aplicar` `migracao_aplicar_versionada` `migracao_aplicar_versionada_v2` `migracao_compatibilidade_validar` `migracao_desfazer_ultima` `migracao_listar` `migracao_reverter_ultima` `migracao_status` `migracao_trilha` `migracao_trilha_listar` `migracao_validar_compatibilidade` `migracao_versionada_aplicar` `migracao_versionada_aplicar_v2` 
- `modelo` (4): `modelo_atualizar` `modelo_buscar_por_id` `modelo_inserir` `modelo_listar` 
- `moderacao` (2): `moderacao_acao` `moderacao_listar` 
- `moderation` (2): `moderation_action` `moderation_list` 
- `observabilidade` (1): `observabilidade_resumo` 
- `orm` (8): `orm_atualizar` `orm_buscar_por_id` `orm_inserir` `orm_listar` `orm_modelo` `orm_relacao_muitos_para_muitos` `orm_relacao_um_para_muitos` `orm_relacao_um_para_um` 
- `papel` (4): `papel_atribuir` `papel_criar_modelo` `papel_listar_usuario` `papel_tem` 
- `permissao` (1): `permissao_tem` 
- `pg` (9): `pg_conectar` `pg_consultar` `pg_executar` `pg_fechar` `pg_transacao_commit` `pg_transacao_iniciar` `pg_transacao_rollback` `pg_tx_consultar` `pg_tx_executar` 
- `qb` (6): `qb_consultar` `qb_limite` `qb_order_by` `qb_select` `qb_sql` `qb_where_eq` 
- `rbac` (5): `rbac_atribuir` `rbac_criar` `rbac_papeis_usuario` `rbac_tem_papel` `rbac_tem_permissao` 
- `resiliencia` (1): `resiliencia_executar` 
- `role` (1): `role_create` 
- `schema` (9): `schema_aplicar_diff` `schema_constraint_check` `schema_constraint_fk` `schema_constraint_unica` `schema_definir` `schema_definir_tabela` `schema_diff` `schema_inspecionar` `schema_preview_plano` 
- `seed` (2): `seed_aplicar` `seed_aplicar_ambiente` 
- `segredo` (3): `segredo_ler` `segredo_mascarar` `segredo_obter` 
- `semente` (2): `semente_aplicar` `semente_aplicar_ambiente` 
- `senha` (4): `senha_gerar_hash` `senha_hash` `senha_validar` `senha_verificar` 
- `sync` (7): `sync_conflict_resolve` `sync_consume` `sync_consumir` `sync_cursor_atual` `sync_register_event` `sync_registrar_evento` `sync_resolver_conflito` 
- `tamanho` (1): `tamanho` 
- `timestamp` (1): `timestamp` 
- `token` (2): `token_criar` `token_verificar` 
- `traca` (3): `traca_evento` `traca_finalizar` `traca_iniciar` 
- `tracas` (2): `tracas_reset` `tracas_snapshot` 
- `traco` (3): `traco_evento` `traco_finalizar` `traco_iniciar` 
- `tracos` (2): `tracos_reset` `tracos_snapshot` 
- `trama` (3): `trama_compilar_arquivo` `trama_compilar_fonte` `trama_compilar_para_arquivo` 
- `transacao` (5): `transacao_cancelar` `transacao_confirmar` `transacao_consultar` `transacao_executar` `transacao_iniciar` 
- `web` (45): `web_adicionar_rota_echo_json` `web_adicionar_rota_json` `web_api_versao` `web_api_versionar` `web_ativar_healthcheck` `web_ativar_observabilidade` `web_configurar_cors` `web_criar_app` `web_iniciar` `web_limite_taxa` `web_middleware` `web_observabilidade_ativar` `web_parar` `web_rate_limit` `web_realtime_ativar_fallback` `web_realtime_confirmar_ack` `web_realtime_definir_limites` `web_realtime_emitir_conexao` `web_realtime_emitir_sala` `web_realtime_emitir_usuario` `web_realtime_publicar` `web_realtime_reenviar_pendentes` `web_realtime_rota` `web_realtime_status` `web_rota` `web_rota_com_contrato` `web_rota_com_dto` `web_rota_contrato` `web_rota_dto` `web_saude_paths` `web_servir_estaticos` `web_socket_rota` `web_tempo_real_ativar_fallback` `web_tempo_real_confirmar_ack` `web_tempo_real_definir_limites` `web_tempo_real_emitir_conexao` `web_tempo_real_emitir_sala` `web_tempo_real_emitir_usuario` `web_tempo_real_publicar` `web_tempo_real_reenviar_pendentes` `web_tempo_real_rota` `web_tempo_real_status` `web_tratador_erro` `web_usar_middleware` `web_websocket_rota` 
- `webhook` (1): `webhook_enviar` 
