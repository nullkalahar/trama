# trama

A `trama` é uma linguagem de programação em português (pt-BR), de uso geral, com tipagem simples (estilo Python), compilação para bytecode próprio e execução em VM própria.

## Direção do Projeto

A meta é construir uma linguagem geral primeiro, com base sólida, e evoluir para suportar backend robusto.


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

### Em andamento

- hardening de runtime e ergonomia para backend (preparação de v0.3+)

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

## Distribuição (atual: v0.2)

Build do binário standalone (obrigatório):

```bash
scripts/build_standalone.sh
./dist/trama executar examples/ola_mundo.trm
```

Build do pacote Debian:

```bash
scripts/package_deb.sh 0.2.0 amd64
sudo apt install ./build/trama_0.2.0_amd64.deb
```

Preparar repositório APT:

```bash
scripts/init_apt_repo.sh packaging/apt-repo stable main trama <SEU_GPG_KEY_ID>
scripts/publish_apt_package.sh packaging/apt-repo stable ./build/trama_0.2.0_amd64.deb
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

### v0.3
- [ ] runtime assíncrono oficial
- [ ] `async/await`, tarefas, timeout e cancelamento
- [ ] I/O não bloqueante

### v0.4
- [ ] stdlib backend mínima (HTTP client, FS, ENV, TIME, LOG)
- [ ] serialização JSON robusta
- [ ] configuração por ambiente

### v0.5
- [ ] servidor web nativo
- [ ] roteamento, middlewares, CORS, request/response
- [ ] validação de payload e erros padronizados
- [ ] healthcheck e serving de estáticos

### v0.6
- [ ] driver PostgreSQL async + query builder/ORM inicial
- [ ] transações
- [ ] migrações idempotentes + seed

### v0.7
- [ ] JWT + hash de senha (bcrypt/argon2)
- [ ] autorização por papéis (RBAC)

### v0.8
- [ ] logs estruturados
- [ ] métricas e tracing inicial
- [ ] práticas de operação para produção

### v0.9
- [ ] test runner oficial
- [ ] cobertura, lint/format
- [ ] templates de projeto backend

### v1.0 (backend pronto para produção)
- [ ] paridade backend geral em produção
- [ ] suporte a APIs versionadas, jobs e webhooks
- [ ] testes de integração e carga com estabilidade operacional

### v1.5 (frontend)
- [ ] toolkit de UI, estado e renderização
- [ ] integração HTML/CSS/DOM (ou runtime equivalente)
- [ ] roteamento SPA + build + hot reload
- [ ] integração full-stack com backend em `trama`

### v1.5–v1.8 (paridade backend avançada)
- [ ] REST + realtime (Socket.IO/WebSocket) com autenticação JWT
- [ ] mensagens em tempo real, eventos sociais e alertas
- [ ] comunidades/guildas com moderação e permissões
- [ ] APIs administrativas + campanhas de push + métricas
- [ ] upload de mídia + persistência + cache offline/sync incremental
- [ ] deploy completo (Docker, `.deb`, standalone) com observabilidade robusta

## Princípios Técnicos

- simplicidade primeiro
- gramática pequena e sem ambiguidades
- testes desde o lexer
- compatibilidade com evolução para backend real
- documentação de linguagem obrigatória: cada versão deve criar/atualizar o manual da linguagem

## Licença

MIT (livre e permissiva).
