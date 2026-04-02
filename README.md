# trama

A `trama` é uma linguagem de programação em português (pt-BR), de uso geral, com tipagem simples (estilo Python), compilação para bytecode próprio e execução em VM própria.

## Direção do Projeto

A meta é construir uma linguagem geral primeiro, com base sólida, e evoluir para suportar backend robusto.

## Identidade pt-BR

A `trama` é uma linguagem **nativamente em português do Brasil**.

Regras oficiais de identidade linguística:

- forma canônica da linguagem: **pt-BR**
- palavras-chave oficiais são em português
- variações sem acento são aceitas como equivalentes
- keywords são case-insensitive

Exemplos de equivalência:

- `função` = `funcao`
- `senão` = `senao`
- `assíncrona` = `assincrona`
- `aguarde` = `await` (compatibilidade, mantendo `aguarde` como forma canônica pt-BR)

Palavras-chave oficiais (forma canônica):

- `função`, `retorne`, `se`, `senão`, `enquanto`, `para`, `em`
- `verdadeiro`, `falso`, `nulo`, `fim`, `pare`, `continue`
- `tente`, `pegue`, `finalmente`, `lance`, `importe`, `como`
- `assíncrona`, `aguarde`

### Convenção de nomes canônicos (identificadores)

Para manter previsibilidade e evitar ambiguidades no parser:

- identificadores canônicos devem usar `snake_case` com `_` (underscore)
- não usar `-` (hífen) em identificadores de código
- em código canônico, preferir nomes sem acento em identificadores

Exemplos canônicos:

- `linha_base`
- `medicao_desempenho`
- `encerramento_gracioso`

Regra de normalização recomendada para equivalência de identificadores:

- converter para minúsculas
- remover diacríticos (acentos)
- converter separadores para `_`
- colapsar `_` repetido

Com isso, nomes como `Medição-Desempenho` e `medicao_desempenho` convergem para o mesmo formato canônico interno.


Isso significa que, além de sintaxe agradável, a `trama` precisa amadurecer em:

- previsibilidade de execução
- mensagens de erro boas
- organização de módulos
- biblioteca padrão útil para servidor
- estabilidade para manutenção de código grande

## Arquitetura

Pipeline da linguagem:

`fonte (.trm)` -> `lexer` -> `parser` -> `AST` -> `análise semântica` -> `compilador` -> `bytecode` -> `VM` -> `execução`

## Estado Atual

- plano técnico documentado em [`docs/PLANO_TRAMA.md`](docs/PLANO_TRAMA.md)
- manual da linguagem v0.1 em [`docs/LINGUAGEM_V0_1.md`](docs/LINGUAGEM_V0_1.md)
- manual da linguagem v0.2 em [`docs/LINGUAGEM_V0_2.md`](docs/LINGUAGEM_V0_2.md)
- manual da linguagem v0.3 em [`docs/LINGUAGEM_V0_3.md`](docs/LINGUAGEM_V0_3.md)
- manual da linguagem v0.4 em [`docs/LINGUAGEM_V0_4.md`](docs/LINGUAGEM_V0_4.md)
- manual da linguagem v0.5 em [`docs/LINGUAGEM_V0_5.md`](docs/LINGUAGEM_V0_5.md)
- manual da linguagem v0.6 em [`docs/LINGUAGEM_V0_6.md`](docs/LINGUAGEM_V0_6.md)
- manual da linguagem v0.7 em [`docs/LINGUAGEM_V0_7.md`](docs/LINGUAGEM_V0_7.md)
- manual da linguagem v0.8 em [`docs/LINGUAGEM_V0_8.md`](docs/LINGUAGEM_V0_8.md)
- manual da linguagem v0.9 em [`docs/LINGUAGEM_V0_9.md`](docs/LINGUAGEM_V0_9.md)
- manual da linguagem v1.1 em [`docs/LINGUAGEM_V1_1.md`](docs/LINGUAGEM_V1_1.md)
- manual da linguagem v1.2 em [`docs/LINGUAGEM_V1_2.md`](docs/LINGUAGEM_V1_2.md)
- manual da linguagem v1.3 em [`docs/LINGUAGEM_V1_3.md`](docs/LINGUAGEM_V1_3.md)
- manual da linguagem v1.4 em [`docs/LINGUAGEM_V1_4.md`](docs/LINGUAGEM_V1_4.md)
- manual da linguagem v1.5-v1.8 em [`docs/LINGUAGEM_V1_5_V1_8.md`](docs/LINGUAGEM_V1_5_V1_8.md)
- manual da linguagem v2.0 (andamento) em [`docs/LINGUAGEM_V2_0.md`](docs/LINGUAGEM_V2_0.md)
- manual da linguagem v2.0.2 (DTO/contrato HTTP) em [`docs/LINGUAGEM_V2_0_2.md`](docs/LINGUAGEM_V2_0_2.md)
- manual completo consolidado até v2.0.2 em [`docs/MANUAL_TRAMA_COMPLETO_V2_0_2.md`](docs/MANUAL_TRAMA_COMPLETO_V2_0_2.md)
- manual completo consolidado até v1.4 em [`docs/MANUAL_COMPLETO_ATE_V1_4.md`](docs/MANUAL_COMPLETO_ATE_V1_4.md)
- manual completo consolidado até v1.8 em [`docs/MANUAL_COMPLETO_ATE_V1_8.md`](docs/MANUAL_COMPLETO_ATE_V1_8.md)
- manual prático da v2.0 fase 2 em [`docs/MANUAL_V2_0_FASE2.md`](docs/MANUAL_V2_0_FASE2.md)
- roadmap detalhado de implementações futuras v2.1 em [`docs/ROADMAP_IMPLEMENTACOES_FUTURAS_V2_1.md`](docs/ROADMAP_IMPLEMENTACOES_FUTURAS_V2_1.md)
- guia de auto-hospedagem v1.0 em [`docs/GUIA_AUTO_HOSPEDAGEM_V1_0.md`](docs/GUIA_AUTO_HOSPEDAGEM_V1_0.md)
- guia de auto-hospedagem do compilador v1.0.5 em [`docs/AUTO_HOSPEDAGEM_V1_0_5.md`](docs/AUTO_HOSPEDAGEM_V1_0_5.md)
- especificação formal de bytecode v1 em [`docs/BYTECODE_V1.md`](docs/BYTECODE_V1.md)
- ABI formal da VM v1 em [`docs/ABI_VM_V1.md`](docs/ABI_VM_V1.md)
- matriz de cobertura bytecode/ABI v1 em [`docs/MATRIZ_COBERTURA_BYTECODE_ABI_V1.md`](docs/MATRIZ_COBERTURA_BYTECODE_ABI_V1.md)
- contratos canônicos da CLI nativa v2 em [`docs/CLI_NATIVA_V2_CONTRATOS.md`](docs/CLI_NATIVA_V2_CONTRATOS.md)
- auditoria de paridade real da fase 2 em [`docs/V2_FASE2_PARIDADE_VM_NATIVA.md`](docs/V2_FASE2_PARIDADE_VM_NATIVA.md)
- checklist de entrega em [`docs/V0_1_CHECKLIST.md`](docs/V0_1_CHECKLIST.md)
- exemplos v2.0 em [`exemplos/v20/`](exemplos/v20/)
- pipeline de linguagem funcional (lexer -> parser -> semântica -> compilador -> bytecode -> VM)
- CLI funcional em [`src/trama/cli.py`](src/trama/cli.py)
- binário standalone gerável por [`scripts/build_standalone.sh`](scripts/build_standalone.sh)
- pacote Debian gerável por [`scripts/package_deb.sh`](scripts/package_deb.sh)
- preparo de repositório APT por [`scripts/init_apt_repo.sh`](scripts/init_apt_repo.sh)

## Progresso do Desenvolvimento

### Feito

- arquitetura e direção do projeto definidas
- regra oficial de equivalência com/sem acento em palavras-chave (ex.: `função/funcao`, `senão/senao`)
- lexer com:
  - keywords equivalentes por acento e case-insensitive
  - comentários `#` e `//`
  - strings com escapes (`\"`, `\\`, `\n`, `\t`, `\r`)
  - números inteiros/reais com validação
  - operadores simples e compostos (`==`, `!=`, `>=`, `<=`)
  - erros léxicos com linha/coluna
- parser com:
  - precedência de operadores
  - declarações de função
  - `se/senao/senão`, `enquanto`
  - `retorne`, `pare`, `continue`
  - atribuição e chamadas de função
  - `tente/pegue/finalmente`, `lance`, `importe`
  - coleções (`[]`, `{}`) e indexação (`obj[chave]`)
- Sprint 3 completo:
  - compilação AST -> bytecode
  - execução em VM com funções, controle de fluxo e `exibir`
  - autoexecução de `principal()` quando definida
- Sprint 4 completo:
  - CLI real para `executar`, `bytecode`, `compilar`
  - saída de bytecode em arquivo `.tbc` (JSON)
- Sprint 6 (núcleo de distribuição) completo:
  - geração de binário standalone
  - geração de pacote `.deb`
  - scripts para inicialização/publicação de repositório APT
- v0.2 completa:
  - exceções reais com `tente/pegue/finalmente`
  - módulos via `importe`
  - escopos e closures para funções aninhadas
  - coleções nativas (lista/mapa) e JSON (`json_parse`/`json_stringify`)
- v0.3 completa:
  - runtime assíncrono oficial
  - `assíncrona/aguarde` (equivalente pt-BR de `async/await`)
  - tarefas, timeout e cancelamento (`criar_tarefa`, `com_timeout`, `cancelar_tarefa`)
  - I/O não bloqueante (`ler_texto_async`, `escrever_texto_async`)
- v0.4 completa:
  - stdlib backend mínima (HTTP client, FS, ENV, TIME, LOG)
  - serialização JSON robusta (`json_parse_seguro`, `json_stringify_pretty`)
  - configuração por ambiente (`config_carregar`)
- v0.5 completa:
  - servidor web nativo
  - roteamento, middlewares, CORS e fluxo `requisicao/resposta`
  - validação de payload e erros padronizados
  - healthcheck e serving de estáticos
- v0.6 completa:
  - driver de banco assíncrono (`pg_*`) com DSN `sqlite:///`, `postgres://` e `postgresql://` com PostgreSQL nativo (`asyncpg`)
  - query builder/ORM inicial (`qb_*`, `orm_*`)
  - transações (`pg_transacao_*`, `pg_tx_*`)
  - migrações idempotentes e seed (`migracao_aplicar`, `seed_aplicar`)
  - aliases oficiais em pt-BR (`banco_*`, `consulta_*`, `modelo_*`, `transacao_*`, `semente_aplicar`)
- v0.7 completa:
  - autenticação JWT nativa (`jwt_criar`/`jwt_verificar`)
  - hash/validação de senha (`senha_hash`/`senha_verificar`) com suporte a pbkdf2 e opcional bcrypt/argon2
  - RBAC com papéis, herança e permissões (`rbac_*` + aliases pt-BR)
- v0.8 completa:
  - logs estruturados (`log_estruturado`, `log_estruturado_json`)
  - métricas (contador/histograma) com snapshot (`metrica_*`, `metricas_snapshot`)
  - tracing inicial com spans/eventos (`traco_*`, `tracos_snapshot`)
- v0.9 completa:
  - test runner oficial para `.trm` (`trama testar`)
  - lint/format/cobertura para `.trm` (`trama lint`, `trama formatar`, `trama cobertura`)
  - gerador de template backend (`trama template-backend`)
- v1.0.5 em andamento (auto-hospedagem):
  - compilador self-host em `.trm` (`selfhost/compilador/mod.trm`)
  - `trama compilar` operando via pipeline self-host por padrão
  - verificação automática de paridade (`trama paridade-selfhost`)

### Em andamento

- hardening de runtime e ergonomia para backend (preparação de v1.0)

### Falta fazer (próximos passos)

- fechamento das lacunas de backend complexo para v1.0+
- publicação do repositório APT em servidor (infra externa + domínio + GPG real)

## Lacunas Para Paridade Backend Complexo

Pontos que ainda faltam para substituir integralmente backends grandes em produção:

- roteamento HTTP com handlers dinâmicos por função (request/response completos)
- roteamento HTTP com handlers dinâmicos por função (`requisicao/resposta` completos)
- cadeia real de middlewares (auth, validação, rate-limit, erro global)
- uploads multipart/form-data e processamento de imagem
- realtime nativo (WebSocket/Socket.IO), salas, presença e eventos
- jobs e filas para tarefas assíncronas de longa duração
- cache robusto com TTL/invalidação e estratégia para múltiplas instâncias
- observabilidade de produção (métricas HTTP/DB, tracing por requisição, logs correlacionados)
- hardening operacional (`encerramento_gracioso`, `saude/pronto/vivo`, limites, timeout, retries)
- testes de integração/e2e/carga para cenários de concorrência alta

## Plano de Paridade Backend (v1.0 -> v1.5)

Ordem de implementação para alcançar backend robusto:

1. Runtime HTTP programável (`requisicao/resposta`, handlers e middleware chain)
2. Segurança de borda (auth middleware, RBAC por rota, rate-limit por política)
3. Persistência avançada (query builder/ORM evoluídos, migrações versionadas, pool tuning)
4. Realtime (WebSocket), notificações, presença e eventos
5. Arquivos e mídia (upload multipart, storage local/S3-like, processamento assíncrono)
6. Operação de produção (observabilidade completa, resiliência, deploy e runbooks)
7. Testes e qualidade (integração, e2e, carga/soak, contrato de API)

## Estrutura do Repositório

```text
trama/
  docs/
  selfhost/
  src/trama/
  tests/
  exemplos/
```

## Primeira Fase (MVP)

Escopo inicial da linguagem:

- variáveis
- números e texto
- operações aritméticas e comparações
- `se/senão`
- `enquanto`
- funções e `retorne`
- builtin `exibir`
- CLI funcional (`trama executar`, `trama bytecode`, `trama compilar`)
- pacote Python instalável
- binário standalone obrigatório (sem dependência de Python no alvo)
- pacote Debian (`.deb`)
- instalação via APT (repositório oficial do projeto)

Fora do escopo do MVP:

- classes
- concorrência
- sistema de tipos estático
- exceções avançadas

## Plano de Execução Imediato

1. Melhorar mensagens de erro com contexto de arquivo/linha no runtime.
2. Adicionar mais biblioteca padrão voltada a backend.
3. Criar pipeline CI para build de standalone e `.deb`.
4. Publicar repositório APT assinado.

## Setup de Desenvolvimento

Pré-requisito: Python 3.11+

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

Para desenvolvimento com PostgreSQL nativo:

```bash
pip install -e .[dev,db]
```

Validação rápida sem pytest:

```bash
make check
make run-example
```

## Comandos da CLI (fase inicial)

```bash
trama executar arquivo.trm
trama compilar arquivo.trm -o arquivo.tbc
trama compilar-legado arquivo.trm -o arquivo.tbc
trama semente-compilar arquivo.trm -o arquivo.tbc
trama autocompilar arquivo.trm -o arquivo.tbc
trama paridade-selfhost arquivo.trm
trama executar-tbc arquivo.tbc
trama bytecode arquivo.trm
trama testar [alvo]
trama lint [alvo]
trama formatar [alvo] [--aplicar]
trama cobertura [alvo]
trama template-backend <destino>
trama repl
```

## Distribuição (atual: v0.9)

Build do binário standalone (obrigatório):

```bash
scripts/build_standalone.sh
./dist/trama executar exemplos/ola_mundo.trm
```

Build do pacote Debian:

```bash
scripts/package_deb.sh 1.0.0 amd64
sudo apt install ./build/trama_1.0.0_amd64.deb
```

Pipeline completo de release self-host:

```bash
scripts/build_release_selfhost.sh 1.0.0 amd64
```

Preparar repositório APT:

```bash
scripts/init_apt_repo.sh packaging/apt-repo stable main trama <SEU_GPG_KEY_ID>
scripts/publish_apt_package.sh packaging/apt-repo stable ./build/trama_0.9.0_amd64.deb
```

## Entrega da v0.1

A `v0.1` é considerada pronta quando cumprir:

- execução fim a fim da linguagem (lexer, parser, compilador, VM)
- CLI funcional para executar e inspecionar bytecode
- pacote Python instalável
- binário standalone obrigatório
- pacote Debian (`.deb`) instalável localmente
- publicação em repositório APT assinado para permitir `apt install trama`

## Roadmap Versionado

Atualize os itens `[ ]` para `[x]` conforme cada entrega for concluída.

### v0.1 (concluída)
- [x] lexer, parser, AST, semântica mínima, compilador e VM
- [x] CLI funcional (`executar`, `bytecode`, `compilar`)
- [x] distribuição inicial (binário standalone + `.deb`)

### v0.2 (concluída)
- [x] exceções reais (`tente/pegue/finalmente`)
- [x] módulos/imports estáveis
- [x] escopos/closures sólidos
- [x] coleções nativas e JSON

### v0.3 (concluída)
- [x] runtime assíncrono oficial
- [x] `assíncrona/aguarde` (`async/await` em pt-BR), tarefas, timeout e cancelamento
- [x] I/O não bloqueante

### v0.4 (concluída)
- [x] stdlib backend mínima (HTTP client, FS, ENV, TIME, LOG)
- [x] serialização JSON robusta
- [x] configuração por ambiente

### v0.5 (concluída)
- [x] servidor web nativo
- [x] roteamento, middlewares, CORS, `requisicao/resposta`
- [x] validação de payload e erros padronizados
- [x] healthcheck e serving de estáticos

### v0.6 (concluída)
- [x] driver PostgreSQL async + query builder/ORM inicial
- [x] transações
- [x] migrações idempotentes + seed

### v0.7 (concluída)
- [x] JWT + hash de senha (bcrypt/argon2)
- [x] autorização por papéis (RBAC)

### v0.8 (concluída)
- [x] logs estruturados
- [x] métricas e tracing inicial
- [x] práticas de operação para produção

### v0.9 (concluída)
- [x] test runner oficial
- [x] cobertura, lint/format
- [x] templates de projeto backend

### v1.0 (concluída)
- [x] runtime HTTP programável: handlers dinâmicos por rota (`requisicao/resposta` completos)
- [x] middleware chain real (pré/pós), erro global e validação por esquema
- [x] segurança por rota (JWT/RBAC), rate-limit configurável e proteção de abuso
- [x] APIs versionadas e contratos de resposta estáveis (com validação de contrato por rota)
- [x] jobs e webhooks com retries, timeout, idempotência e DLQ básica
- [x] persistência sólida: transações, migração versionada e evolução de esquema segura (lock + dry-run + compatibilidade)
- [x] testes de integração e carga com metas mínimas de desempenho/estabilidade
- [x] guia de auto-hospedagem e operação (SLO, monitoramento, backup/restore)

### v1.0.5 (auto-hospedagem do compilador)
- [x] compilador principal em `.trm` (`selfhost/compilador/mod.trm`)
- [x] pipeline oficial de build compilando componentes centrais a partir de código `.trm` (`scripts/build_selfhost.sh`)
- [x] `trama compilar` migrado para pipeline self-host (`compilar-legado` mantido para compatibilidade transitória)
- [x] suíte de equivalência garantindo paridade entre implementação antiga e self-hosted (`trama paridade-selfhost`)
- [x] compilador semente mínimo para bootstrap de futuras versões (`trama semente-compilar`)
- [x] execução de bytecode `.tbc` sem compilador no runtime (`trama executar-tbc`)
- [ ] release oficial marcada como “Trama compilando Trama”

### v1.1 (concluída)
- [x] cache de aplicação completo (TTL, invalidação por chave/padrão, warmup)
- [x] circuit breaker/retry/backoff para integrações externas
- [x] configuração avançada por ambiente e segredos

### v1.2 (concluída)
- [x] uploads multipart/form-data
- [x] pipeline de mídia (redimensionamento/conversão/compressão)
- [x] abstração de storage (local e provedor remoto tipo S3)

### v1.3 (concluída)
- [x] WebSocket nativo com autenticação JWT
- [x] salas/canais, presença, typing/read-receipt e broadcast seletivo
- [x] fallback de transporte e limites de conexão

### v1.4 (concluída)
- [x] observabilidade avançada (métricas HTTP/DB/runtime, tracing por requisição)
- [x] logs estruturados com correlação (`id_requisicao`, `id_traco`, `id_usuario` + aliases `request_id`, `trace_id`, `user_id`)
- [x] dashboard operacional mínimo e alertas iniciais

## Plano Técnico v1.1 (robusto)

Ordem de implementação adotada:

1. configuração/segredos;
2. cache com TTL/invalidação/warmup;
3. resiliência com retry/backoff/timeout/circuit breaker;
4. integração no runtime da linguagem via builtins pt-BR;
5. testes unitários e integração via programas `.trm`.

Critérios de aceite (DoD):

- API canônica em pt-BR com aliases de compatibilidade transitórios;
- validação de configuração por obrigatórios + schema de tipos;
- segredos com leitura segura e mascaramento em logs;
- cache com namespaces, estatísticas de hit/miss/expiração;
- resiliência com estado de circuito (`fechado`, `aberto`, `meio_aberto`);
- testes automatizados cobrindo sucesso, falha, timeout e recuperação;
- documentação atualizada no roadmap/checklist.

## Plano Técnico v1.2 (robusto)

Ordem de implementação adotada:

1. parsing multipart/form-data no runtime HTTP com validação por schema;
2. pipeline de mídia com compressão gzip e processamento de imagem (quando Pillow disponível);
3. camada de storage abstrata com backend local e backend S3-compatível;
4. integração total via builtins canônicos pt-BR;
5. testes unitários e integração HTTP multipart.

Critérios de aceite (DoD):

- `requisicao` expõe `formulario` e `arquivos` para handlers;
- schema suporta `form_obrigatorio` e `arquivos_obrigatorios`;
- storage local bloqueia path traversal e suporta put/get/list/delete/url;
- storage S3-compatível com upload/download/list/delete e URL assinada;
- pipeline de mídia com gzip e hash; operações de imagem com erro controlado sem dependência opcional;
- testes automatizados cobrindo upload multipart, storage e mídia;
- documentação de versão atualizada.

## Plano Técnico v1.4 (robusto)

Ordem de implementação adotada:

1. correlação canônica (`id_requisicao`, `id_traco`, `id_usuario`) com aliases de compatibilidade;
2. instrumentação HTTP (métricas e tracing por requisição);
3. instrumentação DB e runtime (cache/resiliência/jobs/webhooks);
4. dashboard operacional (`/observabilidade`) e endpoint de alertas (`/alertas`);
5. testes unitários e integração comprovando correlação e observabilidade fim a fim.

Critérios de aceite (DoD):

- logs estruturados com correlação automática por contexto de requisição;
- headers de correlação canônicos + aliases (`X-Id-Requisicao`/`X-Request-Id`, `X-Id-Traco`/`X-Trace-Id`);
- métricas HTTP/DB/runtime disponíveis em snapshot;
- tracing por requisição com span raiz e evento de resposta;
- alertas iniciais por taxa de erro e latência (configuráveis);
- testes automatizados cobrindo IDs canônicos e aliases sem regressão funcional.

## Plano de Implementação v1.0 (Completo e Robusto)

Objetivo: entregar backend de produção em `trama` com arquitetura previsível, segurança forte, testes reais e operação confiável.

Regra obrigatória deste plano: toda superfície de linguagem deve ser canônica em pt-BR.
- nomes de API/sintaxe em português como padrão oficial;
- aliases em inglês somente para compatibilidade, nunca como forma principal;
- documentação e exemplos sempre primeiro em pt-BR.

### Fase 1 - Runtime HTTP programável

1. Definir objetos nativos canônicos `requisicao` e `resposta`:
- `requisicao`: método, caminho, consulta, parametros, cabecalhos, corpo, ip, contexto.
- `resposta`: status, cabecalhos, json, texto, bytes, redirecionar, fluxo.
2. Implementar roteador com:
- parâmetros de rota (`/usuarios/:id`), match determinístico e precedência estável.
- composição por método (`GET/POST/PUT/PATCH/DELETE/OPTIONS`).
3. Implementar handlers dinâmicos:
- `web_rota(app, metodo, caminho, funcao_handler)`.
- suporte async completo com cancelamento por timeout.
4. Critério de aceite:
- suíte de integração cobrindo 2xx/4xx/5xx, params/query/body, erros de parser e CORS.

### Fase 2 - Middleware chain e validação por esquema

1. Middleware pré e pós-handler:
- cadeia com ordem explícita e short-circuit seguro.
2. Handler global de erro:
- erro padronizado com código, mensagem, detalhes e `request_id`.
3. Validação por esquema:
- esquema declarativo para `parametros/consulta/corpo`.
- mensagens de erro consistentes e localizadas.
4. Critério de aceite:
- testes de contrato de erro para cada categoria (validação, auth, rate-limit, interno).

### Fase 3 - Segurança por rota

1. Middleware `autenticar_jwt`.
2. Middleware `autorizar_permissoes` (RBAC por rota e método).
3. Rate-limit por política:
- por IP, por usuário e por rota sensível.
4. Proteção de abuso:
- limite de payload, limite de conexões e proteção básica de brute-force.
5. Critério de aceite:
- testes de segurança negativos e positivos com casos de bypass.

### Fase 4 - APIs versionadas e contratos estáveis

1. Namespace de versão (`/api/v1`, `/api/v2`).
2. Contratos de resposta:
- envelope canônico (`ok`, `dados`, `erro`, `meta`).
3. Compatibilidade:
- política de depreciação e changelog de contratos.
4. Critério de aceite:
- testes de snapshot/contrato por rota crítica.

### Fase 5 - Jobs e webhooks

1. Fila de jobs nativa:
- enfileirar, agendar, retry com backoff, timeout por job.
2. Idempotência:
- chave idempotente para evitar processamento duplicado.
3. DLQ (dead-letter queue) básica:
- jobs falhos persistidos para reprocessamento.
4. Webhooks:
- assinatura HMAC, retry, deduplicação e observabilidade.
5. Critério de aceite:
- testes de concorrência e falha controlada (rede/timeout/exceção).

### Fase 6 - Persistência sólida

1. Migrações versionadas:
- `subir/descer`, histórico, lock de migração e rollback seguro.
2. Evolução de schema:
- check de compatibilidade e dry-run.
3. Transações avançadas:
- savepoints e rollback parcial quando suportado.
4. Critério de aceite:
- testes de migração em banco vazio, banco legado e rollback forçado.

### Fase 7 - Qualidade e desempenho

1. Testes obrigatórios:
- unitários, integração HTTP, integração DB, e2e e carga.
2. Metas mínimas de estabilidade:
- sem regressão funcional em suíte completa.
- erro não tratado igual a zero em cenários de integração.
3. Metas mínimas de performance (baseline):
- registrar p50/p95/p99 por rota crítica.
4. Critério de aceite:
- pipeline CI bloqueia merge sem cobertura e sem testes de integração.

### Fase 8 - Operação e auto-hospedagem

1. Guia operacional:
- deploy, rollback, backup/restore, rotação de segredos.
2. SLO/SLI:
- disponibilidade, latência, taxa de erro.
3. Saúde de serviço:
- endpoints canônicos `saude`, `pronto`, `vivo` (com compatibilidade para `health/readiness/liveness`).
4. Runbooks:
- incidentes comuns, banco indisponível, saturação e degradação.
5. Critério de aceite:
- ambiente de staging com ensaio de falha e recuperação validado.

## Regras de Execução (linguagem séria)

- nenhuma feature entra sem teste de integração.
- toda mudança de contrato HTTP exige teste de contrato.
- toda migração exige plano de rollback.
- toda entrega operacional exige documentação atualizada.
- checklist de release obrigatório antes de marcar item como concluído.
- toda API nova deve ter nome canônico em pt-BR e exemplos oficiais em pt-BR.

## v1.5–v1.8 (paridade backend avançada)
- [x] REST + realtime (Socket.IO/WebSocket) com autenticação JWT
- [x] mensagens em tempo real, eventos sociais e alertas
- [x] comunidades/guildas com moderação e permissões
- [x] APIs administrativas + campanhas de push + métricas
- [x] upload de mídia + persistência + cache offline/sync incremental
- [x] deploy completo (Docker, `.deb`, standalone) com observabilidade robusta

### Entregas v1.5

- realtime avançado em `web_runtime` com:
  - `ack/nack`, `retry`, reenvio e `id_mensagem`/ordenação por canal.
  - compatibilidade Socket.IO mínima (`42["evento",{...}]`) sem quebrar WebSocket nativo.
  - autenticação JWT no handshake e por rota de tempo real.
- builtins canônicos pt-BR:
  - `web_tempo_real_publicar`, `web_tempo_real_confirmar_ack`, `web_tempo_real_reenviar_pendentes`.
  - aliases de compatibilidade: `web_realtime_publicar`, `web_realtime_confirmar_ack`, `web_realtime_reenviar_pendentes`.

### Entregas v1.6

- domínio social completo em pt-BR:
  - comunidades, canais, cargos, membros e checagem de permissões.
  - moderação: `reportar`, `banir`, `mutar`, `expulsar`, `soft_delete`.
- builtins canônicos:
  - `comunidade_criar`, `comunidade_obter`, `comunidade_listar`, `canal_criar`, `cargo_criar`, `membro_entrar`, `membro_sair`, `membro_atribuir_cargo`, `comunidade_permissao_tem`, `moderacao_acao`, `moderacao_listar`.

### Entregas v1.7

- APIs administrativas e campanhas:
  - trilha de auditoria administrativa.
  - campanhas push com criação, agendamento, execução, status e listagem.
- métricas operacionais:
  - emissão de métricas de runtime para eventos administrativos e campanhas.
- builtins canônicos:
  - `admin_auditoria_registrar`, `admin_auditoria_listar`, `campanha_criar`, `campanha_agendar`, `campanha_executar`, `campanha_status`, `campanha_listar`.

### Entregas v1.8

- upload/persistência/mídia:
  - integração com storage local/S3 compatível e pipeline de mídia.
- cache offline + sync incremental:
  - `sync_registrar_evento`, `sync_consumir`, `sync_cursor_atual`, `sync_resolver_conflito`.
  - `cache_offline_salvar`, `cache_offline_obter`, `cache_offline_listar`.
- deploy e operação:
  - `Dockerfile`, `docker-compose.yml`, `scripts/healthcheck_http.sh`, `scripts/smoke_deploy.sh`.
  - pipeline existente de standalone + `.deb` mantido.

## v2.0 (autossuficiência total da linguagem)
- [x] fase 1: especificar formato canônico de bytecode e ABI da VM (`bytecode_v1`) com versionamento estável
- [x] fase 2: implementar runtime/VM nativa robusta (backend nativo) para executar `.tbc` sem Python
- [x] fase 3: portar compilador oficial para `.trm` com bootstrap por compilador semente mínimo
- [x] fase 4: remover Python do caminho crítico de build/release e publicar release oficial sem dependência de Python

Status oficial da versão:

- v2.0 considerada concluída para uso de produto.

Resumo consolidado da implementação:

- fase 1 concluída (especificação formal + validação):
  - `docs/BYTECODE_V1.md`
  - `docs/ABI_VM_V1.md`
  - `docs/MATRIZ_COBERTURA_BYTECODE_ABI_V1.md`
- testes de conformidade da fase 1:
  - `tests/test_bytecode_v1_conformance.py`
  - cobertura de shape, roundtrip, payload inválido e opcode inválido
- base da fase 2 iniciada com stub nativo e suíte local:
  - `native/runtime_stub.c`
  - `native/trama_native.c` (VM nativa com `executar-tbc`, exceções, await sequencial e import `.tbc`)
  - `scripts/build_native_stub.sh`
  - `.local/tests/v2_0_native/run_local_v20_native.sh`
- fase 2.A (auditoria) concluída:
  - matriz real de opcodes/recursos suportados vs ausentes em `docs/V2_FASE2_PARIDADE_VM_NATIVA.md`
- contratos canônicos para a próxima etapa da VM/CLI nativa:
  - `docs/CLI_NATIVA_V2_CONTRATOS.md`
  - comandos oficiais pt-BR: `executar`, `compilar`, `executar-tbc`
  - aliases em inglês apenas para compatibilidade
- diagnóstico explícito no CLI atual (canônico + compatibilidade):
  - `trama --diagnostico-runtime`
- diagnóstico equivalente no runtime nativo:
  - `trama-native --diagnostico-runtime`
- compatibilidade de aliases na CLI nativa:
  - `run-tbc` (alias de `executar-tbc`)
- suporte adicional na CLI nativa:
  - `executar` e `compilar` disponíveis por ponte de compatibilidade via standalone (`trama`)
- suíte expandida de testes nativos:
  - `tests/test_native_runtime_v20.py`
  - `.local/tests/v2_0_fase2/run_local_v20_fase2.sh`

Critérios de aceite da fase 1 (DoD):

- especificação formal de `bytecode_v1` publicada.
- ABI da VM v1 publicada.
- matriz de cobertura recurso -> bytecode/ABI publicada.
- testes de conformidade com casos positivos e negativos.
- regressão global sem quebra da suíte existente.

Roadmap técnico pós-v2.0 (sem data definida):

Para o plano detalhado e versionado dos 7 eixos críticos (incluindo evolução da linguagem para codebase grande com `para/em`, módulos e tipagem gradual), consulte:

- [`docs/ROADMAP_IMPLEMENTACOES_FUTURAS_V2_1.md`](docs/ROADMAP_IMPLEMENTACOES_FUTURAS_V2_1.md)

### v2.0.1 - ORM e migrações nível produção
- [x] relações completas (1:1, 1:N, N:N), preload/eager/lazy e paginação robusta.
- [x] constraints avançadas (única composta, FKs complexas, checks) com validação consistente.
- [x] diff de schema confiável com preview antes de aplicar.
- [x] rollback seguro com trilha de execução de migrações.
- [x] seeds determinísticas por ambiente (`dev`, `teste`, `prod`).
- [x] testes de migração em banco vazio e banco legado.

DoD v2.0.1:
- pipeline de migração idempotente.
- rollback validado em cenários reais.
- documentação de operação de banco atualizada.

Entregas implementadas em v2.0.1:
- `db_runtime` com:
  - `orm_modelo`, relações `orm_relacao_um_para_um`, `orm_relacao_um_para_muitos`, `orm_relacao_muitos_para_muitos`;
  - `orm_listar` com preload/eager/lazy e paginação (`pagina`, `limite`, `ordenacao`, `cursor`);
  - constraints de schema (`schema_constraint_unica`, `schema_constraint_fk`, `schema_constraint_check`);
  - diff/preview/aplicação de schema (`schema_inspecionar`, `schema_diff`, `schema_preview_plano`, `schema_aplicar_diff`);
  - trilha de migração (`migracao_aplicar_versionada_v2`, `migracao_trilha_listar`);
  - seeds por ambiente (`seed_aplicar_ambiente`).
- superfície canônica em `builtins` e `semantic` para uso direto em `.trm`.
- testes:
  - `tests/test_db_runtime.py` (cobertura unitária de v2.0.1);
  - `tests/test_vm.py` (fluxo de integração VM em banco vazio/legado);
  - suíte local `.local/tests/v2_0_1_db_orm/run_local_v201.sh`.

### v2.0.2 - DTO/validação e contrato de API
- [x] camada de DTOs declarativos em pt-BR com validação profunda.
- [x] transformação e coerção de tipos de entrada.
- [x] sanitização automática de payload.
- [x] erros padronizados por campo (`codigo`, `campo`, `mensagem`, `detalhes`).
- [x] versionamento de contrato HTTP e compatibilidade retroativa.
- [x] geração de exemplos de payload válidos/inválidos para testes.

DoD v2.0.2:
- validação uniforme em toda API.
- erros de domínio/validação previsíveis e estáveis.
- documentação de contrato publicada.

Entregas implementadas em v2.0.2:
- runtime HTTP (`web_runtime`) com:
  - DTO declarativo por rota (`dto_requisicao`) em `corpo/consulta/parametros/formulario`;
  - coerção de tipos (`coagir`) e sanitização (`sanitizar`) em campos de DTO;
  - validação profunda de objetos/listas aninhados com erros por campo (`codigo`, `campo`, `mensagem`, `detalhes`);
  - contrato de entrada para remoção de campos proibidos (`contrato_entrada.campos_permitidos`);
  - contrato de resposta versionado (`contrato_resposta.versoes`) com fallback retrocompatível (`retrocompativel`).
- superfície canônica em `builtins`/`semantic`:
  - `web_rota_dto`, `dto_validar`, `dto_gerar_exemplos` (+ alias `web_rota_com_dto`).
- testes:
  - `tests/test_web_runtime_v202.py` (DTO, sanitização/coerção e contrato versionado);
  - `tests/test_vm.py::test_v202_dto_contrato_versionado_em_vm` (integração fim a fim em `.trm`).
- documentação:
  - contrato e exemplos oficiais em `docs/LINGUAGEM_V2_0_2.md`.

### v2.0.3 - Realtime distribuído em escala
- [ ] presença/salas com sincronização entre múltiplas instâncias.
- [ ] backplane pub/sub (ex.: Redis) para broadcast distribuído.
- [ ] ack/nack/retry/reenvio com garantia de ordenação por canal.
- [ ] reconexão com recuperação de estado recente por cursor.
- [ ] limites por conexão/usuário/sala com proteção de abuso.
- [ ] testes de concorrência e múltiplas instâncias.

DoD v2.0.3:
- realtime estável em ambiente com mais de uma instância.
- métricas de entrega e reconexão auditáveis.

### v2.0.4 - Cache distribuído e coerência
- [ ] cache distribuído com TTL/invalidação por chave e por padrão.
- [ ] estratégia cache-aside/read-through para consultas críticas.
- [ ] sincronização de invalidação entre instâncias.
- [ ] proteção contra stampede (lock/coalescing).
- [ ] fallback seguro quando cache indisponível.
- [ ] métricas de hit ratio, latência e invalidação.

DoD v2.0.4:
- cache consistente entre nós.
- sem regressão de integridade de dados com cache ativo.

### v2.0.5 - Segurança de produção
- [ ] refresh token rotation e revogação por sessão/dispositivo.
- [ ] listas de bloqueio e invalidação de tokens.
- [ ] rate-limit distribuído por rota/IP/usuário.
- [ ] hardening HTTP (headers de segurança, CORS estrito por ambiente).
- [ ] trilha de auditoria para ações administrativas sensíveis.
- [ ] suíte de testes de segurança (authz/authn e abuso).

DoD v2.0.5:
- fluxo de autenticação completo para produção.
- controles de abuso e revogação validados.

### v2.0.6 - Tooling de backend maduro
- [ ] OpenAPI/Swagger gerado a partir do contrato da aplicação.
- [ ] geração de cliente (SDK) para consumo de API.
- [ ] CLI de administração (usuários, permissões, jobs, manutenção).
- [ ] comandos de migração/seed/diagnóstico padronizados.
- [ ] templates de serviço e módulo para acelerar novos projetos.
- [ ] documentação operacional de comando a comando.

DoD v2.0.6:
- onboarding técnico previsível.
- fluxo de desenvolvimento/admin padronizado.

### v2.0.7 - Observabilidade e SRE
- [ ] exportadores padrão (OpenTelemetry/Prometheus compatível).
- [ ] correlação completa de logs, métricas e traces.
- [ ] dashboards operacionais prontos (API, DB, realtime, jobs).
- [ ] alertas iniciais (erro, latência, saturação, fila).
- [ ] runbooks de incidentes e procedimentos de recuperação.
- [ ] smoke checks e health checks de produção.

DoD v2.0.7:
- operação observável ponta a ponta.
- alertas e runbooks prontos para produção.

### v2.0.8 - Testes avançados (integração/e2e/carga)
- [ ] harness de integração com fixtures reais de banco.
- [ ] suíte e2e para fluxos críticos de negócio.
- [ ] testes de carga e concorrência com metas de SLO.
- [ ] testes de regressão de contrato de API.
- [ ] testes de caos/falha parcial (rede, DB, cache).
- [ ] relatórios automáticos de estabilidade e performance.

DoD v2.0.8:
- cobertura de cenários críticos de produção.
- baseline de performance reproduzível.

### v2.0.9 - Runtime 100% nativo (fechamento do ciclo)
- [ ] remover ponte de compatibilidade em `executar` e `compilar`.
- [ ] compilador oficial nativo de `.trm` para `.tbc`.
- [ ] import nativo direto de módulos `.trm`.
- [ ] async avançado com scheduler concorrente completo.
- [ ] otimizações de memória/CPU da VM nativa.
- [ ] release `.deb` e standalone com diagnóstico de backend 100% nativo.

DoD v2.0.9:
- uso da linguagem sem dependência de runtime externo no caminho crítico.
- paridade funcional consolidada no backend nativo.

### v2.1.0 - Engenharia de produto (CI/CD e governança)
- [ ] pipeline oficial de CI (build, testes, lint, cobertura e segurança) obrigatório para merge.
- [ ] portões de qualidade com bloqueio de regressão crítica em PR.
- [ ] esteira de release automatizada para `standalone`, `.deb` e artefatos versionados.
- [ ] versionamento semântico e changelog por versão com política de compatibilidade.
- [ ] guia formal de contribuição, manutenção e resposta a incidentes.
- [ ] documentação de migração para mudanças potencialmente quebráveis.

DoD v2.1.0:
- merges protegidos por qualidade mínima obrigatória.
- releases reproduzíveis e auditáveis.
- governança de evolução publicada e aplicada.

### v2.1.1 - Linguagem para codebase grande
- [ ] implementação completa de `para/em` em parser, AST, compilador e VM (Python + nativa).
- [ ] contratos de módulo com exportação/importação explícitas e espaços de nomes previsíveis.
- [ ] resolução determinística de módulos para projetos multi-pacote.
- [ ] tipagem gradual fase 1 (anotações opcionais e checagem estática básica).
- [ ] tipagem gradual fase 2 (tipos compostos, fronteira de API e validação entre módulos).
- [ ] diagnósticos semânticos com contexto consistente (arquivo, linha, coluna e sugestão de correção).

DoD v2.1.1:
- manutenção de base grande com contratos explícitos e menor risco de refatoração.
- redução mensurável de erros de runtime em fluxos cobertos por tipagem.
- paridade de linguagem consolidada entre execução Python e nativa para recursos novos.

## v2.5 (frontend)
- [ ] toolkit de UI, estado e renderização
- [ ] integração HTML/CSS/DOM (ou runtime equivalente)
- [ ] roteamento SPA + build + hot reload
- [ ] integração full-stack com backend em `trama`
- [ ] backend em `trama` apto para substituir aplicações complexas com realtime + mídia + observabilidade

## Princípios Técnicos

- simplicidade primeiro
- gramática pequena e sem ambiguidades
- testes desde o lexer
- compatibilidade com evolução para backend real
- documentação de linguagem obrigatória: cada versão deve criar/atualizar o manual da linguagem

## Licença

MIT (livre e permissiva).
