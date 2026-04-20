from __future__ import annotations

from pathlib import Path

from trama import testes_avancados_runtime


def test_v213_suite_critica_relatorios(tmp_path: Path) -> None:
    rel = testes_avancados_runtime.executar_suite_v213(
        diretorio_relatorio=str(tmp_path),
        perfil="rapido",
    )
    assert rel["ok"] is True
    assert rel["versao"] == "2.1.3"
    assert "latencia_p95_ms" in rel["baseline"]
    assert "contrato_http_v213" in rel["suites"]
    assert "integracao_backend_v213" in rel["suites"]
    assert "dados_nativos_v213" in rel["suites"]
    assert "e2e_frontend_v213" in rel["suites"]
    assert "operacao_sre_v213" in rel["suites"]
    assert "baseline_v213" in rel["suites"]
    assert "caos_v213" in rel["suites"]
    integ = dict(rel["suites"]["integracao_backend_v213"] or {})
    assert dict(integ.get("arls_backend") or {}).get("ok") is True

    arq_json = tmp_path / "v213.json"
    arq_md = tmp_path / "v213.md"
    out_json = testes_avancados_runtime.salvar_relatorio_json(rel, str(arq_json))
    out_md = testes_avancados_runtime.salvar_relatorio_markdown(rel, str(arq_md))
    assert out_json["ok"] is True and arq_json.exists()
    assert out_md["ok"] is True and arq_md.exists()
