"""Runtime de observabilidade (v0.8): logs estruturados, métricas e tracing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import threading
import time
import uuid
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


def log_estruturado(
    nivel: str,
    mensagem: object,
    contexto: dict[str, object] | None = None,
) -> dict[str, object]:
    entry = {
        "ts": _now_iso(),
        "nivel": str(nivel).upper(),
        "mensagem": str(mensagem),
        "contexto": dict(contexto or {}),
    }
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


def operacao_validar_config(obrigatorios: list[str]) -> dict[str, object]:
    faltando = [k for k in obrigatorios if not k]
    return {"ok": len(faltando) == 0, "faltando": faltando}
