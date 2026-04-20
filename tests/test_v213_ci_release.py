from __future__ import annotations

from pathlib import Path


def test_ci_v213_tem_suite_critica_e_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    conteudo = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "suite_critica_v213" in conteudo
    assert "gate_v213_obrigatorio" in conteudo
    assert "testes-avancados-v213" in conteudo


def test_readme_v213_aponta_todo_e_fases() -> None:
    root = Path(__file__).resolve().parents[1]
    conteudo = (root / "README.md").read_text(encoding="utf-8")
    assert "TODO_V2_1_3_IMPLEMENTACAO_TOTAL.md" in conteudo
    assert "v2.1.3-alpha.1" in conteudo
    assert "v2.1.3-beta.1" in conteudo
    assert "v2.1.3-rc.1" in conteudo


def test_runtime_nativo_tem_flag_version() -> None:
    root = Path(__file__).resolve().parents[1]
    conteudo = (root / "native" / "trama_native.c").read_text(encoding="utf-8")
    assert "--version" in conteudo
