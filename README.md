# trama

A `trama` é uma linguagem de programação **canonicamente pt-BR** para backend e aplicações gerais, com compilação para bytecode próprio (`.tbc`) e execução em VM própria.

## Visão Rápida

- [x] linguagem oficial em pt-BR (lexer, parser, semântica, compilador, VM, builtins, runtimes, CLI, docs e exemplos)
- [x] pipeline completo de linguagem (`.trm -> lexer -> parser -> AST -> semântica -> compilador -> bytecode -> VM`)
- [x] runtime nativo com execução/compilação sem Python no caminho crítico
- [x] distribuição em `standalone` e `.deb`
- [x] suíte avançada de testes e gates de CI para merge
- [ ] release oficial marcada como "Trama compilando Trama" (pendente histórico da v1.0.5)

## Identidade Canônica pt-BR

A forma oficial da linguagem é pt-BR.

Regras oficiais:
- [x] palavras-chave oficiais em português
- [x] equivalência com/sem acento (`função/funcao`, `senão/senao`, `assíncrona/assincrona`)
- [x] keywords case-insensitive
- [x] identificadores canônicos em `snake_case`, sem acento e sem hífen
- [x] aliases em inglês apenas para compatibilidade retroativa

Palavras-chave canônicas:
- `função`, `retorne`, `se`, `senão`, `enquanto`, `para`, `em`
- `verdadeiro`, `falso`, `nulo`, `fim`, `pare`, `continue`
- `tente`, `pegue`, `finalmente`, `lance`, `importe`, `como`
- `assíncrona`, `aguarde`

## Estado Atual (Resumo)

### Núcleo da linguagem
- [x] lexer, parser, AST, semântica, compilador e VM
- [x] exceções reais, módulos/import, closures, coleções, JSON
- [x] async/await canônico pt-BR com tarefas/timeout/cancelamento
- [x] tipagem gradual (v2.1.1) e diagnósticos estáveis com arquivo/linha/coluna/sugestão

### Backend e runtime
- [x] servidor HTTP com rotas, middlewares, CORS, validação e contratos
- [x] banco (SQLite/PostgreSQL), ORM, migrações versionadas, seeds, diff/preview
- [x] JWT/RBAC, sessão/refresh rotation, denylist e hardening
- [x] realtime distribuído (ack/nack/retry/replay/cursor) e cache distribuído
- [x] observabilidade (logs/métricas/traces), dashboards, alertas e smoke checks

### Engenharia e operação
- [x] CLI robusta para linguagem, tooling e operação
- [x] CI/CD com gates obrigatórios e release auditável
- [x] documentação de governança, migração e operação
- [x] artefatos `standalone` + `.deb` + checksum

## Instalação e Uso

### Setup de desenvolvimento

Pré-requisito: Python 3.11+

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

Com PostgreSQL nativo:

```bash
pip install -e .[dev,db]
```

Validação rápida:

```bash
make check
make run-example
```

### Comandos principais da CLI

```bash
trama executar arquivo.trm
trama compilar arquivo.trm -o arquivo.tbc
trama executar-tbc arquivo.tbc
trama bytecode arquivo.trm
trama testar [alvo]
trama lint [alvo]
trama formatar [alvo] [--aplicar]
trama cobertura [alvo]
trama testes-avancados-v208 [--perfil rapido|completo] [--json]
trama testes-avancados-v212 [--perfil rapido|completo] [--json]
trama testes-avancados-v213 [--perfil rapido|completo] [--json]
```

### Build e distribuição

```bash
scripts/build_standalone.sh
scripts/package_deb.sh 2.1.3 amd64
scripts/build_release_nativo.sh 2.1.3 amd64
```

## Índice de Documentação

### Linguagem por versão
- `docs/LINGUAGEM_V0_1.md`
- `docs/LINGUAGEM_V0_2.md`
- `docs/LINGUAGEM_V0_3.md`
- `docs/LINGUAGEM_V0_4.md`
- `docs/LINGUAGEM_V0_5.md`
- `docs/LINGUAGEM_V0_6.md`
- `docs/LINGUAGEM_V0_7.md`
- `docs/LINGUAGEM_V0_8.md`
- `docs/LINGUAGEM_V0_9.md`
- `docs/LINGUAGEM_V1_1.md`
- `docs/LINGUAGEM_V1_2.md`
- `docs/LINGUAGEM_V1_3.md`
- `docs/LINGUAGEM_V1_4.md`
- `docs/LINGUAGEM_V1_5_V1_8.md`
- `docs/LINGUAGEM_V2_0.md`
- `docs/LINGUAGEM_V2_0_1.md`
- `docs/LINGUAGEM_V2_0_2.md`
- `docs/LINGUAGEM_V2_0_3.md`
- `docs/LINGUAGEM_V2_0_4.md`
- `docs/LINGUAGEM_V2_0_5.md`
- `docs/LINGUAGEM_V2_0_6.md`
- `docs/LINGUAGEM_V2_0_7.md`
- `docs/LINGUAGEM_V2_0_8.md`
- `docs/LINGUAGEM_V2_0_9.md`
- `docs/LINGUAGEM_V2_1_0.md`
- `docs/LINGUAGEM_V2_1_1.md`
- `docs/LINGUAGEM_V2_1_2.md`
- `docs/LINGUAGEM_V2_1_3.md`
- `docs/LINGUAGEM_V2_1_11.md`
- `docs/LINGUAGEM_V2_1_17.md`
- `docs/MANUAL_TRAMA_COMPLETO_V2_1_17.md`
- `docs/OPERACAO_V2_1_17_ENGINE_ASGI_DB_CAPACIDADES.md`
- `docs/REFERENCIA_CAPACIDADES_DB_V2_1_17.md`

### Manuais consolidados e operação
- `docs/MANUAL_TRAMA_COMPLETO_V2_1_3.md`
- `docs/MANUAL_TRAMA_COMPLETO_V2_1_11.md`
- `docs/OPERACAO_V2_1_3_SUBSTITUICAO_TOTAL.md`
- `docs/OPERACAO_V2_1_11_REALTIME_MODULAR.md`
- `docs/OPERACAO_V2_1_2_BACKEND_COMPLEXO.md`
- `docs/OPERACAO_CI_CD_RELEASE_V2_1_0.md`
- `docs/GOVERNANCA_CONTRIBUICAO_V2_1_0.md`
- `docs/MIGRACAO_BREAKING_CHANGES.md`
- `docs/POLITICA_VERSIONAMENTO_CHANGELOG.md`
- `CHANGELOG.md`
- `docs/ROADMAP_IMPLEMENTACOES_FUTURAS_V2_1.md`

### Especificações de bytecode/ABI
- `docs/BYTECODE_V1.md`
- `docs/ABI_VM_V1.md`
- `docs/MATRIZ_COBERTURA_BYTECODE_ABI_V1.md`
- `docs/CLI_NATIVA_V2_CONTRATOS.md`
- `docs/V2_FASE2_PARIDADE_VM_NATIVA.md`

## Índice de Exemplos

- `exemplos/v20/`
- `exemplos/v201/`
- `exemplos/v202/`
- `exemplos/v203/`
- `exemplos/v204/`
- `exemplos/v205/`
- `exemplos/v206/`
- `exemplos/v207/`
- `exemplos/v208/`
- `exemplos/v209/`
- `exemplos/v211/`
- `exemplos/v212/`
- `exemplos/v213/`
- `exemplos/v214/`
- `exemplos/v217/`

## Roadmap Versionado (Checklist)

### v0.1-v0.9
- [x] `v0.1` núcleo da linguagem + CLI + distribuição inicial
- [x] `v0.2` exceções, módulos/import, closures, coleções/JSON
- [x] `v0.3` runtime assíncrono e I/O não bloqueante
- [x] `v0.4` stdlib backend mínima e configuração por ambiente
- [x] `v0.5` servidor web nativo
- [x] `v0.6` DB/ORM inicial, transações, migração/seed
- [x] `v0.7` JWT + RBAC
- [x] `v0.8` observabilidade inicial
- [x] `v0.9` test runner, lint/format/cobertura, templates

### v1.0-v1.8
- [x] `v1.0` backend programável completo (HTTP/middleware/segurança/contratos/jobs/testes/operação)
- [x] `v1.1` cache + resiliência + config/segredos
- [x] `v1.2` multipart/mídia/storage
- [x] `v1.3` websocket/realtime com JWT/salas/presença
- [x] `v1.4` observabilidade avançada com correlação
- [x] `v1.5-v1.8` paridade backend avançada (realtime social/admin/campanhas/sync/deploy)

### v1.0.5 (auto-hospedagem)
- [x] compilador self-host em `.trm`
- [x] `trama compilar` por pipeline self-host
- [x] compilador semente e paridade self-host
- [x] execução `.tbc` sem compilador no runtime
- [ ] release oficial marcada como “Trama compilando Trama”

### v2.0 (autossuficiência)
- [x] bytecode/ABI v1 especificados e validados
- [x] VM nativa robusta para `.tbc`
- [x] compilação oficial para `.trm/.tbc`
- [x] Python fora do caminho crítico de build/release

### v2.0.1 - ORM e migrações
- [x] relações completas e paginação robusta
- [x] constraints avançadas e diff de schema
- [x] rollback seguro e trilha de migração
- [x] seeds determinísticas por ambiente
- [x] testes em banco vazio e legado

### v2.0.2 - DTO/validação/contrato HTTP
- [x] DTO declarativo com validação profunda
- [x] coerção/sanitização
- [x] envelope de erro estável por campo
- [x] contrato versionado com retrocompatibilidade
- [x] geração de exemplos válidos/inválidos

### v2.0.3 - Realtime distribuído
- [x] presença/salas multi-instância
- [x] backplane memória/redis
- [x] ack/nack/retry/reenvio ordenado
- [x] reconexão por cursor com replay
- [x] limites e proteção de abuso

### v2.0.4 - Cache distribuído
- [x] TTL + invalidação por chave/padrão
- [x] cache-aside/read-through
- [x] sincronização entre instâncias
- [x] proteção stampede (lock/coalescing)
- [x] fallback degradado e métricas

### v2.0.5 - Segurança de produção
- [x] refresh rotation + revogação por sessão/dispositivo/usuário
- [x] denylist com TTL e invalidação imediata
- [x] rate-limit distribuído por rota/IP/usuário
- [x] hardening HTTP + CORS estrito por ambiente
- [x] auditoria de ações sensíveis

### v2.0.6 - Tooling backend
- [x] OpenAPI/Swagger a partir de contrato
- [x] geração de SDK cliente
- [x] CLI administrativa e operacional
- [x] comandos padronizados de migração/seed/diagnóstico
- [x] templates de serviço/módulo

### v2.0.7 - Observabilidade e SRE
- [x] exportadores Prometheus/OTEL
- [x] correlação logs/métricas/traces
- [x] dashboards e runbooks iniciais
- [x] alertas de erro/latência/saturação
- [x] smoke/health checks de produção

### v2.0.8 - Testes avançados
- [x] harness de integração com fixtures reais
- [x] suíte e2e de fluxos críticos
- [x] carga/concorrência com metas SLO
- [x] regressão de contrato HTTP
- [x] caos/falha parcial e fallback controlado
- [x] relatório automático JSON/Markdown

### v2.0.9 - Runtime 100% nativo
- [x] `executar`/`compilar` nativos
- [x] compilador nativo `.trm -> .tbc`
- [x] import nativo de módulos `.trm`
- [x] scheduler async concorrente
- [x] otimizações VM nativa
- [x] release `standalone` + `.deb` com diagnóstico nativo

### v2.1.0 - Engenharia de produto
- [x] CI obrigatório para merge
- [x] gates de qualidade com bloqueio
- [x] release automatizado com artefatos versionados
- [x] semver + changelog + política de compatibilidade
- [x] governança/contribuição/incidentes documentados

### v2.1.1 - Linguagem para codebase grande
- [x] `para/em` completo (parser/AST/compilador/VM)
- [x] contratos de módulo explícitos (`exporte`/`importe ... expondo ...`)
- [x] resolução determinística de módulos multi-pacote
- [x] tipagem gradual fase 1 e fase 2
- [x] diagnósticos semânticos estáveis com contexto completo

### v2.1.2 - Prontidão backend complexo
- [x] suíte crítica oficial v2.1.2 com gate obrigatório
- [x] baseline reproduzível de carga/concorrência
- [x] caos/falha parcial com fallback seguro
- [x] segurança mínima forte + observabilidade auditável
- [x] release reproduzível com rollback documentado

### v2.1.3 - Substituição JS/TS por Trama nativa
- [x] superfície oficial integralmente canônica pt-BR (incluindo lexer/parser)
- [x] paridade funcional do backend ARLS em `.trm`
- [x] frontend SPA/PWA nativo (template + fluxo validado)
- [x] cadeia de dados nativa (migração/seed/diagnóstico)
- [x] execução/compilação 100% nativas no caminho crítico
- [x] regressão obrigatória de contrato/e2e/carga/caos via suíte v2.1.3

Evidências principais da v2.1.3:
- `trama testes-avancados-v213`
- `docs/TODO_V2_1_3_IMPLEMENTACAO_TOTAL.md`
- `docs/LINGUAGEM_V2_1_3.md`
- `exemplos/v213/` (pacote amplo + ARLS)

### v2.1.4+ - Evolução incremental da base ao topo
- [x] `v2.1.4` separar `web_runtime.py` em núcleo HTTP, modelo de rotas/DTO/contrato e engine legada baseada em `http.server`
- [x] `v2.1.5` introduzir interface de engine HTTP pluggável mantendo compatibilidade total da superfície atual
- [x] `v2.1.6` criar suíte de paridade entre engine legada e nova abstração HTTP com os testes `v202`
- [x] `v2.1.7` extrair `TempoRealHub` e o core de presença/salas/cursor/ack para módulo dedicado desacoplado do servidor HTTP
- [x] `v2.1.8` extrair transporte fallback HTTP de tempo real para módulo próprio, preservando replay/reconexão por cursor
- [x] `v2.1.9` extrair transporte WebSocket para módulo próprio com handshake, frames e fechamento isolados
- [x] `v2.1.10` formalizar interface de backplane de realtime com backend de memória como implementação de referência
- [x] `v2.1.11` endurecer o backend Redis de realtime com testes reais de integração multi-instância e sincronização
- [x] `v2.1.12` introduzir engine ASGI como backend HTTP de produção mantendo a engine legada como fallback compatível
- [x] `v2.1.13` adicionar shutdown gracioso, readiness/liveness e limites operacionais consistentes nas engines HTTP
- [x] `v2.1.14` separar dialeto SQL, conexão e ORM para que SQLite e PostgreSQL virem backends de primeira classe
- [x] `v2.1.15` ampliar a suíte de integração PostgreSQL real para cobrir transação, paginação, constraints, migração e seed
- [x] `v2.1.16` consolidar introspecção e diff de schema por dialeto com paridade real entre SQLite/PostgreSQL
- [x] `v2.1.17` formalizar camada de capability/capacidades por backend de banco para evitar comportamento implícito de SQLite
- [ ] `v2.1.18` dividir segurança em módulos de JWT, sessão, RBAC e políticas, preservando a API canônica existente
- [ ] `v2.1.19` adicionar suporte a JWT assimétrico (`RS256`) com chaves locais e `kid`
- [ ] `v2.1.20` adicionar suporte a JWK/JWKS com cache, rotação e validação de `iss`/`aud`
- [ ] `v2.1.21` introduzir base de autenticação federada/OIDC para consumo de provedores externos
- [ ] `v2.1.22` evoluir autorização de RBAC puro para políticas contextuais baseadas em ator/ação/recurso/contexto
- [ ] `v2.1.23` transformar jobs em fachada com backend pluggável, preservando o backend em memória atual para desenvolvimento
- [ ] `v2.1.24` adicionar backend persistente de jobs via SQL com retry, leasing, DLQ e reprocessamento
- [ ] `v2.1.25` criar worker standalone e comandos operacionais para filas, DLQ e reprocessamento
- [ ] `v2.1.26` adicionar backend Redis para jobs e concorrência distribuída controlada
- [ ] `v2.1.27` formalizar modelo de contrato/IR para HTTP, DTOs, erros, auth, exemplos e versionamento
- [ ] `v2.1.28` fazer OpenAPI consumir o IR formal em vez de depender diretamente das estruturas ad hoc do runtime
- [ ] `v2.1.29` fazer geração de SDK Python/TypeScript consumir o mesmo IR formal de contrato
- [ ] `v2.1.30` adicionar verificação automatizada de breaking changes em contrato entre versões
- [ ] `v2.1.31` evoluir storage para pipeline de upload com validação de MIME, tamanho, hash e promoção temporário->definitivo
- [ ] `v2.1.32` endurecer multipart/streaming para upload grande sem depender de payload inteiro em memória
- [ ] `v2.1.33` adicionar pipeline de mídia com transformação, variantes e metadados conectada ao storage
- [ ] `v2.1.34` formalizar políticas de lifecycle, URL assinada, retenção e visibilidade por backend de storage
- [ ] `v2.1.35` ampliar observabilidade com propagação W3C (`traceparent`), métricas por engine e tracing mais formal
- [ ] `v2.1.36` integrar circuit breaker, timeouts globais, pools configuráveis e diagnóstico operacional por ambiente
- [ ] `v2.1.37` fechar a plataforma backend de produção com benchmark, suíte de carga multi-processo e critérios SLO oficiais
- [ ] `v2.1.38` consolidar documentação final da arquitetura modular de produção e a matriz oficial de capacidades por camada

### v2.5 (frontend futuro)
- [ ] toolkit de UI, estado e renderização
- [ ] integração HTML/CSS/DOM (ou runtime equivalente)
- [ ] roteamento SPA + build + hot reload
- [ ] integração full-stack com backend em `trama`
- [ ] backend em `trama` apto para substituir aplicações complexas com realtime + mídia + observabilidade

## Regras de Execução do Projeto

- [x] nenhuma feature entra sem teste de integração
- [x] mudança de contrato HTTP exige teste de contrato
- [x] migração exige plano de rollback
- [x] entrega operacional exige documentação atualizada
- [x] APIs novas em forma canônica pt-BR com exemplos oficiais pt-BR

## Estrutura do Repositório

```text
trama/
  docs/
  selfhost/
  src/trama/
  tests/
  exemplos/
```

## Princípios Técnicos

- simplicidade primeiro
- gramática pequena e sem ambiguidades
- testes desde o lexer
- compatibilidade com evolução para backend real
- documentação obrigatória por versão

## Licença

MIT.
