# Trama v2.1.0 - Engenharia de produto (CI/CD e governanca)

A v2.1.0 consolida operacao de engenharia para producao com gates obrigatorios, release auditavel e governanca formal.

## Objetivo
- garantir qualidade minima obrigatoria antes de merge.
- tornar release reproduzivel e auditavel.
- formalizar governanca de evolucao do projeto.

## Entregas tecnicas

1. CI oficial com gates
- arquivo: `.github/workflows/ci.yml`
- etapas: lint, testes, cobertura, build nativo e seguranca.
- gate final: `gate_v210_obrigatorio`.

2. Release automatizado
- arquivo: `.github/workflows/release.yml`
- disparo por tag semver `v*.*.*`.
- artefatos: standalone, `.deb`, checksums e metadados json.

3. SemVer + changelog estruturado
- `pyproject.toml` com versao oficial.
- `CHANGELOG.md` por versao.
- validacao automatica por `scripts/validar_versao_semver.py`.

4. Governanca/contribuicao
- `CONTRIBUTING.md`
- `docs/GOVERNANCA_CONTRIBUICAO_V2_1_0.md`
- template de PR com checklist em `.github/pull_request_template.md`.

5. Migracao de breaking changes
- `docs/MIGRACAO_BREAKING_CHANGES.md` com estrategia e rollback.

## DoD v2.1.0 atendido
- merges protegidos por qualidade minima obrigatoria: sim (gate CI).
- releases reproduziveis e auditaveis: sim (workflow + checksums + metadados).
- governanca de evolucao publicada e aplicada: sim (guias e template).
