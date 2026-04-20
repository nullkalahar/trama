# Manual Trama Completo - ate v2.1.3

## 1. Resumo executivo

A Trama v2.1.3 consolida:
- runtime nativo para caminho critico;
- suite critica versionada para validacao de producao;
- trilha de release auditavel (`standalone`, `.deb`, checksum, rollback);
- diretriz canonica pt-BR em lexer/parser/semantica/compilador/VM/runtimes.

## 2. Linha de evolucao relevante

- v2.0.8: harness de testes avancados;
- v2.0.9: runtime 100% nativo;
- v2.1.0: CI/CD e governanca;
- v2.1.1: linguagem para codebase grande;
- v2.1.2: prontidao backend complexo;
- v2.1.3: substituicao total JS/TS por Trama nativa (foco de entrega atual).

## 3. Comandos principais

Executar codigo:

```bash
trama executar arquivo.trm
```

Compilar para bytecode:

```bash
trama compilar arquivo.trm -o saida.tbc
```

Executar bytecode:

```bash
trama executar-tbc saida.tbc
```

Diagnostico de runtime:

```bash
trama --diagnostico-runtime
```

Suite avancada v2.1.3:

```bash
trama testes-avancados-v213 --perfil rapido --json
```

## 4. Boas praticas para backend complexo

- usar contratos HTTP versionados por rota;
- padronizar erros com envelope estavel;
- manter suites de regressao e contrato obrigatorias;
- documentar operacao e rollback por release;
- evitar acoplamento com toolchain externo no caminho critico.

## 5. Dados e migracoes

A cadeia nativa deve cobrir:
- migracao versionada;
- trilha de execucao;
- seed por ambiente;
- validacao de compatibilidade e rollback seguro.

## 6. Qualidade e gates

Gates minimos de merge:
- qualidade (build/lint/testes/cobertura);
- seguranca (SAST/dependencias/segredos);
- suite critica v2.1.3;
- gate final bloqueando merge em falha critica.

## 7. Artefatos de distribuicao

- `standalone`;
- `.deb`;
- `SHA256SUMS`;
- `ROLLBACK.md`.

## 8. Exemplos oficiais

Colecao de exemplos da versao:
- `exemplos/v213/`;
- indice principal: `exemplos/v213/README_EXEMPLOS_V213.md`.

## 9. Encerramento de versao

A versao v2.1.3 deve ser marcada como concluida somente com:
- checklist tecnico completo;
- evidencia de suites verdes;
- instalacao validada em sistema alvo;
- documentacao consolidada publicada.
