# Changelog

Todas as mudancas relevantes deste projeto serao documentadas neste arquivo.

Formato baseado em Keep a Changelog e versionamento semantico (SemVer).

## [2.1.3] - 2026-04-20

### Adicionado
- suíte crítica oficial da v2.1.3 em `src/trama/testes_avancados_runtime.py` com:
  - `contrato_http_v213`;
  - `integracao_backend_v213`;
  - `dados_nativos_v213`;
  - `e2e_frontend_v213`;
  - `operacao_sre_v213`;
  - `baseline_v213`;
  - `caos_v213`.
- comando CLI canônico `trama testes-avancados-v213`.
- novos testes:
  - `tests/test_testes_avancados_v213.py`
  - `tests/test_v213_ci_release.py`
- CI expandida com:
  - `suite_critica_v213`
  - `gate_v213_obrigatorio`
- documentação oficial da versão:
  - `docs/LINGUAGEM_V2_1_3.md`
  - `docs/MANUAL_TRAMA_COMPLETO_V2_1_3.md`
  - `docs/OPERACAO_V2_1_3_SUBSTITUICAO_TOTAL.md`
  - `docs/TODO_V2_1_3_IMPLEMENTACAO_TOTAL.md`
- pacote massivo de exemplos v2.1.3:
  - `exemplos/v213/213_01_exemplo_v213.trm` até `exemplos/v213/213_84_exemplo_v213.trm`
  - `exemplos/v213/sistema_grande_v213/`.
- backend de domínio ARLS em `.trm`:
  - `exemplos/v213/arls_amm_trm/mod_estado.trm`
  - `exemplos/v213/arls_amm_trm/mod_auth.trm`
  - `exemplos/v213/arls_amm_trm/mod_obreiros.trm`
  - `exemplos/v213/arls_amm_trm/mod_visitantes.trm`
  - `exemplos/v213/arls_amm_trm/mod_reunioes.trm`
  - `exemplos/v213/arls_amm_trm/mod_dashboard.trm`
  - `exemplos/v213/arls_amm_trm/213_85_backend_arls_amm_fluxo_completo.trm`
- template canônico de frontend/PWA na CLI:
  - comando `trama template-frontend-pwa`.
- teste de integração do fluxo ARLS em `.trm`:
  - `tests/test_v213_arls_backend_trm.py`.

### Alterado
- versão do projeto para `2.1.3` em:
  - `pyproject.toml`
  - `src/trama/__init__.py`
- build/release nativo:
  - `scripts/build_release_nativo.sh` com versão padrão `2.1.3`;
  - suporte explícito a `--version` no runtime nativo (`native/trama_native.c`).
- README e índice de exemplos/documentação atualizados para v2.1.3.

## [2.1.2] - 2026-04-07

### Adicionado
- suite critica oficial da v2.1.2 em `src/trama/testes_avancados_runtime.py` com:
  - paridade Python/nativo para fluxos criticos;
  - contrato HTTP com erros estaveis;
  - carga/concorrrencia multi-instancia;
  - caos/falha parcial para DB/cache/backplane;
  - validacao minima de seguranca de producao.
- comando CLI canônico `trama testes-avancados-v212`.
- novos testes:
  - `tests/test_testes_avancados_v212.py`
  - `tests/test_cli_v212.py`
  - `tests/test_v212_ci_release.py`
- workflow de CI atualizado para v2.1.2 com gate bloqueante:
  - `suite_critica_v212`
  - `gate_v212_obrigatorio`
- workflow de release atualizado para v2.1.2 com `ROLLBACK.md` entre artefatos publicados.
- documentação oficial da versão:
  - `docs/LINGUAGEM_V2_1_2.md`
  - `docs/MANUAL_TRAMA_COMPLETO_V2_1_2.md`
  - `docs/OPERACAO_V2_1_2_BACKEND_COMPLEXO.md`
  - `docs/BASELINE_V2_1_2.md`
  - `docs/REFERENCIA_CAPACIDADES_V2_1_2.md`
- script de geração de referência completa de capacidades:
  - `scripts/gerar_referencia_capacidades.py`
- teste de consistência da cobertura documental:
  - `tests/test_documentacao_capacidades_v212.py`
- exemplos oficiais em `exemplos/v212/`.

### Alterado
- versão do projeto para `2.1.2` em `pyproject.toml`.
- versão de pacote em `src/trama/__init__.py`.
- README com status concluido da v2.1.2 e evidencias.

## [2.1.0] - 2026-04-05

### Adicionado
- pipeline oficial de CI em `.github/workflows/ci.yml` com jobs de:
  - build nativo,
  - testes,
  - lint,
  - cobertura,
  - seguranca.
- gate obrigatorio de merge (`gate_v210_obrigatorio`) para bloquear regressao critica em PR.
- esteira de release automatizada em `.github/workflows/release.yml` para tags `v*.*.*`.
- scripts de release/governanca:
  - `scripts/validar_versao_semver.py`
  - `scripts/gerar_metadados_release.py`
- metadados auditaveis de release (json + checksums).
- template de PR com checklist obrigatorio em `.github/pull_request_template.md`.
- documentacao de governanca, operacao CI/CD e migracao:
  - `docs/LINGUAGEM_V2_1_0.md`
  - `docs/MANUAL_TRAMA_COMPLETO_V2_1_0.md`
  - `docs/OPERACAO_CI_CD_RELEASE_V2_1_0.md`
  - `docs/GOVERNANCA_CONTRIBUICAO_V2_1_0.md`
  - `docs/MIGRACAO_BREAKING_CHANGES.md`
  - `docs/POLITICA_VERSIONAMENTO_CHANGELOG.md`

### Alterado
- versao do projeto para `2.1.0` em `pyproject.toml`.
- dependencias de desenvolvimento ampliadas para cobertura e seguranca.
- README atualizado com roadmap e evidencias da v2.1.0.

## [2.0.9] - 2026-04-05

### Adicionado
- runtime nativo 100% no caminho critico (`executar`, `compilar`, `executar-tbc`).
