from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _build_native(root: Path, tmp_path: Path) -> Path:
    build = subprocess.run(
        ["bash", str(root / "scripts" / "build_native_stub.sh")],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    native = root / "dist" / "native" / "trama-native"
    assert native.exists()
    local = tmp_path / "trama-native"
    shutil.copy2(native, local)
    local.chmod(0o755)
    return local


def _compilar_legado_python(root: Path, fonte: Path, saida: Path) -> None:
    py = root / ".venv" / "bin" / "python"
    comp = subprocess.run(
        [str(py), "-m", "trama.cli", "compilar-legado", str(fonte), "-o", str(saida)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
    )
    assert comp.returncode == 0, comp.stderr
    assert saida.exists()


def test_v211_paridade_nativa_para_em_via_tbc(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    native = _build_native(root, tmp_path)

    src = tmp_path / "for_v211.trm"
    src.write_text(
        (
            "função principal()\n"
            "    nums = [1, 2, 3, 4]\n"
            "    total = 0\n"
            "    para n em nums\n"
            "        total = total + n\n"
            "    fim\n"
            "    exibir(total)\n"
            "fim\n"
        ),
        encoding="utf-8",
    )
    out_tbc = tmp_path / "for_v211.tbc"
    _compilar_legado_python(root, src, out_tbc)

    run = subprocess.run(
        [str(native), "executar-tbc", str(out_tbc)],
        cwd=str(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "10"


def test_v211_paridade_nativa_import_explicito_via_tbc(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    native = _build_native(root, tmp_path)

    modulo = tmp_path / "mod.trm"
    modulo.write_text(
        (
            "exporte soma\n"
            "função soma(a: inteiro, b: inteiro): inteiro\n"
            "    retorne a + b\n"
            "fim\n"
        ),
        encoding="utf-8",
    )
    _compilar_legado_python(root, modulo, tmp_path / "mod.tbc")

    app = tmp_path / "app.trm"
    app.write_text(
        (
            'importe "mod.trm" como m expondo soma\n'
            "função principal()\n"
            "    exibir(m[\"soma\"](7, 5))\n"
            "fim\n"
        ),
        encoding="utf-8",
    )

    out_tbc = tmp_path / "app.tbc"
    _compilar_legado_python(root, app, out_tbc)

    run = subprocess.run(
        [str(native), "executar-tbc", str(out_tbc)],
        cwd=str(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "12"
