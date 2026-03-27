# Linguagem trama v0.9

A `v0.9` adiciona tooling oficial para projetos reais: testes, lint/format, cobertura e template backend.

## CLI de tooling

## Test runner oficial

```bash
trama testar [alvo]
trama testar [alvo] --json
```

Executa todos os arquivos `test_*.trm`.

## Lint

```bash
trama lint [alvo]
trama lint [alvo] --json
```

Valida lexer/parser/semântica (`compile_source`) para cada `.trm`.

## Formatador

```bash
trama formatar [alvo]
trama formatar [alvo] --aplicar
```

Normalizações atuais:

- tabs para 4 espaços
- remoção de espaço no fim da linha
- newline final garantido
- redução de blocos de linhas em branco excessivas

## Cobertura

```bash
trama cobertura [alvo]
trama cobertura [alvo] --json
```

Relatório de cobertura estática de módulos `.trm` com base em imports de arquivos de teste.

## Template backend

```bash
trama template-backend <destino>
trama template-backend <destino> --forcar
```

Estrutura criada:

- `src/app.trm`
- `tests/test_smoke.trm`
- `migrations/001_inicial.sql`
- `seeds/001_seed.sql`
- `config/.env.exemplo`
- `README.md`
