# Trama v2.1.3 - Substituicao total JS/TS por Trama nativa

## 1. Escopo da versao

A v2.1.3 consolida a evolucao da Trama para substituir stacks JS/TS em backend e frontend com superficie oficial canonicamente pt-BR, sem dependencia de Python no caminho critico de producao.

Objetivos centrais:
- backend de dominio em `.trm` com contrato HTTP estavel;
- dados nativos (migracao/seed/diagnostico) sem Prisma/Node;
- frontend SPA/PWA nativo em Trama;
- release auditavel (`standalone` + `.deb`) com checksum e rollback.

## 2. Canonico pt-BR (regra de ouro)

A forma oficial da linguagem permanece em pt-BR em toda a superficie:
- lexer;
- parser;
- AST;
- semantica;
- compilador;
- VM;
- builtins e runtimes;
- CLI, docs e exemplos.

Regras:
- identificadores em `snake_case` sem acento;
- mensagens e codigos de erro deterministicas;
- aliases em ingles apenas para compatibilidade retroativa.

## 3. API oficial de testes avancados v2.1.3

Novo comando canonico:

```bash
trama testes-avancados-v213 --perfil rapido --json
```

Parametros:
- `--perfil`: `rapido` ou `completo`;
- `--saida-json`: caminho do relatorio JSON;
- `--saida-md`: caminho do relatorio Markdown;
- `--json`: imprime resumo no stdout.

Suites da v2.1.3:
- `contrato_http_v213`;
- `integracao_backend_v213`;
- `dados_nativos_v213`;
- `e2e_frontend_v213`;
- `operacao_sre_v213`;
- `baseline_v213`;
- `caos_v213`.

Template frontend/PWA canônico:

```bash
trama template-frontend-pwa ./meu_frontend --json
```

Fluxo de backend de domínio ARLS em `.trm`:
- `exemplos/v213/arls_amm_trm/mod_estado.trm`
- `exemplos/v213/arls_amm_trm/mod_auth.trm`
- `exemplos/v213/arls_amm_trm/mod_obreiros.trm`
- `exemplos/v213/arls_amm_trm/mod_visitantes.trm`
- `exemplos/v213/arls_amm_trm/mod_reunioes.trm`
- `exemplos/v213/arls_amm_trm/mod_dashboard.trm`

Capacidades de reuniao no dominio ARLS:
- criacao, alteracao e remocao logica (`status=cancelada`);
- identificacao temporal (`reuniao_ja_passou`);
- controle de presenca por perfil `chanceler`;
- validacao de `cargo_ocupado` contra lista oficial de cargos;
- consolidacao de presencas/atividades/visitantes/observacoes no detalhamento.

## 4. Contrato de erro esperado

Envelope de erro oficial:

```json
{
  "ok": false,
  "dados": null,
  "erro": {
    "codigo": "VALIDACAO_FALHOU",
    "mensagem": "Payload invalido.",
    "detalhes": {
      "campos": []
    }
  },
  "meta": {
    "timestamp": "2026-04-20T10:00:00-03:00"
  }
}
```

Campos obrigatorios:
- `codigo`;
- `mensagem`;
- `detalhes`.

## 5. Fluxo recomendado de validacao de versao

1. executar suite v2.1.3:

```bash
trama testes-avancados-v213 --perfil completo --saida-json .local/test-results/v213_relatorio.json --saida-md .local/test-results/v213_relatorio.md
```

2. gerar release nativo:

```bash
scripts/build_release_nativo.sh 2.1.3 amd64
```

3. validar runtime e versao:

```bash
./dist/native/trama-native --diagnostico-runtime
./dist/native/trama-native
```

## 6. Compatibilidade

A v2.1.3 preserva compatibilidade retroativa da superficie publica existente.

Compromissos:
- rotas/erros criticos sem regressao;
- contratos HTTP versionados;
- comandos anteriores mantidos.

## 7. Evidencias minimas de pronto

- relatorio `v213_relatorio.json` com suites verdes;
- testes de dominio ARLS em `.trm`:
  - `tests/test_v213_arls_backend_trm.py`;
  - `tests/test_v213_arls_reunioes_permissoes.py`;
- CI com `suite_critica_v213` e `gate_v213_obrigatorio`;
- artefatos de release gerados (`.deb`, standalone, checksum);
- docs da versao e exemplos extensos publicados.
