# Politica de versionamento e changelog

## SemVer adotado
Formato: `MAJOR.MINOR.PATCH`

- MAJOR: mudanca quebravel.
- MINOR: funcionalidade nova retrocompativel.
- PATCH: correcao retrocompativel.

## Regras obrigatorias
- versao do `pyproject.toml` deve bater com tag de release (`vX.Y.Z`).
- `CHANGELOG.md` deve conter entrada da versao antes da release.
- toda release deve gerar checksums e metadados auditaveis.

## Estrutura de changelog
Para cada versao:
- `Adicionado`
- `Alterado`
- `Corrigido`
- `Removido` (se houver)
- `Seguranca` (se houver)

## Compatibilidade
- aliases em ingles apenas para compatibilidade retroativa.
- superficie oficial sempre pt-BR canonico.
