#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _extrair_versao_pyproject(pyproject_path: Path) -> str:
    text = pyproject_path.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    if not m:
        raise ValueError("versao_nao_encontrada_no_pyproject")
    return m.group(1)


def _validar_semver(valor: str, nome: str) -> None:
    if not SEMVER_RE.match(valor):
        raise ValueError(f"{nome}_invalido_semver:{valor}")


def _validar_changelog(changelog_path: Path, versao: str) -> None:
    text = changelog_path.read_text(encoding="utf-8")
    marcadores = [f"## [{versao}]", f"## {versao}"]
    if not any(m in text for m in marcadores):
        raise ValueError(f"changelog_sem_versao:{versao}")


def validar(tag: str, changelog: Path, pyproject: Path) -> None:
    _validar_semver(tag, "tag")
    versao_pyproject = _extrair_versao_pyproject(pyproject)
    _validar_semver(versao_pyproject, "pyproject")
    if versao_pyproject != tag:
        raise ValueError(f"versao_divergente:tag={tag};pyproject={versao_pyproject}")
    _validar_changelog(changelog, tag)


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida semver e changelog da release.")
    parser.add_argument("--tag", required=True, help="versao sem 'v', ex.: 2.1.0")
    parser.add_argument("--changelog", required=True, type=Path)
    parser.add_argument("--pyproject", required=True, type=Path)
    args = parser.parse_args()

    try:
        validar(args.tag, args.changelog, args.pyproject)
    except ValueError as exc:
        print(f"ERRO_VALIDACAO_RELEASE: {exc}")
        return 1

    print("OK_VALIDACAO_RELEASE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
