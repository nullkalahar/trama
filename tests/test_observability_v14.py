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


def test_registro_metricas_http_db_runtime() -> None:
    observability_runtime.metricas_reset()

    observability_runtime.registrar_http_metrica(
        metodo="GET",
        rota="/itens/:id",
        status=200,
        latencia_ms=12.0,
        id_requisicao="r-http",
        id_traco="t-http",
        id_usuario="u-http",
    )
    observability_runtime.registrar_db_metrica(
        operacao="consultar",
        backend="sqlite",
        latencia_ms=3.0,
        sucesso=True,
    )
    observability_runtime.registrar_runtime_metrica(
        componente="jobs",
        evento="processado",
        valor=2,
        labels={"fila": "emails"},
    )

    snap = observability_runtime.metricas_snapshot()
    nomes = {c["nome"] for c in snap["counters"]}
    assert "http.requisicoes_total" in nomes
    assert "db.operacoes_total" in nomes
    assert "runtime.eventos_total" in nomes


def test_observabilidade_resumo_ok_com_metricas_vazias() -> None:
    observability_runtime.metricas_reset()
    observability_runtime.tracos_reset()
    observability_runtime.correlacao_limpar()

    resumo = observability_runtime.observabilidade_resumo(
        config_alerta={
            "erro_percentual_limite": 1.0,
            "latencia_ms_limite": 1.0,
            "requisicoes_minimas": 999,
        }
    )
    assert resumo["ok"] is True
    assert resumo["estado"] == "ok"
    assert "metricas" in resumo
    assert "tracos" in resumo
    assert "alertas" in resumo
