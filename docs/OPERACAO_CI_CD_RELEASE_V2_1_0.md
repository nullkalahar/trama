# Operacao CI/CD e Release v2.1.0

## 1) Pipeline de CI (PR/push)
Workflow: `.github/workflows/ci.yml`

Etapas:
1. `qualidade_build_test_lint_cobertura`
2. `seguranca_sast_dependencias_segredos`
3. `gate_v210_obrigatorio`

## 2) Execucao local equivalente (pre-PR)

```bash
python -m pip install -e .[dev]
ruff check src tests
pytest --cov=src/trama --cov-report=term-missing --cov-report=xml --cov-fail-under=30
bash scripts/build_native_stub.sh
bandit -q -r src/trama -x tests -b .bandit-baseline.json
python -m pip check
pip-audit --progress-spinner off
detect-secrets-hook --baseline .secrets.baseline $(git ls-files)
```

## 3) Release por tag
Workflow: `.github/workflows/release.yml`

Disparo:
```bash
git tag v2.1.0
git push origin v2.1.0
```

Etapas de release:
- valida semver/changelog;
- build standalone;
- build release nativo + `.deb`;
- gera `SHA256SUMS.txt`;
- gera `metadados_release.json`;
- publica artefatos no GitHub Release.

## 4) Rollback de release
1. revogar tag/release incorreta.
2. corrigir changelog/versao.
3. publicar nova tag com patch incrementado (`x.y.z+1`).

## 5) Troubleshooting
- falha semver: alinhar `pyproject.toml` e `CHANGELOG.md`.
- falha cobertura: aumentar cobertura ou ajustar testes de regressao.
- falha seguranca: corrigir novo achado em relacao ao baseline (`.bandit-baseline.json` e `.secrets.baseline`).
