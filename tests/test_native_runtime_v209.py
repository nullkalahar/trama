from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
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


def test_v209_compilar_e_executar_nativos_sem_ponte(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    native = _build_native(root, tmp_path)

    src = tmp_path / "prog.trm"
    src.write_text("função principal()\n    exibir(1 + 2)\nfim\n", encoding="utf-8")
    out_tbc = tmp_path / "prog.tbc"

    comp = subprocess.run(
        [str(native), "compilar", str(src), "-o", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert comp.returncode == 0, comp.stderr
    assert out_tbc.exists()

    run_tbc = subprocess.run(
        [str(native), "executar-tbc", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_tbc.returncode == 0, run_tbc.stderr
    assert run_tbc.stdout.strip() == "3"

    run_src = subprocess.run(
        [str(native), "executar", str(src)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_src.returncode == 0, run_src.stderr
    assert run_src.stdout.strip() == "3"


def test_v209_import_trm_direto_em_runtime_nativo(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    native = _build_native(root, tmp_path)

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
    app_tbc = tmp_path / "app.tbc"
    comp = subprocess.run(
        [str(py), "-m", "trama.cli", "compilar-legado", str(app_src), "-o", str(app_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
    )
    assert comp.returncode == 0, comp.stderr
    assert not (tmp_path / "mod.tbc").exists()

    run = subprocess.run(
        [str(native), "executar-tbc", str(app_tbc)],
        cwd=str(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "15"
    assert (tmp_path / "mod.tbc").exists()


def test_v209_async_scheduler_tarefas_timeout_cancelamento(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    native = _build_native(root, tmp_path)
    src = tmp_path / "async.trm"
    src.write_text(
        (
            "assíncrona função soma(a, b)\n"
            "    retorne a + b\n"
            "fim\n"
            "assíncrona função principal()\n"
            "    t1 = criar_tarefa(soma(20, 22))\n"
            "    t2 = criar_tarefa(soma(1, 2))\n"
            "    cancelar_tarefa(t2)\n"
            "    v1 = aguarde com_timeout(t1, 1.0)\n"
            "    exibir(v1)\n"
            "fim\n"
        ),
        encoding="utf-8",
    )
    out_tbc = tmp_path / "async.tbc"
    comp = subprocess.run(
        [str(native), "compilar", str(src), "-o", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert comp.returncode == 0, comp.stderr
    run = subprocess.run(
        [str(native), "executar-tbc", str(out_tbc)],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "42"


def test_v209_diagnostico_100_por_cento_nativo() -> None:
    root = Path(__file__).resolve().parents[1]
    tmp_path = Path(tempfile.mkdtemp(prefix="trama-native-v209-"))
    native = _build_native(root, tmp_path)
    diag = subprocess.run(
        [str(native), "--diagnostico-runtime"],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    assert diag.returncode == 0, diag.stderr
    txt = diag.stdout
    assert "backend_runtime=nativo_c_vm" in txt
    assert "backend_compilador=nativo_c_compilador" in txt
    assert "requer_python_host=nao" in txt
