# trama

Linguagem de programação em português (pt-BR), de propósito geral, com tipagem simples estilo Python e compilação para bytecode próprio executado por uma VM própria.

## Objetivo

A `trama` nasce para ser:

- simples de aprender e usar
- legível para quem pensa em português
- útil para scripts e evolução para backend

## Arquitetura

Pipeline da linguagem:

`fonte (.trm)` -> `lexer` -> `parser` -> `AST` -> `análise semântica` -> `compilador` -> `bytecode` -> `VM` -> `execução`

## Status

Projeto em fase inicial (scaffold + plano técnico).

Documento de planejamento:

- [`docs/PLANO_TRAMA.md`](docs/PLANO_TRAMA.md)

## Estrutura do Projeto

```text
trama/
  docs/
  src/trama/
  tests/
  examples/
```

## Como começar

1. Criar ambiente virtual Python 3.11+
2. Instalar dependências de desenvolvimento
3. Executar testes

Comandos:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## Roadmap imediato

- implementar `token.py` e `lexer.py`
- criar testes de lexer
- implementar parser e AST mínima
- fechar ciclo de execução com bytecode + VM

## Licença

A definir.
