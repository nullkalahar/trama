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

### Manuais consolidados e operação
- `docs/MANUAL_TRAMA_COMPLETO_V2_1_3.md`
- `docs/OPERACAO_V2_1_3_SUBSTITUICAO_TOTAL.md`
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
