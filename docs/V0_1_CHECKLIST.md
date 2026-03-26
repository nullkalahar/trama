# Checklist v0.1 - trama

## Linguagem

- [x] Lexer funcional (tokens, comentários, strings, números, erros)
- [x] Equivalência com/sem acento em keywords (`função/funcao`, `senão/senao`)
- [x] Parser com precedência e blocos por `fim`
- [x] AST mínima para MVP
- [x] Análise semântica mínima
- [x] Compilador AST -> bytecode
- [x] VM executável com funções, `se/senao`, `enquanto`, `retorne`, `pare`, `continue`

## CLI

- [x] `trama executar`
- [x] `trama bytecode`
- [x] `trama compilar -o arquivo.tbc`

## Distribuição

- [x] Pacote Python instalável
- [x] Binário standalone obrigatório (`scripts/build_standalone.sh`)
- [x] Pacote Debian (`scripts/package_deb.sh`)
- [x] Scripts para repositório APT (`scripts/init_apt_repo.sh`, `scripts/publish_apt_package.sh`)

## Pendências externas (infra)

- [ ] chave GPG definitiva para assinatura de repositório
- [ ] servidor/hosting do repositório APT
- [ ] publicação pública para `apt install trama`
