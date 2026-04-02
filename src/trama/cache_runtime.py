"""Runtime de cache local/distribuído com TTL, invalidação e coalescência (v2.0.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
import fnmatch
import threading
import time
from typing import Any, Callable

from . import observability_runtime


class CacheErro(RuntimeError):
    """Erro base do runtime de cache."""


class CacheBackendIndisponivel(CacheErro):
    """Backend distribuído indisponível."""


@dataclass
class _Entry:
    value: object
    created_at: float
    expire_at: float | None

    def ttl_restante(self, now: float | None = None) -> float | None:
        if self.expire_at is None:
            return None
        atual = time.monotonic() if now is None else float(now)
        restante = self.expire_at - atual
        return restante if restante > 0 else 0.0


@dataclass
class _EventoBackplane:
    seq: int
    tipo: str
    namespace: str
    chave: str | None = None
    padrao: str | None = None
    at: float = field(default_factory=time.monotonic)


@dataclass
class _InFlight:
    cond: threading.Condition
    carregando: bool = True


class _BackplaneMemoria:
    def __init__(self, grupo: str) -> None:
        self.grupo = grupo
        self.lock = threading.RLock()
        self.disponivel = True
        self.seq = 0
        self.eventos: list[_EventoBackplane] = []
        self.store: dict[str, dict[str, _Entry]] = {}

    def _ensure_ns(self, namespace: str) -> None:
        if namespace not in self.store:
            self.store[namespace] = {}

    def _check(self) -> None:
        if not self.disponivel:
            raise CacheBackendIndisponivel(f"Backplane indisponível para grupo {self.grupo}.")

    def set_disponivel(self, disponivel: bool) -> None:
        with self.lock:
            self.disponivel = bool(disponivel)

    def upsert(self, namespace: str, chave: str, valor: object, ttl_segundos: float | None) -> None:
        with self.lock:
            self._check()
            self._ensure_ns(namespace)
            expire_at = None if ttl_segundos is None else (time.monotonic() + float(ttl_segundos))
            self.store[namespace][chave] = _Entry(value=valor, created_at=time.monotonic(), expire_at=expire_at)

    def get(self, namespace: str, chave: str) -> object | None:
        with self.lock:
            self._check()
            self._ensure_ns(namespace)
            entry = self.store[namespace].get(chave)
            if entry is None:
                return None
            if entry.expire_at is not None and entry.expire_at <= time.monotonic():
                self.store[namespace].pop(chave, None)
                return None
            return entry.value

    def get_entry(self, namespace: str, chave: str) -> _Entry | None:
        with self.lock:
            self._check()
            self._ensure_ns(namespace)
            entry = self.store[namespace].get(chave)
            if entry is None:
                return None
            if entry.expire_at is not None and entry.expire_at <= time.monotonic():
                self.store[namespace].pop(chave, None)
                return None
            return _Entry(value=entry.value, created_at=entry.created_at, expire_at=entry.expire_at)

    def remove(self, namespace: str, chave: str) -> bool:
        with self.lock:
            self._check()
            self._ensure_ns(namespace)
            return self.store[namespace].pop(chave, None) is not None

    def invalidar_padrao(self, namespace: str, padrao: str) -> int:
        with self.lock:
            self._check()
            self._ensure_ns(namespace)
            keys = [k for k in self.store[namespace] if fnmatch.fnmatch(k, padrao)]
            for key in keys:
                self.store[namespace].pop(key, None)
            return len(keys)

    def publicar_evento(
        self,
        tipo: str,
        namespace: str,
        *,
        chave: str | None = None,
        padrao: str | None = None,
    ) -> int:
        with self.lock:
            self._check()
            self.seq += 1
            self.eventos.append(
                _EventoBackplane(
                    seq=self.seq,
                    tipo=tipo,
                    namespace=namespace,
                    chave=chave,
                    padrao=padrao,
                )
            )
            return self.seq

    def coletar_eventos(self, desde_seq: int) -> list[_EventoBackplane]:
        with self.lock:
            self._check()
            return [e for e in self.eventos if e.seq > desde_seq]


_BACKPLANES_LOCK = threading.RLock()
_BACKPLANES: dict[str, _BackplaneMemoria] = {}


def _backplane(grupo: str) -> _BackplaneMemoria:
    g = (grupo or "padrao").strip() or "padrao"
    with _BACKPLANES_LOCK:
        if g not in _BACKPLANES:
            _BACKPLANES[g] = _BackplaneMemoria(g)
        return _BACKPLANES[g]


class CacheDistribuido:
    def __init__(
        self,
        *,
        grupo: str = "padrao",
        id_instancia: str | None = None,
        auto_sincronizar: bool = True,
    ) -> None:
        self.grupo = (grupo or "padrao").strip() or "padrao"
        self.id_instancia = (id_instancia or f"inst_{int(time.time()*1000)}_{id(self)}").strip()
        self.auto_sincronizar = bool(auto_sincronizar)
        self._lock = threading.RLock()
        self._store: dict[str, dict[str, _Entry]] = {}
        self._stats: dict[str, dict[str, float]] = {}
        self._lat: dict[str, dict[str, float]] = {}
        self._inflight: dict[tuple[str, str], _InFlight] = {}
        self._seq_aplicado = 0
        self._bp = _backplane(self.grupo)

    def _ns(self, namespace: str | None) -> str:
        return (namespace or "padrao").strip() or "padrao"

    def _ensure_ns(self, namespace: str) -> None:
        if namespace not in self._store:
            self._store[namespace] = {}
        if namespace not in self._stats:
            self._stats[namespace] = {
                "hits": 0,
                "misses": 0,
                "expirados": 0,
                "definicoes": 0,
                "remocoes": 0,
                "invalidacoes_locais": 0,
                "invalidacoes_remotas": 0,
                "falhas_backend": 0,
                "fallback_usado": 0,
                "coalescencia_espera": 0,
                "coalescencia_lider": 0,
            }

    def _obs_evento(self, evento: str, namespace: str, valor: float = 1.0, labels: dict[str, object] | None = None) -> None:
        lb = {"namespace": namespace, "grupo": self.grupo, "instancia": self.id_instancia}
        lb.update(dict(labels or {}))
        observability_runtime.registrar_runtime_metrica("cache_distribuido", evento, valor=valor, labels=lb)

    def _obs_latencia(self, operacao: str, namespace: str, dur_ms: float) -> None:
        lb = {"operacao": operacao, "namespace": namespace, "grupo": self.grupo, "instancia": self.id_instancia}
        observability_runtime.metrica_observar("cache_distribuido.latencia_ms", float(dur_ms), lb)
        with self._lock:
            agg = self._lat.setdefault(operacao, {"amostras": 0.0, "total_ms": 0.0})
            agg["amostras"] += 1.0
            agg["total_ms"] += float(dur_ms)

    def _expired(self, entry: _Entry, now: float) -> bool:
        return entry.expire_at is not None and entry.expire_at <= now

    def _sync_if_needed(self) -> int:
        if not self.auto_sincronizar:
            return 0
        return self.sincronizar_invalidez()

    def sincronizar_invalidez(self) -> int:
        start = time.perf_counter()
        aplicados = 0
        try:
            eventos = self._bp.coletar_eventos(self._seq_aplicado)
        except CacheBackendIndisponivel:
            with self._lock:
                for ns in self._stats:
                    self._stats[ns]["falhas_backend"] += 1
            return 0
        with self._lock:
            for ev in eventos:
                self._ensure_ns(ev.namespace)
                if ev.tipo == "invalidar_chave" and ev.chave is not None:
                    if self._store[ev.namespace].pop(ev.chave, None) is not None:
                        self._stats[ev.namespace]["invalidacoes_remotas"] += 1
                elif ev.tipo == "invalidar_padrao" and ev.padrao is not None:
                    keys = [k for k in self._store[ev.namespace] if fnmatch.fnmatch(k, ev.padrao)]
                    for k in keys:
                        self._store[ev.namespace].pop(k, None)
                    if keys:
                        self._stats[ev.namespace]["invalidacoes_remotas"] += len(keys)
                elif ev.tipo == "limpar_namespace":
                    qtd = len(self._store[ev.namespace])
                    if qtd:
                        self._store[ev.namespace].clear()
                        self._stats[ev.namespace]["invalidacoes_remotas"] += qtd
                self._seq_aplicado = max(self._seq_aplicado, ev.seq)
                aplicados += 1
        self._obs_latencia("sincronizar", "*", (time.perf_counter() - start) * 1000.0)
        return aplicados

    def definir(self, chave: str, valor: object, *, ttl_segundos: float | None = None, namespace: str = "padrao") -> object:
        ns = self._ns(namespace)
        if not isinstance(chave, str) or not chave:
            raise ValueError("cache_definir exige chave texto não vazia.")
        self._sync_if_needed()
        start = time.perf_counter()
        exp = None if ttl_segundos is None else (time.monotonic() + float(ttl_segundos))
        with self._lock:
            self._ensure_ns(ns)
            self._store[ns][chave] = _Entry(value=valor, created_at=time.monotonic(), expire_at=exp)
            self._stats[ns]["definicoes"] += 1
        try:
            self._bp.upsert(ns, chave, valor, ttl_segundos)
        except CacheBackendIndisponivel:
            with self._lock:
                self._stats[ns]["falhas_backend"] += 1
            self._obs_evento("backend_indisponivel", ns)
        self._obs_evento("definir", ns)
        self._obs_latencia("definir", ns, (time.perf_counter() - start) * 1000.0)
        return valor

    def obter(self, chave: str, padrao: object | None = None, *, namespace: str = "padrao") -> object:
        ns = self._ns(namespace)
        self._sync_if_needed()
        start = time.perf_counter()
        now = time.monotonic()
        with self._lock:
            self._ensure_ns(ns)
            entry = self._store[ns].get(chave)
            if entry is not None and not self._expired(entry, now):
                self._stats[ns]["hits"] += 1
                self._obs_evento("hit", ns)
                self._obs_latencia("obter", ns, (time.perf_counter() - start) * 1000.0)
                return entry.value
            if entry is not None and self._expired(entry, now):
                self._store[ns].pop(chave, None)
                self._stats[ns]["expirados"] += 1
            self._stats[ns]["misses"] += 1

        # read-through distribuído: tenta backend compartilhado
        try:
            entrada_backend = self._bp.get_entry(ns, chave)
        except CacheBackendIndisponivel:
            with self._lock:
                self._stats[ns]["falhas_backend"] += 1
            entrada_backend = None

        if entrada_backend is not None:
            with self._lock:
                ttl_restante = entrada_backend.ttl_restante(now)
                expire_at_local = None if ttl_restante is None else (time.monotonic() + ttl_restante)
                self._store[ns][chave] = _Entry(
                    value=entrada_backend.value,
                    created_at=time.monotonic(),
                    expire_at=expire_at_local,
                )
                self._stats[ns]["hits"] += 1
                self._stats[ns]["misses"] = max(0, self._stats[ns]["misses"] - 1)
            self._obs_evento("hit_readthrough", ns)
            self._obs_latencia("obter", ns, (time.perf_counter() - start) * 1000.0)
            return entrada_backend.value

        self._obs_evento("miss", ns)
        self._obs_latencia("obter", ns, (time.perf_counter() - start) * 1000.0)
        return padrao

    def existe(self, chave: str, *, namespace: str = "padrao") -> bool:
        sentinel = object()
        return self.obter(chave, sentinel, namespace=namespace) is not sentinel

    def remover(self, chave: str, *, namespace: str = "padrao") -> bool:
        ns = self._ns(namespace)
        self._sync_if_needed()
        start = time.perf_counter()
        with self._lock:
            self._ensure_ns(ns)
            removed = self._store[ns].pop(chave, None) is not None
            if removed:
                self._stats[ns]["remocoes"] += 1
        try:
            _ = self._bp.remove(ns, chave)
            self._bp.publicar_evento("invalidar_chave", ns, chave=chave)
        except CacheBackendIndisponivel:
            with self._lock:
                self._stats[ns]["falhas_backend"] += 1
        self._obs_evento("remover", ns, labels={"removido": str(removed).lower()})
        self._obs_latencia("remover", ns, (time.perf_counter() - start) * 1000.0)
        return removed

    def invalidar_chave(self, chave: str, *, namespace: str = "padrao") -> bool:
        ns = self._ns(namespace)
        self._sync_if_needed()
        with self._lock:
            self._ensure_ns(ns)
            removed = self._store[ns].pop(chave, None) is not None
            if removed:
                self._stats[ns]["invalidacoes_locais"] += 1
        try:
            self._bp.remove(ns, chave)
            self._bp.publicar_evento("invalidar_chave", ns, chave=chave)
        except CacheBackendIndisponivel:
            with self._lock:
                self._stats[ns]["falhas_backend"] += 1
        self._obs_evento("invalidar_chave", ns, labels={"removido": str(removed).lower()})
        return removed

    def invalidar_padrao(self, padrao: str, *, namespace: str = "padrao") -> int:
        ns = self._ns(namespace)
        if not isinstance(padrao, str) or not padrao:
            raise ValueError("cache_invalidar_padrao exige padrão texto não vazio.")
        self._sync_if_needed()
        start = time.perf_counter()
        with self._lock:
            self._ensure_ns(ns)
            keys = [k for k in self._store[ns] if fnmatch.fnmatch(k, padrao)]
            for key in keys:
                self._store[ns].pop(key, None)
            total = len(keys)
            if total:
                self._stats[ns]["invalidacoes_locais"] += total
        try:
            _ = self._bp.invalidar_padrao(ns, padrao)
            self._bp.publicar_evento("invalidar_padrao", ns, padrao=padrao)
        except CacheBackendIndisponivel:
            with self._lock:
                self._stats[ns]["falhas_backend"] += 1
        self._obs_evento("invalidar_padrao", ns, valor=float(total), labels={"padrao": padrao})
        self._obs_latencia("invalidar_padrao", ns, (time.perf_counter() - start) * 1000.0)
        return total

    def limpar(self, *, namespace: str | None = None) -> int:
        if namespace is None:
            total = 0
            for ns in list(self._store.keys()):
                total += self.limpar(namespace=ns)
            return total
        ns = self._ns(namespace)
        self._sync_if_needed()
        with self._lock:
            self._ensure_ns(ns)
            total = len(self._store[ns])
            self._store[ns].clear()
            if ns in self._stats:
                self._stats[ns] = {
                    "hits": 0,
                    "misses": 0,
                    "expirados": 0,
                    "definicoes": 0,
                    "remocoes": 0,
                    "invalidacoes_locais": 0,
                    "invalidacoes_remotas": 0,
                    "falhas_backend": 0,
                    "fallback_usado": 0,
                    "coalescencia_espera": 0,
                    "coalescencia_lider": 0,
                }
        try:
            self._bp.publicar_evento("limpar_namespace", ns)
        except CacheBackendIndisponivel:
            pass
        self._obs_evento("limpar", ns, valor=float(total))
        return total

    def aquecer(
        self,
        itens: dict[str, object] | list[dict[str, object]] | list[list[object]] | list[tuple[object, ...]],
        *,
        ttl_segundos: float | None = None,
        namespace: str = "padrao",
    ) -> int:
        total = 0
        if isinstance(itens, dict):
            for chave, valor in itens.items():
                self.definir(str(chave), valor, ttl_segundos=ttl_segundos, namespace=namespace)
                total += 1
            return total

        if not isinstance(itens, list):
            raise ValueError("cache_aquecer espera mapa ou lista.")

        for item in itens:
            if isinstance(item, dict):
                chave = str(item.get("chave"))
                valor = item.get("valor")
                ttl = item.get("ttl_segundos", ttl_segundos)
                self.definir(chave, valor, ttl_segundos=None if ttl is None else float(ttl), namespace=namespace)
                total += 1
                continue
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                chave = str(item[0])
                valor = item[1]
                ttl = float(item[2]) if len(item) >= 3 and item[2] is not None else ttl_segundos
                self.definir(chave, valor, ttl_segundos=ttl, namespace=namespace)
                total += 1
                continue
            raise ValueError("Item inválido em cache_aquecer; use mapa {'chave','valor'} ou tupla (chave, valor, ttl?).")
        return total

    def obter_ou_carregar(
        self,
        chave: str,
        carregador: Callable[[], object],
        *,
        ttl_segundos: float | None = None,
        namespace: str = "padrao",
        timeout_coalescencia_segundos: float = 2.0,
        fallback: object | None = None,
    ) -> object:
        ns = self._ns(namespace)
        valor = self.obter(chave, None, namespace=ns)
        if valor is not None:
            return valor

        k = (ns, chave)
        sou_lider = False
        cond: threading.Condition

        with self._lock:
            self._ensure_ns(ns)
            inflight = self._inflight.get(k)
            if inflight is None:
                cond = threading.Condition(self._lock)
                self._inflight[k] = _InFlight(cond=cond, carregando=True)
                self._stats[ns]["coalescencia_lider"] += 1
                sou_lider = True
            else:
                cond = inflight.cond
                self._stats[ns]["coalescencia_espera"] += 1

        if not sou_lider:
            with self._lock:
                cond.wait(timeout=max(0.01, float(timeout_coalescencia_segundos)))
            v2 = self.obter(chave, None, namespace=ns)
            if v2 is not None:
                return v2
            if fallback is not None:
                with self._lock:
                    self._stats[ns]["fallback_usado"] += 1
                self._obs_evento("fallback", ns, labels={"motivo": "timeout_coalescencia"})
                return fallback

        try:
            carregado = carregador()
            self.definir(chave, carregado, ttl_segundos=ttl_segundos, namespace=ns)
            return carregado
        except Exception:
            with self._lock:
                self._stats[ns]["fallback_usado"] += 1
            self._obs_evento("fallback", ns, labels={"motivo": "erro_carregador"})
            if fallback is not None:
                return fallback
            raise
        finally:
            if sou_lider:
                with self._lock:
                    inflight2 = self._inflight.pop(k, None)
                    if inflight2 is not None:
                        inflight2.carregando = False
                        inflight2.cond.notify_all()

    def stats(self, *, namespace: str = "padrao") -> dict[str, Any]:
        ns = self._ns(namespace)
        self._sync_if_needed()
        now = time.monotonic()
        with self._lock:
            self._ensure_ns(ns)
            expiradas: list[str] = []
            for key, entry in self._store[ns].items():
                if self._expired(entry, now):
                    expiradas.append(key)
            for key in expiradas:
                self._stats[ns]["expirados"] += 1
                self._store[ns].pop(key, None)

            hits = float(self._stats[ns]["hits"])
            misses = float(self._stats[ns]["misses"])
            total_consultas = hits + misses
            hit_ratio = (hits / total_consultas) if total_consultas > 0 else 0.0

            latencias: dict[str, dict[str, float]] = {}
            for op, agg in self._lat.items():
                am = float(agg.get("amostras", 0.0))
                tot = float(agg.get("total_ms", 0.0))
                latencias[op] = {
                    "amostras": am,
                    "total_ms": tot,
                    "media_ms": (tot / am) if am > 0 else 0.0,
                }

            return {
                "namespace": ns,
                "grupo": self.grupo,
                "instancia": self.id_instancia,
                "itens": len(self._store[ns]),
                "hits": int(self._stats[ns]["hits"]),
                "misses": int(self._stats[ns]["misses"]),
                "hit_ratio": hit_ratio,
                "expirados": int(self._stats[ns]["expirados"]),
                "definicoes": int(self._stats[ns]["definicoes"]),
                "remocoes": int(self._stats[ns]["remocoes"]),
                "invalidacoes_locais": int(self._stats[ns]["invalidacoes_locais"]),
                "invalidacoes_remotas": int(self._stats[ns]["invalidacoes_remotas"]),
                "falhas_backend": int(self._stats[ns]["falhas_backend"]),
                "fallback_usado": int(self._stats[ns]["fallback_usado"]),
                "coalescencia_espera": int(self._stats[ns]["coalescencia_espera"]),
                "coalescencia_lider": int(self._stats[ns]["coalescencia_lider"]),
                "latencias": latencias,
                "seq_sincronizado": self._seq_aplicado,
            }


# Instância padrão para manter compatibilidade v1.1+
_INSTANCIA_PADRAO = CacheDistribuido(grupo="padrao", id_instancia="padrao", auto_sincronizar=True)


def cache_distribuido_criar(
    grupo: str = "padrao",
    id_instancia: str | None = None,
    auto_sincronizar: bool = True,
) -> CacheDistribuido:
    return CacheDistribuido(grupo=grupo, id_instancia=id_instancia, auto_sincronizar=auto_sincronizar)


def cache_distribuido_configurar_backplane(grupo: str = "padrao", disponivel: bool = True) -> dict[str, object]:
    bp = _backplane(grupo)
    bp.set_disponivel(disponivel)
    observability_runtime.registrar_runtime_metrica(
        "cache_distribuido",
        "backplane_configurar",
        labels={"grupo": grupo, "disponivel": str(bool(disponivel)).lower()},
    )
    return {"ok": True, "grupo": grupo, "disponivel": bool(disponivel)}


def _inst(instancia: CacheDistribuido | None) -> CacheDistribuido:
    return instancia if isinstance(instancia, CacheDistribuido) else _INSTANCIA_PADRAO


def cache_distribuido_sincronizar(instancia: CacheDistribuido | None = None) -> int:
    return _inst(instancia).sincronizar_invalidez()


def cache_distribuido_definir(
    chave: str,
    valor: object,
    ttl_segundos: float | None = None,
    namespace: str = "padrao",
    instancia: CacheDistribuido | None = None,
) -> object:
    return _inst(instancia).definir(chave, valor, ttl_segundos=ttl_segundos, namespace=namespace)


def cache_distribuido_obter(
    chave: str,
    padrao: object | None = None,
    namespace: str = "padrao",
    instancia: CacheDistribuido | None = None,
) -> object:
    return _inst(instancia).obter(chave, padrao, namespace=namespace)


def cache_distribuido_invalidar_chave(
    chave: str,
    namespace: str = "padrao",
    instancia: CacheDistribuido | None = None,
) -> bool:
    return _inst(instancia).invalidar_chave(chave, namespace=namespace)


def cache_distribuido_invalidar_padrao(
    padrao: str,
    namespace: str = "padrao",
    instancia: CacheDistribuido | None = None,
) -> int:
    return _inst(instancia).invalidar_padrao(padrao, namespace=namespace)


def cache_distribuido_obter_ou_carregar(
    chave: str,
    carregador: Callable[[], object],
    ttl_segundos: float | None = None,
    namespace: str = "padrao",
    timeout_coalescencia_segundos: float = 2.0,
    fallback: object | None = None,
    instancia: CacheDistribuido | None = None,
) -> object:
    return _inst(instancia).obter_ou_carregar(
        chave,
        carregador,
        ttl_segundos=ttl_segundos,
        namespace=namespace,
        timeout_coalescencia_segundos=timeout_coalescencia_segundos,
        fallback=fallback,
    )


def cache_distribuido_stats(namespace: str = "padrao", instancia: CacheDistribuido | None = None) -> dict[str, Any]:
    return _inst(instancia).stats(namespace=namespace)


def cache_distribuido_limpar(namespace: str | None = None, instancia: CacheDistribuido | None = None) -> int:
    return _inst(instancia).limpar(namespace=namespace)


# API legada v1.1 (compatibilidade)
def cache_definir(
    chave: str,
    valor: object,
    ttl_segundos: float | None = None,
    namespace: str = "padrao",
) -> object:
    return cache_distribuido_definir(chave, valor, ttl_segundos=ttl_segundos, namespace=namespace)


def cache_obter(
    chave: str,
    padrao: object | None = None,
    namespace: str = "padrao",
) -> object:
    return cache_distribuido_obter(chave, padrao=padrao, namespace=namespace)


def cache_existe(chave: str, namespace: str = "padrao") -> bool:
    return _INSTANCIA_PADRAO.existe(chave, namespace=namespace)


def cache_remover(chave: str, namespace: str = "padrao") -> bool:
    return _INSTANCIA_PADRAO.remover(chave, namespace=namespace)


def cache_invalidar_padrao(padrao: str, namespace: str = "padrao") -> int:
    return cache_distribuido_invalidar_padrao(padrao, namespace=namespace)


def cache_limpar(namespace: str | None = None) -> int:
    return cache_distribuido_limpar(namespace=namespace)


def cache_aquecer(
    itens: dict[str, object] | list[dict[str, object]] | list[list[object]] | list[tuple[object, ...]],
    ttl_segundos: float | None = None,
    namespace: str = "padrao",
) -> int:
    return _INSTANCIA_PADRAO.aquecer(itens, ttl_segundos=ttl_segundos, namespace=namespace)


def cache_stats(namespace: str = "padrao") -> dict[str, Any]:
    return cache_distribuido_stats(namespace=namespace)
