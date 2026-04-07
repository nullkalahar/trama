from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_referencia_capacidades_v212_esta_atualizada(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    doc_oficial = root / "docs" / "REFERENCIA_CAPACIDADES_V2_1_2.md"
    assert doc_oficial.exists()

    gerado = tmp_path / "referencia.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "gerar_referencia_capacidades.py"),
            "--saida",
            str(gerado),
        ],
        cwd=str(root),
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    oficial = doc_oficial.read_text(encoding="utf-8")
    novo = gerado.read_text(encoding="utf-8")
    assert oficial == novo


def test_readme_e_manual_referenciam_referencia_capacidades() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    manual = (root / "docs" / "LINGUAGEM_V2_1_2.md").read_text(encoding="utf-8")
    assert "REFERENCIA_CAPACIDADES_V2_1_2.md" in readme
    assert "REFERENCIA_CAPACIDADES_V2_1_2.md" in manual
