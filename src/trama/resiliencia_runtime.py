"""Runtime de resiliência: retry/backoff/timeout/circuit-breaker (v1.1)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import random
import threading
import time
from typing import Any, Awaitable, Callable


class ResilienciaError(RuntimeError):
    """Erro base do runtime de resiliência."""


class CircuitoAbertoError(ResilienciaError):
    """Erro quando o circuito está aberto."""


@dataclass
class _EstadoCircuito:
    estado: str = "fechado"
    falhas_consecutivas: int = 0
    aberto_ate: float = 0.0
    ultima_falha: str | None = None
    ultima_transicao: float = 0.0


_LOCK = threading.RLock()
_ESTADOS: dict[str, _EstadoCircuito] = {}


def _get_estado(nome: str) -> _EstadoCircuito:
    with _LOCK:
        estado = _ESTADOS.get(nome)
        if estado is None:
            estado = _EstadoCircuito(ultima_transicao=time.monotonic())
            _ESTADOS[nome] = estado
        return estado


def circuito_status(nome: str) -> dict[str, object]:
    estado = _get_estado(nome)
    with _LOCK:
        return {
            "nome": nome,
            "estado": estado.estado,
            "falhas_consecutivas": estado.falhas_consecutivas,
            "aberto_ate": estado.aberto_ate,
            "ultima_falha": estado.ultima_falha,
            "ultima_transicao": estado.ultima_transicao,
        }


def circuito_reset(nome: str | None = None) -> None:
    with _LOCK:
        if nome is None:
            _ESTADOS.clear()
            return
        _ESTADOS.pop(nome, None)


def _deve_retentar(exc: Exception, classes_nao_retentaveis: tuple[type[BaseException], ...]) -> bool:
    if isinstance(exc, asyncio.CancelledError):
        return False
    return not isinstance(exc, classes_nao_retentaveis)


def _transicao_aberto(nome: str, estado: _EstadoCircuito, reset_timeout_segundos: float, erro: Exception) -> None:
    estado.estado = "aberto"
    estado.aberto_ate = time.monotonic() + max(0.001, float(reset_timeout_segundos))
    estado.ultima_falha = str(erro)
    estado.ultima_transicao = time.monotonic()
    _ESTADOS[nome] = estado


def _transicao_fechado(nome: str, estado: _EstadoCircuito) -> None:
    estado.estado = "fechado"
    estado.falhas_consecutivas = 0
    estado.aberto_ate = 0.0
    estado.ultima_falha = None
    estado.ultima_transicao = time.monotonic()
    _ESTADOS[nome] = estado


def _registrar_falha(
    nome: str,
    estado: _EstadoCircuito,
    max_falhas: int,
    reset_timeout_segundos: float,
    erro: Exception,
) -> None:
    estado.falhas_consecutivas += 1
    estado.ultima_falha = str(erro)
    estado.ultima_transicao = time.monotonic()
    if estado.falhas_consecutivas >= max_falhas:
        _transicao_aberto(nome, estado, reset_timeout_segundos, erro)
    else:
        _ESTADOS[nome] = estado


async def executar(
    nome: str,
    operacao: Callable[[], Awaitable[object]],
    *,
    tentativas: int = 3,
    timeout_segundos: float | None = None,
    max_falhas: int = 5,
    reset_timeout_segundos: float = 30.0,
    base_backoff_segundos: float = 0.1,
    max_backoff_segundos: float = 2.0,
    jitter_segundos: float = 0.05,
    excecoes_nao_retentaveis: tuple[type[BaseException], ...] = (),
) -> object:
    if tentativas < 1:
        raise ResilienciaError("tentativas deve ser >= 1.")
    if max_falhas < 1:
        raise ResilienciaError("max_falhas deve ser >= 1.")

    estado = _get_estado(nome)

    with _LOCK:
        agora = time.monotonic()
        if estado.estado == "aberto":
            if agora < estado.aberto_ate:
                raise CircuitoAbertoError(f"Circuito '{nome}' aberto até {estado.aberto_ate:.3f}.")
            estado.estado = "meio_aberto"
            estado.ultima_transicao = agora
            _ESTADOS[nome] = estado

    ultima_exc: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        try:
            task = operacao()
            resultado = await asyncio.wait_for(task, timeout=timeout_segundos) if timeout_segundos else await task
            with _LOCK:
                estado_atual = _get_estado(nome)
                if estado_atual.estado in {"meio_aberto", "aberto"}:
                    _transicao_fechado(nome, estado_atual)
                else:
                    estado_atual.falhas_consecutivas = 0
                    estado_atual.ultima_falha = None
                    _ESTADOS[nome] = estado_atual
            return resultado
        except Exception as exc:  # noqa: BLE001
            ultima_exc = exc
            with _LOCK:
                estado_atual = _get_estado(nome)
                _registrar_falha(
                    nome,
                    estado_atual,
                    max_falhas=max_falhas,
                    reset_timeout_segundos=reset_timeout_segundos,
                    erro=exc,
                )

            if tentativa >= tentativas:
                break
            if not _deve_retentar(exc, excecoes_nao_retentaveis):
                break

            expoente = tentativa - 1
            backoff = min(max_backoff_segundos, max(0.0, base_backoff_segundos) * (2**expoente))
            jitter = random.uniform(0.0, max(0.0, jitter_segundos))
            await asyncio.sleep(backoff + jitter)

    if ultima_exc is not None:
        raise ultima_exc
    raise ResilienciaError("Falha desconhecida em execução resiliente.")
