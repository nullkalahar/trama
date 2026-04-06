# Changelog

Todas as mudancas relevantes deste projeto serao documentadas neste arquivo.

Formato baseado em Keep a Changelog e versionamento semantico (SemVer).

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
