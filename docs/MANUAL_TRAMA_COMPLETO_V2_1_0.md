# Manual Trama completo ate v2.1.0

Consolidado de capacidades ate a v2.1.0.

## Evolucao recente
- v2.0.8: testes avancados.
- v2.0.9: runtime 100% nativo no caminho critico.
- v2.1.0: engenharia de produto (CI/CD e governanca).

## O que a v2.1.0 adiciona
1. CI obrigatoria para merge (build, testes, lint, cobertura, seguranca).
2. gates de qualidade para bloquear regressao critica em PR.
3. pipeline de release por tag semver com artefatos versionados.
4. rastreabilidade de release via checksum e metadados json.
5. politica de versionamento/changelog e guia formal de contribuicao.
6. guia de migracao para mudancas quebraveis.

## Artefatos oficiais da versao
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `scripts/validar_versao_semver.py`
- `scripts/gerar_metadados_release.py`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `docs/OPERACAO_CI_CD_RELEASE_V2_1_0.md`
- `docs/GOVERNANCA_CONTRIBUICAO_V2_1_0.md`
- `docs/MIGRACAO_BREAKING_CHANGES.md`
- `docs/POLITICA_VERSIONAMENTO_CHANGELOG.md`
