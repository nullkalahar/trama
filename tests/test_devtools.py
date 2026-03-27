from __future__ import annotations

import json
from pathlib import Path

from trama.devtools import coverage_trm, format_trm, gerar_template_backend, lint_trm, run_test_runner


def test_test_runner_lint_format_coverage(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "mod.trm").write_text("função dobro(x)\n    retorne x * 2\nfim\n", encoding="utf-8")
    (src / "test_ok.trm").write_text(
        "importe \"mod.trm\" como m\nfunção principal()\n    exibir(m[\"dobro\"](2))\nfim\n",
        encoding="utf-8",
    )
    (src / "bad.trm").write_text("retorne 1\n", encoding="utf-8")

    test_report = run_test_runner(str(src))
    assert test_report["total"] == 1
    assert test_report["aprovados"] == 1
    assert test_report["falhos"] == 0

    lint_report = lint_trm(str(src))
    assert lint_report["ok"] is False
    assert len(lint_report["erros"]) == 1

    fmt_target = src / "fmt.trm"
    fmt_target.write_text("função principal()\t\n    exibir(\"x\")    \n\n\nfim", encoding="utf-8")
    fmt_preview = format_trm(str(fmt_target), write=False)
    assert fmt_preview["total_alterados"] == 1
    fmt_apply = format_trm(str(fmt_target), write=True)
    assert fmt_apply["total_alterados"] == 1
    assert fmt_target.read_text(encoding="utf-8").endswith("\n")

    cov = coverage_trm(str(src))
    assert cov["ok"] is True
    assert isinstance(cov["cobertura_percentual"], float)


def test_gerar_template_backend(tmp_path: Path) -> None:
    dst = tmp_path / "template"
    out = gerar_template_backend(str(dst))
    assert out["ok"] is True
    assert (dst / "src" / "app.trm").exists()
    assert (dst / "tests" / "test_smoke.trm").exists()
    assert (dst / "config" / ".env.exemplo").exists()
    assert "Projeto backend Trama" in (dst / "README.md").read_text(encoding="utf-8")
    json.dumps(out)
