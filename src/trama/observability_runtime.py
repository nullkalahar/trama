"""Runtime de observabilidade (v0.8): logs estruturados, métricas e tracing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import json
import threading
import time
import uuid
from contextvars import ContextVar
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _labels_key(labels: dict[str, object] | None) -> tuple[tuple[str, str], ...]:
    if not labels:
        return tuple()
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


@dataclass
class _MetricPoint:
    kind: str
    name: str
    value: float
    labels: tuple[tuple[str, str], ...]
    at: float


_METRICS_LOCK = threading.Lock()
_METRIC_COUNTERS: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
_METRIC_OBSERVATIONS: list[_MetricPoint] = []

_TRACE_LOCK = threading.Lock()
_SPANS: dict[str, dict[str, Any]] = {}
_SPAN_EVENTS: list[dict[str, Any]] = []

_CORR_CTX: ContextVar[dict[str, object]] = ContextVar("trama_corr_ctx", default={})


def _normalizar_correlação(
    id_requisicao: object | None = None,
    id_traco: object | None = None,
    id_usuario: object | None = None,
) -> dict[str, object]:
    out: dict[str, object] = {}
    if id_requisicao:
        out["id_requisicao"] = str(id_requisicao)
        out["request_id"] = str(id_requisicao)
    if id_traco:
        out["id_traco"] = str(id_traco)
        out["trace_id"] = str(id_traco)
    if id_usuario:
        out["id_usuario"] = str(id_usuario)
        out["user_id"] = str(id_usuario)
    return out


def correlacao_definir(
    id_requisicao: object | None = None,
    id_traco: object | None = None,
    id_usuario: object | None = None,
) -> dict[str, object]:
    merged = dict(_CORR_CTX.get() or {})
    merged.update(_normalizar_correlação(id_requisicao, id_traco, id_usuario))
    _CORR_CTX.set(merged)
    return dict(merged)


def correlacao_obter() -> dict[str, object]:
    return dict(_CORR_CTX.get() or {})


def correlacao_limpar() -> None:
    _CORR_CTX.set({})


def log_estruturado(
    nivel: str,
    mensagem: object,
    contexto: dict[str, object] | None = None,
) -> dict[str, object]:
    corr = correlacao_obter()
    ctx = dict(contexto or {})
    for k, v in corr.items():
        ctx.setdefault(k, v)
    entry = {
        "ts": _now_iso(),
        "nivel": str(nivel).upper(),
        "mensagem": str(mensagem),
        "contexto": ctx,
    }
    for k in ("id_requisicao", "request_id", "id_traco", "trace_id", "id_usuario", "user_id"):
        if k in corr:
            entry[k] = corr[k]
    return entry


def log_estruturado_json(
    nivel: str,
    mensagem: object,
    contexto: dict[str, object] | None = None,
) -> str:
    return json.dumps(log_estruturado(nivel, mensagem, contexto), ensure_ascii=False, sort_keys=True)


def metrica_incrementar(nome: str, valor: float = 1.0, labels: dict[str, object] | None = None) -> None:
    key = (str(nome), _labels_key(labels))
    with _METRICS_LOCK:
        _METRIC_COUNTERS[key] = float(_METRIC_COUNTERS.get(key, 0.0) + float(valor))


def metrica_observar(nome: str, valor: float, labels: dict[str, object] | None = None) -> None:
    point = _MetricPoint(
        kind="histogram",
        name=str(nome),
        value=float(valor),
        labels=_labels_key(labels),
        at=time.time(),
    )
    with _METRICS_LOCK:
        _METRIC_OBSERVATIONS.append(point)


def metricas_snapshot() -> dict[str, object]:
    with _METRICS_LOCK:
        counters = [
            {"nome": name, "labels": dict(labels), "valor": value}
            for (name, labels), value in sorted(_METRIC_COUNTERS.items(), key=lambda x: x[0][0])
        ]
        observations = [
            {
                "tipo": p.kind,
                "nome": p.name,
                "labels": dict(p.labels),
                "valor": p.value,
                "at": p.at,
            }
            for p in _METRIC_OBSERVATIONS
        ]
    return {"counters": counters, "observacoes": observations}


def metricas_reset() -> None:
    with _METRICS_LOCK:
        _METRIC_COUNTERS.clear()
        _METRIC_OBSERVATIONS.clear()


def traco_iniciar(nome: str, atributos: dict[str, object] | None = None) -> dict[str, object]:
    corr = correlacao_obter()
    span_id = uuid.uuid4().hex
    span = {
        "id": span_id,
        "nome": str(nome),
        "atributos": dict(atributos or {}),
        "status": "aberto",
        "inicio_ts": _now_iso(),
        "inicio_epoch": time.time(),
        "fim_ts": None,
        "duracao_ms": None,
        "erro": None,
    }
    span.update({k: v for k, v in corr.items() if k in {"id_requisicao", "id_traco", "id_usuario"}})
    with _TRACE_LOCK:
        _SPANS[span_id] = span
    return dict(span)


def traco_evento(span: dict[str, object], nome: str, atributos: dict[str, object] | None = None) -> dict[str, object]:
    span_id = str(span.get("id"))
    event = {
        "span_id": span_id,
        "nome": str(nome),
        "atributos": dict(atributos or {}),
        "ts": _now_iso(),
        "epoch": time.time(),
    }
    with _TRACE_LOCK:
        _SPAN_EVENTS.append(event)
    return dict(event)


def traco_finalizar(
    span: dict[str, object],
    status: str = "ok",
    erro: object | None = None,
) -> dict[str, object]:
    span_id = str(span.get("id"))
    with _TRACE_LOCK:
        current = _SPANS.get(span_id)
        if current is None:
            raise RuntimeError("span inválido")
        if current["status"] != "aberto":
            return dict(current)
        end = time.time()
        current["status"] = str(status)
        current["erro"] = None if erro is None else str(erro)
        current["fim_ts"] = _now_iso()
        current["duracao_ms"] = (end - float(current["inicio_epoch"])) * 1000.0
        _SPANS[span_id] = current
        return dict(current)


def tracos_snapshot() -> dict[str, object]:
    with _TRACE_LOCK:
        spans = [dict(v) for _, v in sorted(_SPANS.items(), key=lambda x: x[1]["inicio_epoch"])]
        events = [dict(e) for e in _SPAN_EVENTS]
    return {"spans": spans, "eventos": events}


def tracos_reset() -> None:
    with _TRACE_LOCK:
        _SPANS.clear()
        _SPAN_EVENTS.clear()


def registrar_http_metrica(
    metodo: str,
    rota: str,
    status: int,
    latencia_ms: float,
    id_requisicao: str | None = None,
    id_traco: str | None = None,
    id_usuario: str | None = None,
) -> None:
    labels_base: dict[str, object] = {
        "metodo": metodo,
        "rota": rota,
        "status": int(status),
    }
    if id_requisicao:
        labels_base["id_requisicao"] = id_requisicao
    if id_traco:
        labels_base["id_traco"] = id_traco
    if id_usuario:
        labels_base["id_usuario"] = id_usuario
    metrica_incrementar("http.requisicoes_total", 1, labels_base)
    metrica_observar("http.latencia_ms", float(latencia_ms), labels_base)
    if int(status) >= 500:
        metrica_incrementar("http.erros_total", 1, labels_base)


def registrar_db_metrica(
    operacao: str,
    backend: str,
    latencia_ms: float,
    sucesso: bool,
) -> None:
    labels = {"operacao": operacao, "backend": backend, "sucesso": str(bool(sucesso)).lower()}
    metrica_incrementar("db.operacoes_total", 1, labels)
    metrica_observar("db.latencia_ms", float(latencia_ms), labels)
    if not sucesso:
        metrica_incrementar("db.erros_total", 1, labels)


def registrar_runtime_metrica(
    componente: str,
    evento: str,
    valor: float = 1.0,
    labels: dict[str, object] | None = None,
) -> None:
    lb = {"componente": componente, "evento": evento}
    lb.update(dict(labels or {}))
    metrica_incrementar("runtime.eventos_total", float(valor), lb)


def _sum_counter(name: str) -> float:
    snap = metricas_snapshot()
    total = 0.0
    for c in snap.get("counters", []):
        if c.get("nome") == name:
            total += float(c.get("valor", 0.0))
    return total


def _observacoes_por_nome(name: str) -> list[float]:
    snap = metricas_snapshot()
    values: list[float] = []
    for o in snap.get("observacoes", []):
        if o.get("nome") == name:
            values.append(float(o.get("valor", 0.0)))
    return values


def _percentil(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    pos = min(len(sorted_values) - 1, max(0, int(round((len(sorted_values) - 1) * p))))
    return float(sorted_values[pos])


def alertas_avaliar(config: dict[str, object] | None = None) -> dict[str, object]:
    cfg = dict(config or {})
    erro_pct_limite = float(cfg.get("erro_percentual_limite", os.getenv("TRAMA_ALERTA_ERRO_PERCENTUAL", "5")))
    latencia_ms_limite = float(cfg.get("latencia_ms_limite", os.getenv("TRAMA_ALERTA_LATENCIA_MS", "500")))
    req_minimas = int(cfg.get("requisicoes_minimas", os.getenv("TRAMA_ALERTA_REQ_MINIMAS", "20")))

    req_total = _sum_counter("http.requisicoes_total")
    req_erro = _sum_counter("http.erros_total")
    taxa_erro = (req_erro / req_total * 100.0) if req_total > 0 else 0.0
    latencias = _observacoes_por_nome("http.latencia_ms")
    p95 = _percentil(latencias, 0.95)

    ativos: list[dict[str, object]] = []
    if req_total >= req_minimas and taxa_erro >= erro_pct_limite:
        ativos.append(
            {
                "codigo": "ERRO_HTTP_ALTO",
                "mensagem": "Taxa de erro HTTP acima do limite.",
                "detalhes": {"taxa_erro_pct": taxa_erro, "limite_pct": erro_pct_limite, "requisicoes": req_total},
            }
        )
    if req_total >= req_minimas and p95 >= latencia_ms_limite:
        ativos.append(
            {
                "codigo": "LATENCIA_HTTP_ALTA",
                "mensagem": "Latência HTTP p95 acima do limite.",
                "detalhes": {"p95_ms": p95, "limite_ms": latencia_ms_limite, "requisicoes": req_total},
            }
        )

    estado = "ok" if not ativos else "degradado"
    return {
        "estado": estado,
        "ativos": ativos,
        "resumo": {
            "requisicoes_total": req_total,
            "erros_total": req_erro,
            "taxa_erro_pct": taxa_erro,
            "latencia_p95_ms": p95,
        },
        "limites": {
            "erro_percentual_limite": erro_pct_limite,
            "latencia_ms_limite": latencia_ms_limite,
            "requisicoes_minimas": req_minimas,
        },
    }


def observabilidade_resumo(config_alerta: dict[str, object] | None = None) -> dict[str, object]:
    alertas = alertas_avaliar(config_alerta)
    return {
        "ok": alertas["estado"] == "ok",
        "estado": alertas["estado"],
        "metricas": metricas_snapshot(),
        "tracos": tracos_snapshot(),
        "alertas": alertas,
        "ts": _now_iso(),
    }


def exportar_prometheus() -> str:
    snap = metricas_snapshot()
    linhas: list[str] = []
    linhas.append("# HELP trama_runtime_info Informacoes basicas do runtime Trama")
    linhas.append("# TYPE trama_runtime_info gauge")
    linhas.append('trama_runtime_info{runtime="python",linguagem="trama"} 1')
    for c in snap.get("counters", []):
        nome = str(c.get("nome", "")).strip().replace(".", "_")
        if not nome:
            continue
        labels_map = dict(c.get("labels", {}))
        labels_txt = ",".join(f'{str(k)}="{str(v)}"' for k, v in sorted(labels_map.items()))
        labels_fmt = "{" + labels_txt + "}" if labels_txt else ""
        linhas.append(f"{nome}{labels_fmt} {float(c.get('valor', 0.0))}")
    for o in snap.get("observacoes", []):
        nome = str(o.get("nome", "")).strip().replace(".", "_")
        if not nome:
            continue
        labels_map = dict(o.get("labels", {}))
        labels_txt = ",".join(f'{str(k)}="{str(v)}"' for k, v in sorted(labels_map.items()))
        labels_fmt = "{" + labels_txt + "}" if labels_txt else ""
        linhas.append(f"{nome}_observacao{labels_fmt} {float(o.get('valor', 0.0))}")
    return "\n".join(linhas) + "\n"


def exportar_otel_json() -> dict[str, object]:
    snap_m = metricas_snapshot()
    snap_t = tracos_snapshot()
    corr = correlacao_obter()
    metricas = []
    for c in snap_m.get("counters", []):
        metricas.append(
            {
                "name": c.get("nome"),
                "kind": "sum",
                "value": float(c.get("valor", 0.0)),
                "attributes": dict(c.get("labels", {})),
            }
        )
    for o in snap_m.get("observacoes", []):
        metricas.append(
            {
                "name": o.get("nome"),
                "kind": "gauge",
                "value": float(o.get("valor", 0.0)),
                "attributes": dict(o.get("labels", {})),
            }
        )
    spans = []
    for s in snap_t.get("spans", []):
        spans.append(
            {
                "trace_id": str(s.get("id_traco") or corr.get("id_traco") or ""),
                "span_id": str(s.get("id", "")),
                "name": str(s.get("nome", "")),
                "status": str(s.get("status", "")),
                "start_time": s.get("inicio_ts"),
                "end_time": s.get("fim_ts"),
                "attributes": dict(s.get("atributos", {})),
            }
        )
    eventos = []
    for e in snap_t.get("eventos", []):
        eventos.append(
            {
                "span_id": str(e.get("span_id", "")),
                "name": str(e.get("nome", "")),
                "time": e.get("ts"),
                "attributes": dict(e.get("atributos", {})),
            }
        )
    return {
        "resource": {"service.name": "trama"},
        "metrics": metricas,
        "spans": spans,
        "events": eventos,
        "correlacao": corr,
        "gerado_em": _now_iso(),
    }


def operacao_validar_config(obrigatorios: list[str]) -> dict[str, object]:
    faltando = [k for k in obrigatorios if not k]
    return {"ok": len(faltando) == 0, "faltando": faltando}
