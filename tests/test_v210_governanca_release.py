from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_validar_semver_e_changelog_ok(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "2.1.0"\n', encoding="utf-8")

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [2.1.0] - 2026-04-05\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "validar_versao_semver.py"),
            "--tag",
            "2.1.0",
            "--changelog",
            str(changelog),
            "--pyproject",
            str(pyproject),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK_VALIDACAO_RELEASE" in proc.stdout


def test_validar_semver_divergente_falha(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "2.1.1"\n', encoding="utf-8")

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## [2.1.1] - 2026-04-05\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "validar_versao_semver.py"),
            "--tag",
            "2.1.0",
            "--changelog",
            str(changelog),
            "--pyproject",
            str(pyproject),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "versao_divergente" in (proc.stdout + proc.stderr)


def test_gerar_metadados_release(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    art1 = tmp_path / "a.bin"
    art1.write_bytes(b"abc")
    art2 = tmp_path / "nao_existe.bin"

    saida = tmp_path / "metadados.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "gerar_metadados_release.py"),
            "--versao",
            "2.1.0",
            "--saida",
            str(saida),
            "--artefato",
            str(art1),
            "--artefato",
            str(art2),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert saida.exists()

    saved = json.loads(saida.read_text(encoding="utf-8"))
    assert saved["versao"] == "2.1.0"
    assert saved["artefatos"][0]["existe"] is True
    assert saved["artefatos"][1]["existe"] is False
