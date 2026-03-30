# Manual Completo da linguagem Trama (até v1.1)

Este manual consolida os recursos entregues da `v0.1` até a `v1.1`.

## 1. Fundamentos da linguagem

- linguagem canônica em pt-BR;
- equivalência com/sem acento em palavras-chave;
- palavras-chave case-insensitive;
- pipeline: `fonte .trm -> lexer -> parser -> AST -> semântica -> compilador -> bytecode -> VM`.

Exemplos de equivalência:

- `função` = `funcao`
- `senão` = `senao`
- `assíncrona` = `assincrona`

## 2. Núcleo da linguagem (v0.1-v0.4)

Recursos principais:

- variáveis, números, texto, lógico e `nulo`;
- listas e mapas;
- `se/senão`, `enquanto`, `pare`, `continue`;
- funções, `retorne`, closures;
- erros com `tente/pegue/finalmente` e `lance`;
- módulos com `importe ... como ...`;
- programação assíncrona com `assíncrona`, `aguarde`, tarefas e timeout;
- stdlib base de JSON, arquivos, ambiente, tempo, cliente HTTP e logs.

## 3. Backend web e banco (v0.5-v0.6)

### 3.1 Runtime web

- `web_criar_app`;
- rotas estáticas JSON e echo JSON;
- rotas dinâmicas por handler: `web_rota`;
- middleware pré/pós: `web_middleware`;
- tratador global de erro: `web_tratador_erro`;
- CORS, health/readiness/liveness, estáticos;
- contratos/versionamento de API: `web_rota_contrato`, `web_api_versionar`;
- limite de taxa: `web_rate_limit`;
- execução: `web_iniciar` / `web_parar`.

Objetos canônicos:

- `requisicao`
- `resposta`

### 3.2 Banco de dados

- drivers async para `sqlite:///...`, `postgres://...`, `postgresql://...`;
- API base:
  - `pg_conectar`, `pg_executar`, `pg_consultar`, `pg_fechar`;
- transações:
  - `pg_transacao_*`, `pg_tx_*`;
- query builder:
  - `qb_select`, `qb_where_eq`, `qb_order_by`, `qb_limite`, `qb_sql`, `qb_consultar`;
- ORM inicial:
  - `orm_inserir`, `orm_atualizar`, `orm_buscar_por_id`;
- migrações/sementes:
  - `migracao_aplicar`, `seed_aplicar`, `migracao_aplicar_versionada`, `migracao_status`, `migracao_reverter_ultima`, `migracao_validar_compatibilidade`.

Aliases pt-BR:

- `banco_*`, `consulta_*`, `modelo_*`, `transacao_*`, `semente_aplicar`.

## 4. Segurança (v0.7)

### JWT

- `jwt_criar(payload, segredo, exp_segundos?, algoritmo?)`
- `jwt_verificar(token, segredo, leeway_segundos?)`
- aliases: `token_criar`, `token_verificar`

### Senhas

- `senha_hash(senha, algoritmo?)`
- `senha_verificar(senha, hash)`
- aliases: `senha_gerar_hash`, `senha_validar`

Algoritmos:

- `pbkdf2` (nativo)
- `bcrypt` (opcional)
- `argon2`/`argon2id` (opcional)

### RBAC

- `rbac_criar`, `rbac_atribuir`, `rbac_papeis_usuario`
- `rbac_tem_papel`, `rbac_tem_permissao`
- aliases: `papel_*`, `permissao_tem`

## 5. Observabilidade (v0.8)

- logs estruturados: `log_estruturado`, `log_estruturado_json`;
- métricas: `metrica_incrementar`, `metrica_observar`, `metricas_snapshot`, `metricas_reset`;
- tracing: `traco_iniciar`, `traco_evento`, `traco_finalizar`, `tracos_snapshot`, `tracos_reset`;
- aliases de compatibilidade sem acento: `traca_*`, `tracas_*`.

## 6. Tooling oficial (v0.9)

- test runner: `trama testar [alvo]`;
- lint: `trama lint [alvo]`;
- formatação: `trama formatar [alvo] [--aplicar]`;
- cobertura: `trama cobertura [alvo]`;
- template backend: `trama template-backend <destino>`.

## 7. Backend de produção (v1.0)

Consolidação de runtime robusto para backend:

- handlers dinâmicos por rota;
- middleware chain real e validação por esquema;
- segurança por rota (JWT/RBAC) e rate-limit;
- versionamento/contrato de API;
- jobs + webhooks com retries, timeout, idempotência e DLQ básica;
- migração versionada com lock/dry-run/compatibilidade;
- documentação operacional (SLO, monitoramento, backup/restore).

## 8. Auto-hospedagem do compilador (v1.0.5)

Status atual:

- compilador principal em `.trm` em `selfhost/compilador/mod.trm`;
- runtime base em `.trm` em `selfhost/runtime/mod.trm`;
- `trama compilar` usando pipeline self-host por padrão;
- `trama compilar-legado` para compatibilidade transitória;
- `trama semente-compilar` (compilador semente mínimo);
- `trama paridade-selfhost` (equivalência);
- `trama executar-tbc` (executa bytecode sem etapa de compilação no runtime).

Obs.: ainda existe implementação em `.py` para bootstrap/transição.

## 9. v1.1 - Configuração, cache e resiliência

### 9.1 Configuração e segredos

- `config_carregar_ambiente(padrao, prefixo?, obrigatorios?, schema?)`
- `config_validar(config, obrigatorios?, schema?)`
- `segredo_obter(nome, padrao?, obrigatorio?, permitir_vazio?)`
- `segredo_mascarar(valor, visivel?)`
- alias: `segredo_ler`

### 9.2 Cache

- `cache_definir(chave, valor, ttl_segundos?, namespace?)`
- `cache_obter(chave, padrao?, namespace?)`
- `cache_existe(chave, namespace?)`
- `cache_remover(chave, namespace?)`
- `cache_invalidar_padrao(padrao, namespace?)`
- `cache_limpar(namespace?)`
- `cache_aquecer(itens, ttl_segundos?, namespace?)`
- `cache_stats(namespace?)`

### 9.3 Resiliência

- `resiliencia_executar(nome, operacao_fn, argumentos?, opcoes?)`
- `circuito_status(nome)`
- `circuito_resetar(nome?)`

Opções suportadas:

- `tentativas`
- `timeout_segundos`
- `max_falhas`
- `reset_timeout_segundos`
- `base_backoff_segundos`
- `max_backoff_segundos`
- `jitter_segundos`
- `nao_retentaveis`

## 10. CLI atual

```bash
trama executar arquivo.trm
trama executar-tbc arquivo.tbc
trama bytecode arquivo.trm
trama compilar arquivo.trm -o programa.tbc
trama compilar-legado arquivo.trm -o programa.tbc
trama semente-compilar arquivo.trm -o programa.tbc
trama autocompilar arquivo.trm -o programa.tbc
trama paridade-selfhost arquivo.trm
trama testar [alvo]
trama lint [alvo]
trama formatar [alvo] [--aplicar]
trama cobertura [alvo]
trama template-backend <destino>
trama repl
```

## 11. Exemplos prontos

Ver:

- `exemplos/README_EXEMPLOS.md`
- diretório `exemplos/` com exemplos v0.x, v1.0 e v1.1.

## 12. Distribuição

- binário standalone: `scripts/build_standalone.sh`;
- build self-host: `scripts/build_selfhost.sh`;
- release self-host: `scripts/build_release_selfhost.sh`;
- pacote Debian: `scripts/package_deb.sh`.

## 13. Política de atualização de documentação

A cada versão:

- atualizar manual da versão (`docs/LINGUAGEM_VX_Y.md`);
- atualizar manual consolidado;
- atualizar roadmap/checklists no README.
