# TASK - Evoluir a linguagem Trama para substituir 100% JS/TS do ARLS_AMM (sem Python)

## 0. Status Atual (v2.1.3)

Entregue nesta rodada:
- versão do projeto atualizada para `2.1.3` (`pyproject.toml` e `src/trama/__init__.py`);
- CLI com comando `testes-avancados-v213`;
- suíte crítica v2.1.3 implementada no runtime:
  - `contrato_http_v213`;
  - `integracao_backend_v213`;
  - `dados_nativos_v213`;
  - `e2e_frontend_v213`;
  - `operacao_sre_v213`;
  - `baseline_v213`;
  - `caos_v213`;
- CI com `suite_critica_v213` e `gate_v213_obrigatorio`;
- runtime nativo com `--version` e `--diagnostico-runtime`;
- `.deb` v2.1.3 gerado/instalado e versão validada no sistema;
- documentação da versão v2.1.3 criada (linguagem, operação, manual consolidado e todo);
- pacote grande de exemplos v2.1.3 publicado em `exemplos/v213/` com 80+ arquivos e cenário multi-módulo.
- backend de domínio ARLS implementado em `.trm` em `exemplos/v213/arls_amm_trm/` com fluxo completo (`213_85_backend_arls_amm_fluxo_completo.trm`);
- template canônico de frontend/PWA adicionado na CLI (`trama template-frontend-pwa`).

Fechamento desta rodada:
- paridade do domínio ARLS em `.trm` validada por suíte oficial v2.1.3 e testes dedicados de domínio;
- fluxo de frontend/PWA coberto por template canônico e suíte e2e da versão;
- cadeia de dados nativa validada por migração/seed/diagnóstico no harness oficial;
- documentação e evidências de release/instalação consolidadas.

Verificação final executada:
- `.venv/bin/python -m trama.cli lint exemplos/v213 --json`:
  - `ok: true`, `total_arquivos: 97`, `erros: []`.
- `.venv/bin/python -m pytest -q tests/test_v212_ci_release.py tests/test_v213_ci_release.py tests/test_testes_avancados_v212.py tests/test_testes_avancados_v213.py tests/test_v213_arls_backend_trm.py tests/test_v213_arls_reunioes_permissoes.py tests/test_cli.py`:
  - `20 passed`.
- `.venv/bin/python -m trama.cli testes-avancados-v213 --perfil rapido --saida-json .local/test-results/v213_relatorio_final.json --saida-md .local/test-results/v213_relatorio_final.md --json`:
  - `ok: true`.

## 1. Objetivo

Atualizar a Trama para ampliar o funcionamento da linguagem (lexer, parser, semântica, compilador, VM e runtimes oficiais) de modo que ela substitua **integralmente** o stack JS/TS do projeto `/home/arara/ARLS_AMM` (backend + frontend + operação), com runtime e compilação **100% nativos** no caminho crítico, mantendo a identidade canônica pt-BR da linguagem.

Restrições deste planejamento:
- não alterar nada em `/home/arara/ARLS_AMM`;
- manter compatibilidade retroativa nas superfícies já existentes da Trama;
- sem dependência de Python em produção (execução, compilação, build, release e operação).
- manter a linguagem **canonicamente pt-BR** (lexer, parser, AST, semântica, compilador, VM, builtins, runtimes, CLI, docs e exemplos), com aliases em inglês apenas para compatibilidade retroativa.

## 2. Leitura e entendimento consolidado do ARLS_AMM

## 2.1 Domínio funcional atual

- autenticação administrativa com login/refresh/logout (refresh rotativo);
- gestão de obreiros e dependentes (familiares);
- gestão de visitantes e lojas;
- gestão de reuniões com:
  - presença por obreiro;
  - atividade (cartão de visita, trabalho);
  - observações oficiais;
  - visitantes por reunião;
- dashboard executivo com KPIs mensais;
- frontend PWA (instalável no iPhone);
- operação via `systemd` + PostgreSQL em container.

## 2.2 Contratos HTTP atuais (base mínima de paridade)

- padrão de envelope:
  - sucesso: `ok: true`, `dados`, `erro: null`, `meta.timestamp`;
  - erro: `ok: false`, `dados: null`, `erro.{codigo,mensagem,detalhes}`, `meta.timestamp`;
- rotas:
  - `/api/v1/auth/*`
  - `/api/v1/obreiros*`
  - `/api/v1/reunioes*`
  - `/api/v1/visitantes*`, `/api/v1/lojas*`
  - `/api/v1/dashboard/resumo`
  - `/saude`, `/pronto`, `/api/v1/ping`;
- validação de payload/parâmetros com regras explícitas (equivalente ao uso atual de Zod).

## 2.3 Persistência e dados

- banco PostgreSQL com entidades:
  - `usuarios`, `sessoes`, `obreiros`, `familiares`,
  - `lojas`, `visitantes`,
  - `reunioes`, `reuniao_presencas`, `reuniao_atividades`, `reuniao_visitantes`, `reuniao_observacoes`;
- constraints críticas:
  - unicidade por `refresh_token`;
  - unicidade composta em presença/atividade/visitante por reunião;
  - índices de busca para painéis e autocomplete.

## 2.4 Frontend

- SPA em hash router (`#/dashboard`, `#/obreiros`, `#/reunioes`, etc.);
- formulários completos de CRUD e lançamento;
- utilitários de data/hora/telefone/cookies/PWA;
- build com Vite + plugin PWA + testes utilitários.

## 2.5 Operação

- serviços `amm-loja-api` e `amm-loja-web` via `systemd`;
- scripts operacionais de backup/restore PostgreSQL;
- checks de saúde (`/saude`, `/pronto`) e smoke operacional.

## 3. Escopo de evolução da Trama para paridade 100%

Princípio de execução deste plano:
- o foco principal é a evolução da linguagem Trama e de seu ecossistema nativo;
- ARLS_AMM é referência de validação real de capacidade, não o fim em si;
- cada entrega deve fortalecer a plataforma Trama para múltiplos projetos complexos.
- toda superfície oficial nova deve nascer em pt-BR canônico (`snake_case`, sem acento em identificadores).

## 3.1 Runtime backend nativo (obrigatório)

- consolidar runtime HTTP nativo para cobrir 100% das rotas/contratos acima;
- DTO/contrato pt-BR canônico com validação profunda, coerção e sanitização;
- autenticação/sessão nativa (JWT + refresh rotation + revogação);
- autorização por perfil/cargo com erros determinísticos;
- integração completa com runtime DB nativo (PostgreSQL);
- realtime/cache distribuídos já existentes com garantias de integridade.

## 3.2 Ferramentas de dados nativas

- migrações e seed nativas Trama (sem Prisma/Node);
- introspecção e diff de schema para evolução controlada;
- comandos canônicos:
  - `trama migrar`
  - `trama seed`
  - `trama diagnostico-db`.

## 3.3 Frontend canônico Trama (para remover TS/React/Vite)

- runtime UI oficial em pt-BR para:
  - componentes, estado, eventos e roteamento SPA;
  - formulários com validação integrada a contrato;
  - consumo HTTP/realtime com sessão e renovação;
  - empacotamento PWA e manifesto;
- CLI de build frontend nativo:
  - `trama web-dev`
  - `trama web-build`
  - `trama web-preview`.

## 3.4 Build/distribuição sem Python

- `executar`, `compilar`, `executar-tbc` exclusivamente nativos;
- compilador `.trm -> .tbc` oficial para backend e frontend;
- release `.deb` + standalone com checksum e rollback;
- diagnóstico explícito de backend nativo ativo.

## 4. Plano de execução (ordem recomendada)

## Fase A - Congelamento de contrato e baseline
- extrair contrato HTTP canônico do ARLS_AMM para snapshots versionados;
- congelar cenários críticos (auth, obreiros, reuniões, visitantes, dashboard);
- publicar baseline funcional e de performance de referência.

Critério de aceite:
- suíte de regressão de contrato cobrindo 100% das rotas críticas.

## Fase B - Runtime backend Trama com paridade funcional
- implementar módulo de domínio ARLS em `.trm` com contratos explícitos;
- mapear entidades e regras de negócio atuais sem regressão;
- manter envelopes de erro/sucesso equivalentes e estáveis.

Critério de aceite:
- testes de integração passando contra as mesmas fixtures de dados.

## Fase C - Persistência/migração/seed nativos
- portar schema e migrações para ferramenta nativa Trama;
- portar seed administrativo e dados iniciais;
- validar restore/backup com scripts equivalentes nativos.

Critério de aceite:
- ambiente sobe do zero sem Node/Prisma e com schema íntegro.

## Fase D - Frontend nativo Trama
- implementar SPA equivalente (rotas, formulários, dashboard, reuniões, visitantes);
- portar utilitários críticos (timezone Fortaleza, formatação, hash router, cookies);
- suportar PWA instalável com manifesto e cache policy.

Critério de aceite:
- cobertura e2e dos fluxos críticos com UX equivalente ao sistema atual.

## Fase E - Operação/segurança/observabilidade/release
- consolidar `systemd`, health checks, métricas, traces e logs correlacionados;
- gates de CI/CD obrigatórios para merge e release;
- release `.deb` e standalone auditáveis.

Critério de aceite:
- deploy reprodutível em servidor com rollback validado.

## 5. Matriz de paridade obrigatória

- Auth:
  - login, refresh rotation, logout, revogação imediata.
- Obreiros/Familiares:
  - CRUD funcional + validações e erros estáveis.
- Visitantes/Lojas:
  - busca incremental e autocadastro sem inconsistência.
- Reuniões:
  - CRUD, presença, atividade, visitantes e observações.
- Dashboard:
  - KPIs mensais consistentes com dados persistidos.
- PWA/Frontend:
  - instalação, navegação, formulários, estado e integração API.
- Operação:
  - serviços, saúde, backup/restore e monitoramento.

Cada linha acima precisa de:
- teste unitário;
- teste de integração;
- teste de contrato (HTTP);
- evidência em documentação.

## 6. Requisitos de qualidade e bloqueios de merge

- determinismo de erros (`codigo`, `mensagem`, `detalhes`);
- compatibilidade retroativa nas APIs canônicas já existentes;
- nenhum TODO/placeholder em fluxo crítico;
- teste de integração obrigatório para toda feature nova;
- mudança de contrato HTTP sempre com teste de contrato;
- documentação atualizada por versão.

## 7. Definição de pronto (meta final)

Considerar concluído apenas quando:
- ARLS_AMM puder ser reconstruído integralmente em Trama sem JS/TS no runtime crítico;
- execução e compilação forem 100% nativas (sem ponte Python);
- suite de regressão, contrato, carga e caos estiver estável;
- release `.deb`/standalone com operação documentada e auditável.

## 8. Proposta de versionamento na Trama

Criar e usar a versão de roadmap:
- **v2.1.3 - Substituição total de stack JS/TS por Trama nativa**.

Escopo da v2.1.3:
- backend de produção com paridade funcional ARLS_AMM;
- frontend SPA/PWA nativo;
- migração/seed/operação/release sem dependência de Python.

## 9. Versionamento de implementação (fatiamento executável)

### v2.1.3-alpha.1 - Base de contrato e regressão
- congelamento de contrato HTTP atual (snapshots por rota);
- harness de regressão para envelopes de sucesso/erro;
- baseline inicial de performance e estabilidade.

Saída obrigatória:
- suíte `contrato_http_v213` bloqueando merge.

### v2.1.3-alpha.2 - Núcleo backend de domínio
- portar auth/obreiros/familiares/visitantes/reuniões/dashboard para `.trm`;
- manter compatibilidade canônica pt-BR e envelopes estáveis;
- validar paridade funcional por integração.

Saída obrigatória:
- suíte `integracao_backend_v213` verde com fixtures reais.

### v2.1.3-alpha.3 - Dados nativos (sem Prisma/Node)
- migração, seed e diagnóstico DB nativos;
- portar schema e constraints críticas;
- garantir boot do ambiente do zero sem toolchain JS.

Saída obrigatória:
- suíte `dados_nativos_v213` + comando de subida limpa documentado.

### v2.1.3-beta.1 - Frontend nativo Trama
- runtime UI canônico pt-BR (estado, componentes, roteamento);
- implementação dos fluxos críticos equivalentes ao web atual;
- build/preview PWA nativos.

Saída obrigatória:
- suíte `e2e_frontend_v213` cobrindo fluxos críticos ponta a ponta.

### v2.1.3-beta.2 - Operação e SRE de produção
- integração com métricas/logs/traces + health checks;
- scripts operacionais equivalentes (backup/restore/smoke);
- hardening e observabilidade auditável.

Saída obrigatória:
- suíte `operacao_sre_v213` e runbooks publicados.

### v2.1.3-rc.1 - Performance, caos e robustez
- carga/concorrência com metas `p50`, `p95`, throughput e taxa de erro;
- cenários de falha parcial DB/cache/backplane com fallback seguro;
- validação de não regressão de integridade.

Saída obrigatória:
- relatório reproduzível `baseline_v213` + `caos_v213`.

### v2.1.3 - GA (produção)
- release standalone + `.deb` + checksum + rollback;
- diagnóstico oficial "runtime 100% nativo";
- documentação final consolidada da versão.

Saída obrigatória:
- artefatos assinados/publicados e checklist DoD completo.

## 10. Ordem de implementação (dependências e trilha crítica)

1. `v2.1.3-alpha.1`  
dependência: nenhuma; define base de verdade de contrato.

2. `v2.1.3-alpha.2`  
dependência: `alpha.1`; backend só evolui com regressão de contrato ativa.

3. `v2.1.3-alpha.3`  
dependência: `alpha.2`; migração nativa usa domínio/backend já portados.

4. `v2.1.3-beta.1`  
dependência: `alpha.2` e preferencialmente `alpha.3`; frontend consome backend estável.

5. `v2.1.3-beta.2`  
dependência: `beta.1`; observabilidade/operação final com fluxos completos.

6. `v2.1.3-rc.1`  
dependência: `beta.2`; carga e caos só após stack completo integrado.

7. `v2.1.3`  
dependência: `rc.1`; release apenas com todas as suítes obrigatórias verdes.

## 11. Gates de avanço entre versões

- `alpha -> beta`:
  - paridade backend comprovada;
  - contrato HTTP estável;
  - dados nativos funcionais sem toolchain JS.
- `beta -> rc`:
  - frontend nativo completo;
  - operação/SRE auditável;
  - sem regressão crítica em auth/reuniões.
- `rc -> ga`:
  - baseline de performance reproduzível;
  - caos/falha parcial validados;
  - artefatos de release + rollback testados.

## 12. Roadmap operacional v2.1.4+ (tarefas executáveis)

### v2.1.4 - separar `web_runtime.py` em núcleo HTTP, modelo e engine legada
- [x] criar trilha operacional detalhada para os itens `v2.1.4+`
- [x] extrair `WebRoute`, `RateLimitPolicy` e `RateLimitDistribuidoPolicy` para módulo dedicado `src/trama/web_model.py`
- [x] extrair configuração de `WebApp` e contratos HTTP para módulo próprio de modelo
- [x] mover a engine legada baseada em `http.server` para módulo dedicado, preservando a API pública de `web_runtime`
- [x] validar compatibilidade com testes web existentes (`v202`, cache, segurança, observabilidade e multipart)

### v2.1.5 - introduzir interface de engine HTTP pluggável
- [x] definir contrato interno `HttpEngine`/`HttpRuntimeEngine`
- [x] adaptar `WebRuntime` para atuar como fachada da engine selecionada
- [x] registrar a engine legada como implementação padrão

### v2.1.6 - criar suíte de paridade entre engines
- [x] duplicar os cenários `v202` para uma matriz por engine
- [x] validar paridade de headers, envelopes e códigos de erro
- [x] bloquear regressão por CI com suíte de paridade

### v2.1.7 - extrair core de realtime
- [x] mover `TempoRealHub` e conexões para módulo `realtime_core`
- [x] separar estado de presença/salas/ack/cursor da camada HTTP
- [x] preservar API pública atual via reexport

### v2.1.8 - extrair fallback HTTP do realtime
- [x] mover endpoints e fluxo de long-polling para módulo próprio
- [x] testar reconexão por cursor sem depender do handler HTTP principal
- [x] manter compatibilidade dos testes `v203`

### v2.1.9 - extrair transporte WebSocket
- [x] isolar handshake e parsing de frames
- [x] separar ciclo de vida de conexão do hub de realtime
- [x] cobrir fechamento/heartbeat/limites com testes dedicados

### v2.1.10 - formalizar interface de backplane de realtime
- [x] definir interface de backplane distribuído
- [x] manter memória como backend de referência
- [x] preparar pontos de extensão explícitos para Redis

### v2.1.11 - endurecer backend Redis de realtime
- [x] ampliar testes reais Redis multi-instância
- [x] validar replay, ack/nack e recuperação após indisponibilidade
- [x] medir ordenação e consistência interprocesso

### v2.1.12 - introduzir engine ASGI
- [x] implementar backend ASGI compatível com `WebApp`
- [x] mapear request/response/stream sem quebrar contratos atuais
- [x] validar mesma app rodando em engine legada e ASGI

### v2.1.13 - shutdown, readiness e limites operacionais
- [x] adicionar shutdown gracioso nas engines HTTP
- [x] distinguir readiness/liveness/health na infraestrutura
- [x] formalizar limites de payload, conexões e tempo por request

### v2.1.14 - separar dialeto SQL, conexão e ORM
- [x] criar camada explícita de dialeto SQL
- [x] desacoplar conexão/transação de regras de ORM
- [x] remover pressupostos implícitos de SQLite nas rotas críticas

### v2.1.15 - ampliar suíte PostgreSQL real
- [x] executar CRUD/ORM/migração/seed em PostgreSQL real
- [x] cobrir transações, paginação e constraints
- [x] integrar a suíte ao CI

### v2.1.16 - consolidar introspecção e diff por dialeto
- [x] alinhar inspeção de schema entre SQLite e PostgreSQL
- [x] gerar diff/preview por dialeto
- [x] validar aplicação e rollback em ambos os backends

### v2.1.17 - formalizar capacidades por backend de banco
- [x] expor matriz de capabilities por backend
- [x] impedir uso implícito de features não suportadas
- [x] refletir capabilities em erro/documentação/CLI

### v2.1.18 - dividir segurança em módulos
- [ ] separar JWT, sessão, RBAC e políticas em módulos próprios
- [ ] manter API canônica estável via fachada
- [ ] ampliar testes por domínio de segurança

### v2.1.19 - adicionar `RS256`
- [ ] suportar chaves assimétricas locais
- [ ] suportar `kid` em emissão e validação
- [ ] validar rotação básica de chaves

### v2.1.20 - adicionar JWK/JWKS
- [ ] implementar resolução e cache de JWKS
- [ ] validar `iss`, `aud` e `kid`
- [ ] suportar rotação sem reinício do runtime

### v2.1.21 - base OIDC
- [ ] implementar discovery básico
- [ ] consumir `jwks_uri` e metadados do provedor
- [ ] validar fluxo mínimo de autenticação federada

### v2.1.22 - políticas contextuais de autorização
- [ ] introduzir engine de políticas ator/ação/recurso/contexto
- [ ] manter RBAC como subconjunto compatível
- [ ] documentar exemplos de autorização contextual

### v2.1.23 - jobs como fachada com backend pluggável
- [ ] definir interface de backend de jobs
- [ ] adaptar `JobQueue` para delegar no backend selecionado
- [ ] manter backend em memória como padrão de desenvolvimento

### v2.1.24 - backend persistente de jobs via SQL
- [ ] persistir fila, tentativas, leasing e DLQ em SQL
- [ ] implementar retry e reprocessamento
- [ ] cobrir reinício de processo sem perda de fila

### v2.1.25 - worker standalone
- [ ] criar comando de worker separado
- [ ] adicionar comandos operacionais de DLQ/reprocessamento/status
- [ ] documentar topologia web + worker

### v2.1.26 - backend Redis para jobs
- [ ] implementar fila Redis
- [ ] validar concorrência distribuída e visibilidade
- [ ] comparar semântica com backend SQL

### v2.1.27 - formalizar IR de contrato HTTP
- [ ] definir IR para rotas, DTOs, erros, auth e versões
- [ ] adaptar runtime HTTP para consumir o IR
- [ ] manter compatibilidade com contratos ad hoc existentes

### v2.1.28 - OpenAPI a partir do IR
- [ ] ligar gerador OpenAPI ao IR formal
- [ ] manter envelopes e exemplos consistentes
- [ ] validar retrocompatibilidade do output gerado

### v2.1.29 - SDKs a partir do IR
- [ ] ligar gerador Python ao IR
- [ ] ligar gerador TypeScript ao IR
- [ ] validar métodos, tipos e erros produzidos

### v2.1.30 - verificação de breaking changes
- [ ] comparar IR entre versões
- [ ] detectar mudança incompatível em rota/campo/erro
- [ ] bloquear regressão via CI

### v2.1.31 - pipeline de upload
- [ ] validar MIME, tamanho e hash
- [ ] suportar staging temporário e promoção
- [ ] integrar upload com storage local/S3

### v2.1.32 - multipart/streaming robustos
- [ ] evitar carga integral de payload grande em memória
- [ ] suportar streaming de upload
- [ ] ampliar testes de upload grande e limite

### v2.1.33 - pipeline de mídia
- [ ] conectar transformação/variantes ao storage
- [ ] persistir metadados e rastreabilidade
- [ ] cobrir fluxos mínimos de imagem/arquivo

### v2.1.34 - lifecycle e visibilidade de storage
- [ ] formalizar URL assinada e retenção
- [ ] suportar políticas por backend
- [ ] refletir visibilidade/expiração em CLI e docs

### v2.1.35 - observabilidade formal ampliada
- [ ] propagar `traceparent`
- [ ] medir métricas por engine/subsistema
- [ ] padronizar integração com exportadores

### v2.1.36 - resiliência operacional
- [ ] integrar circuit breaker e timeouts globais
- [ ] formalizar pools configuráveis
- [ ] consolidar diagnóstico operacional por ambiente

### v2.1.37 - backend de produção com SLO oficial
- [ ] publicar benchmark reproduzível
- [ ] adicionar suíte de carga multi-processo
- [ ] formalizar critérios SLO e erro aceitável

### v2.1.38 - documentação final da arquitetura modular
- [ ] publicar visão arquitetural consolidada
- [ ] publicar matriz oficial de capacidades por camada
- [ ] fechar checklist de adoção em produção
