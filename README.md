# trama

A `trama` é uma linguagem de programação em português (pt-BR), de uso geral, com tipagem simples (estilo Python), compilação para bytecode próprio e execução em VM própria.

## Direção do Projeto

A meta é construir uma linguagem geral primeiro, com base sólida, e evoluir para suportar backend robusto.

Referência prática de objetivo futuro:

- projeto backend existente em `/home/arara/SugoiDekkai Migração/Ecos de Faerùn/backend`

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
- checklist de entrega em [`docs/V0_1_CHECKLIST.md`](docs/V0_1_CHECKLIST.md)
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

### Em andamento

- refinamento de erros e hardening para casos limite

### Falta fazer (próximos passos)

- Sprint 5: integração orientada a backend (módulos, libs padrão iniciais, melhoria de erros)
- publicação do repositório APT em servidor (infra externa + domínio + GPG real)

## Estrutura do Repositório

```text
trama/
  docs/
  src/trama/
  tests/
  examples/
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

Validação rápida sem pytest:

```bash
make check
make run-example
```

## Comandos da CLI (fase inicial)

```bash
trama executar arquivo.trm
trama compilar arquivo.trm -o arquivo.tbc
trama bytecode arquivo.trm
trama repl
```

## Distribuição v0.1

Build do binário standalone (obrigatório):

```bash
scripts/build_standalone.sh
./dist/trama executar examples/ola_mundo.trm
```

Build do pacote Debian:

```bash
scripts/package_deb.sh 0.1.0 amd64
sudo apt install ./build/trama_0.1.0_amd64.deb
```

Preparar repositório APT:

```bash
scripts/init_apt_repo.sh packaging/apt-repo stable main trama <SEU_GPG_KEY_ID>
scripts/publish_apt_package.sh packaging/apt-repo stable ./build/trama_0.1.0_amd64.deb
```

## Entrega da v0.1

A `v0.1` é considerada pronta quando cumprir:

- execução fim a fim da linguagem (lexer, parser, compilador, VM)
- CLI funcional para executar e inspecionar bytecode
- pacote Python instalável
- binário standalone obrigatório
- pacote Debian (`.deb`) instalável localmente
- publicação em repositório APT assinado para permitir `apt install trama`

## Objetivo da v1.0 (Backend)

Para a `trama` ser uma linguagem viável para backend em produção, a v1.0 deve entregar:

- sistema de módulos/imports estável
- biblioteca padrão de rede/HTTP (cliente e servidor)
- acesso a banco de dados (mínimo SQL)
- I/O de arquivos e configuração por ambiente
- tratamento de erros/exceções robusto
- concorrência assíncrona (ou modelo equivalente para I/O)
- logs estruturados e observabilidade básica (métricas/traces iniciais)
- testes e tooling para projetos backend (runner, cobertura, lint/format)
- empacotamento e deploy previsíveis (binário, `.deb`, container-friendly)
- compatibilidade e documentação de migração entre versões

## Objetivo da v1.5 (Frontend)

Após consolidar backend na v1.0, a v1.5 deve habilitar desenvolvimento frontend com:

- toolkit de UI (componentes, estado e ciclo de renderização)
- integração com HTML/CSS/DOM (ou runtime equivalente)
- roteamento de aplicação (SPA)
- consumo de API HTTP no cliente
- build de assets frontend (dev/prod)
- hot reload para desenvolvimento
- integração full-stack com backend em `trama`
- documentação e templates de projeto frontend

## Meta v1.5: Substituir o Backend 

Para a `trama` substituir esse backend real até a `v1.5`, precisa atingir paridade funcional nos pontos abaixo:

- framework web HTTP com roteamento, middlewares e CORS
- suporte a API versionada (`/api/v1`) e rotas de webhook
- autenticação com bearer token (JWT) + hashing de senha (bcrypt)
- validação/serialização de payloads (equivalente ao uso atual de schemas)
- ORM/SQL assíncrono com PostgreSQL (queries, filtros, join, upsert, transação)
- migrações de banco e seed idempotente de dados iniciais (planos/cupons)
- jobs agendados assíncronos (cron e interval), com execução contínua em produção
- camada de integração HTTP externa assíncrona (ex.: Evolution API)
- integração com provedores de pagamento e webhooks (Stripe já ativo; Mercado Pago planejado)
- regras de negócio de assinatura/plano (free, premium, empresarial) e autorização por plano
- sincronização em lote cliente-servidor (endpoint de sync com upsert + diff por `updated_at`)
- gerenciamento de listas de transmissão e membros com limites por plano
- i18n de mensagens de lembrete e tratamento de timezone por usuário
- observabilidade mínima para produção: logs estruturados, healthcheck, códigos de erro consistentes
- servir frontend estático (SPA) no mesmo backend quando necessário
- deploy container-friendly (Docker), `.deb` e binário standalone
- suíte de testes de integração cobrindo auth, CRUD, sync, assinatura e jobs

Critério objetivo de aceite:

- executar os mesmos fluxos atuais do Sooner (auth, eventos, listas, sync, usuário, assinaturas, webhooks e jobs)
- manter compatibilidade de contrato HTTP com os clientes atuais (app/web)
- operar com estabilidade em ambiente real (túnel/proxy + Postgres + serviços externos)

## Meta v1.5–v1.8: 

Para a `trama` também substituir esse backend no intervalo `v1.5` a `v1.8`, precisa entregar:

- servidor HTTP completo com rotas REST compatíveis com os contratos atuais do app
- servidor Socket.IO/WebSocket nativo com autenticação JWT por conexão
- sistema de mensagens privadas em tempo real (conversas, mensagens, upload de arquivo, contador de não lidas, confirmação de leitura)
- eventos realtime compatíveis: `new_message`, `typing_status`, `read_receipt`, `user_online`, `user_offline`
- sistema social/gamificado em tempo real (eventos `new_like`, `new_comment`, `new_follower`, `new_alert`)
- sistema de guildas/comunidades (feed por guilda, posts, comentários, reações, moderação e permissões de membro)
- APIs administrativas (dashboard, métricas de engajamento em tempo real e campanhas de push)
- suporte a push notifications end-to-end (registro de token, campanhas, envio e estatísticas)
- autenticação/autorização robusta (JWT + perfis de permissão: usuário, moderador, administrador)
- camada de upload de mídia com validação de tipo/tamanho e URLs públicas
- persistência e cache (banco relacional para domínio principal + estratégia de cache offline/sincronização incremental)
- observabilidade e operação (métricas de conexões WebSocket, filas/eventos, logs estruturados, healthcheck e backpressure)
- compatibilidade de deploy (execução atrás de túnel/proxy, Docker, `.deb` e binário standalone)

Critério objetivo de aceite:

- app Flutter atual do BraniMeDB funcionar sem regressão crítica ao trocar o backend para `trama`
- manter paridade de eventos realtime e contratos REST usados em produção
- suportar carga de mensagens/conexões simultâneas com estabilidade operacional

## Princípios Técnicos

- simplicidade primeiro
- gramática pequena e sem ambiguidades
- testes desde o lexer
- compatibilidade com evolução para backend real

## Licença

MIT (livre e permissiva).
