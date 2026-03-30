from __future__ import annotations

from trama import observability_runtime


def test_correlacao_contexto_log_traco() -> None:
    observability_runtime.metricas_reset()
    observability_runtime.tracos_reset()
    observability_runtime.correlacao_limpar()
    observability_runtime.correlacao_definir("r-1", "t-1", "u-1")

    entry = observability_runtime.log_estruturado("info", "ok", {})
    assert entry["id_requisicao"] == "r-1"
    assert entry["id_traco"] == "t-1"
    assert entry["id_usuario"] == "u-1"
    assert entry["request_id"] == "r-1"
    assert entry["trace_id"] == "t-1"
    assert entry["user_id"] == "u-1"

    span = observability_runtime.traco_iniciar("req", {})
    assert span["id_requisicao"] == "r-1"
    assert span["id_traco"] == "t-1"
    assert span["id_usuario"] == "u-1"
    observability_runtime.traco_finalizar(span, "ok")
    observability_runtime.correlacao_limpar()


def test_alertas_avaliar_degradado() -> None:
    observability_runtime.metricas_reset()
    observability_runtime.metrica_incrementar("http.requisicoes_total", 100, {"rota": "/x"})
    observability_runtime.metrica_incrementar("http.erros_total", 20, {"rota": "/x"})
    for _ in range(100):
        observability_runtime.metrica_observar("http.latencia_ms", 1200.0, {"rota": "/x"})
    out = observability_runtime.alertas_avaliar(
        {"erro_percentual_limite": 5.0, "latencia_ms_limite": 500.0, "requisicoes_minimas": 10}
    )
    assert out["estado"] == "degradado"
    assert len(out["ativos"]) >= 1
