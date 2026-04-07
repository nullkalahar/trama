from __future__ import annotations

from pathlib import Path

from trama import testes_avancados_runtime


def test_v212_paridade_python_nativo_fluxos_criticos(tmp_path: Path) -> None:
    out = testes_avancados_runtime.executar_paridade_python_nativo_fluxos_criticos(
        diretorio_trabalho=str(tmp_path / "paridade")
    )
    assert out["ok"] is True
    checks = list(out["checks"])
    assert len(checks) >= 3
    assert all(bool(item["ok"]) for item in checks)


def test_v212_suite_critica_relatorios(tmp_path: Path) -> None:
    rel = testes_avancados_runtime.executar_suite_v212(
        diretorio_relatorio=str(tmp_path),
        perfil="rapido",
    )
    assert rel["ok"] is True
    assert rel["versao"] == "2.1.2"
    assert "latencia_p95_ms" in rel["baseline"]

    arq_json = tmp_path / "v212.json"
    arq_md = tmp_path / "v212.md"
    out_json = testes_avancados_runtime.salvar_relatorio_json(rel, str(arq_json))
    out_md = testes_avancados_runtime.salvar_relatorio_markdown(rel, str(arq_md))
    assert out_json["ok"] is True and arq_json.exists()
    assert out_md["ok"] is True and arq_md.exists()
