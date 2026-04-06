from __future__ import annotations

from pathlib import Path

from trama import testes_avancados_runtime


def test_v208_harness_integracao_sqlite(tmp_path: Path) -> None:
    out = testes_avancados_runtime.executar_harness_integracao(
        diretorio_base=str(tmp_path / "fixtures"),
        validar_postgres=False,
        validar_redis=False,
    )
    assert out["ok"] is True
    assert out["sqlite"]["ok"] is True
    assert int(out["sqlite"]["total_pedidos"]) >= 1


def test_v208_suite_e2e_fluxos_criticos() -> None:
    out = testes_avancados_runtime.executar_suite_e2e_fluxos_criticos()
    assert out["ok"] is True
    assert len(out["checks"]) >= 4
    assert all(bool(x["ok"]) for x in out["checks"])


def test_v208_regressao_contrato_api() -> None:
    out = testes_avancados_runtime.executar_regressao_contrato_api()
    assert out["ok"] is True
    assert len(out["checks"]) >= 2


def test_v208_carga_concorrencia_com_slo_reproduzivel() -> None:
    out = testes_avancados_runtime.executar_teste_carga_concorrencia(
        total_requisicoes=80,
        concorrencia=8,
        slo_p95_ms_max=1500.0,
        slo_erro_pct_max=1.0,
        slo_throughput_min_rps=10.0,
    )
    assert out["ok"] is True
    m = out["metricas"]
    assert float(m["latencia_p95_ms"]) >= 0.0
    assert float(m["throughput_rps"]) > 0.0
    assert float(m["erro_pct"]) <= 1.0


def test_v208_caos_falha_parcial_controlada() -> None:
    out = testes_avancados_runtime.executar_teste_caos_falha_parcial()
    assert out["ok"] is True
    assert len(out["checks"]) >= 3


def test_v208_relatorios_json_markdown(tmp_path: Path) -> None:
    rel = testes_avancados_runtime.executar_suite_v208(
        diretorio_relatorio=str(tmp_path),
        validar_postgres=False,
        validar_redis=False,
        perfil="rapido",
    )
    assert rel["ok"] is True
    json_out = tmp_path / "v208.json"
    md_out = tmp_path / "v208.md"
    r1 = testes_avancados_runtime.salvar_relatorio_json(rel, str(json_out))
    r2 = testes_avancados_runtime.salvar_relatorio_markdown(rel, str(md_out))
    assert r1["ok"] is True and json_out.exists()
    assert r2["ok"] is True and md_out.exists()
