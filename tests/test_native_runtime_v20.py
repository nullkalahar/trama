from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_v20_native_executar_tbc_basico(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    build = subprocess.run(
        ["bash", str(root / "scripts" / "build_native_stub.sh")],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr

    src = tmp_path / "prog.trm"
    src.write_text("função principal()\n    exibir(5 + 7)\nfim\n", encoding="utf-8")
    out_tbc = tmp_path / "prog.tbc"

    py = root / ".venv" / "bin" / "python"
    comp = subprocess.run(
        [str(py), "-m", "trama.cli", "compilar-legado", str(src), "-o", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
    )
    assert comp.returncode == 0, comp.stderr

    native = root / "dist" / "native" / "trama-native"
    run = subprocess.run(
        [str(native), "executar-tbc", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "12"


def test_v20_native_alias_run_tbc(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    build = subprocess.run(
        ["bash", str(root / "scripts" / "build_native_stub.sh")],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr

    src = tmp_path / "prog.trm"
    src.write_text("função principal()\n    exibir(2 + 3)\nfim\n", encoding="utf-8")
    out_tbc = tmp_path / "prog.tbc"

    py = root / ".venv" / "bin" / "python"
    comp = subprocess.run(
        [str(py), "-m", "trama.cli", "compilar-legado", str(src), "-o", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
    )
    assert comp.returncode == 0, comp.stderr

    native = root / "dist" / "native" / "trama-native"
    run = subprocess.run(
        [str(native), "run-tbc", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "5"


def test_v20_native_diagnostico_campos_canonicos_e_compatibilidade() -> None:
    root = Path(__file__).resolve().parents[1]
    build = subprocess.run(
        ["bash", str(root / "scripts" / "build_native_stub.sh")],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr

    native = root / "dist" / "native" / "trama-native"
    diag = subprocess.run(
        [str(native), "--diagnostico-runtime"],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert diag.returncode == 0, diag.stderr
    text = diag.stdout
    assert "backend_runtime=" in text
    assert "backend_compilador=" in text
    assert "requer_python_host=" in text
    assert "runtime_backend=" in text
    assert "compilador_backend=" in text
    assert "python_host_required=" in text


def test_v20_native_await_basico(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    build = subprocess.run(
        ["bash", str(root / "scripts" / "build_native_stub.sh")],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr

    src = tmp_path / "await.trm"
    src.write_text(
        (
            "assíncrona função soma(a, b)\n"
            "    retorne a + b\n"
            "fim\n"
            "assíncrona função principal()\n"
            "    exibir(aguarde soma(20, 22))\n"
            "fim\n"
        ),
        encoding="utf-8",
    )
    out_tbc = tmp_path / "await.tbc"
    py = root / ".venv" / "bin" / "python"
    comp = subprocess.run(
        [str(py), "-m", "trama.cli", "compilar-legado", str(src), "-o", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
    )
    assert comp.returncode == 0, comp.stderr
    native = root / "dist" / "native" / "trama-native"
    run = subprocess.run(
        [str(native), "executar-tbc", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "42"


def test_v20_native_throw_pegue(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    build = subprocess.run(
        ["bash", str(root / "scripts" / "build_native_stub.sh")],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    src = tmp_path / "try.trm"
    src.write_text(
        (
            "função principal()\n"
            "    tente\n"
            "        lance \"erro\"\n"
            "    pegue e\n"
            "        exibir(e)\n"
            "    fim\n"
            "fim\n"
        ),
        encoding="utf-8",
    )
    out_tbc = tmp_path / "try.tbc"
    py = root / ".venv" / "bin" / "python"
    comp = subprocess.run(
        [str(py), "-m", "trama.cli", "compilar-legado", str(src), "-o", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
    )
    assert comp.returncode == 0, comp.stderr
    native = root / "dist" / "native" / "trama-native"
    run = subprocess.run(
        [str(native), "executar-tbc", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert "erro" in run.stdout


def test_v20_native_import_tbc(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    build = subprocess.run(
        ["bash", str(root / "scripts" / "build_native_stub.sh")],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    mod_src = tmp_path / "mod.trm"
    mod_src.write_text("função soma(a, b)\n    retorne a + b\nfim\n", encoding="utf-8")
    app_src = tmp_path / "app.trm"
    app_src.write_text(
        (
            "importe \"mod.trm\" como m\n"
            "função principal()\n"
            "    exibir(m[\"soma\"](7, 8))\n"
            "fim\n"
        ),
        encoding="utf-8",
    )
    py = root / ".venv" / "bin" / "python"
    for source in (mod_src, app_src):
        out_tbc = source.with_suffix(".tbc")
        comp = subprocess.run(
            [str(py), "-m", "trama.cli", "compilar-legado", str(source), "-o", str(out_tbc)],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(root / "src")},
        )
        assert comp.returncode == 0, comp.stderr
    native = root / "dist" / "native" / "trama-native"
    run = subprocess.run(
        [str(native), "executar-tbc", str(app_src.with_suffix(".tbc"))],
        cwd=str(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "15"


def test_v20_native_executar_e_compilar_via_cli_standalone(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    build = subprocess.run(
        ["bash", str(root / "scripts" / "build_native_stub.sh")],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    src = tmp_path / "prog.trm"
    src.write_text("função principal()\n    exibir(99)\nfim\n", encoding="utf-8")
    out_tbc = tmp_path / "prog.tbc"
    native = root / "dist" / "native" / "trama-native"

    run_exec = subprocess.run(
        [str(native), "executar", str(src)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_exec.returncode == 0, run_exec.stderr
    assert run_exec.stdout.strip() == "99"

    run_comp = subprocess.run(
        [str(native), "compilar", str(src), "-o", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_comp.returncode == 0, run_comp.stderr
    assert out_tbc.exists()
