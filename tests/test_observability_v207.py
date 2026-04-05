from __future__ import annotations

from trama import observability_runtime


def test_v207_exportadores_prometheus_e_otel_com_correlacao() -> None:
    observability_runtime.metricas_reset()
    observability_runtime.tracos_reset()
    observability_runtime.correlacao_limpar()

    observability_runtime.correlacao_definir("req-207", "traco-207", "user-207")
    observability_runtime.registrar_http_metrica("GET", "/api/v1/itens", 200, 23.4, "req-207", "traco-207", "user-207")
    span = observability_runtime.traco_iniciar("http.requisicao", {"rota": "/api/v1/itens"})
    observability_runtime.traco_evento(span, "resposta", {"status": 200})
    observability_runtime.traco_finalizar(span, "ok")

    prom = observability_runtime.exportar_prometheus()
    assert "trama_runtime_info" in prom
    assert "http_requisicoes_total" in prom
    assert 'id_requisicao="req-207"' in prom

    otel = observability_runtime.exportar_otel_json()
    assert otel["resource"]["service.name"] == "trama"
    assert isinstance(otel["metrics"], list)
    assert isinstance(otel["spans"], list)
    assert isinstance(otel["events"], list)
    assert otel["correlacao"]["id_requisicao"] == "req-207"
    assert any(m["name"] == "http.requisicoes_total" for m in otel["metrics"])
    assert any(s["name"] == "http.requisicao" for s in otel["spans"])
