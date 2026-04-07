from __future__ import annotations

from pathlib import Path


def test_ci_v212_tem_suite_critica_e_gate() -> None:
    root = Path(__file__).resolve().parents[1]
    conteudo = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "name: ci_trama_v212" in conteudo
    assert "suite_critica_v212" in conteudo
    assert "gate_v212_obrigatorio" in conteudo
    assert "testes-avancados-v212" in conteudo


def test_release_v212_publica_checksum_e_rollback() -> None:
    root = Path(__file__).resolve().parents[1]
    conteudo = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "name: release_trama_v212" in conteudo
    assert "SHA256SUMS.txt" in conteudo
    assert "ROLLBACK.md" in conteudo
