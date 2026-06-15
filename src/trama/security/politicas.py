"""Módulo de políticas de segurança."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time

from .. import observability_runtime
from .comum import SecurityError, agora, agora_iso, novo_id, token_fingerprint

_DENYLIST_LOCK = threading.RLock()
_TOKEN_DENYLIST: dict[str, float] = {}

_AUDITORIA_LOCK = threading.RLock()
_AUDITORIA_ADMIN: list[dict[str, object]] = []


def _emitir_metrica(evento: str, valor: float = 1.0, labels: dict[str, object] | None = None) -> None:
    observability_runtime.registrar_runtime_metrica("seguranca", evento, valor=float(valor), labels=dict(labels or {}))


def _limpar_denylist_expirados(now: float | None = None) -> int:
    atual = agora() if now is None else float(now)
    removidos = 0
    with _DENYLIST_LOCK:
        for chave, expira_em in list(_TOKEN_DENYLIST.items()):
            if float(expira_em) <= atual:
                _TOKEN_DENYLIST.pop(chave, None)
                removidos += 1
    if removidos > 0:
        _emitir_metrica("denylist_limpeza", removidos)
    return removidos


def token_bloquear(token: str, ttl_segundos: float | None = None, motivo: str = "manual") -> dict[str, object]:
    if not isinstance(token, str) or not token.strip():
        raise SecurityError("token inválido para bloqueio.")
    _limpar_denylist_expirados()
    ttl = 24 * 3600.0 if ttl_segundos is None else max(float(ttl_segundos), 1.0)
    expira_em = agora() + ttl
    chave = token_fingerprint(token)
    with _DENYLIST_LOCK:
        _TOKEN_DENYLIST[chave] = expira_em
    _emitir_metrica("token_bloqueado", labels={"motivo": str(motivo)})
    return {
        "ok": True,
        "chave": chave,
        "motivo": str(motivo),
        "expira_em": expira_em,
        "expira_em_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expira_em)),
    }


def token_esta_bloqueado(token: str) -> bool:
    if not isinstance(token, str) or not token.strip():
        return False
    _limpar_denylist_expirados()
    chave = token_fingerprint(token)
    with _DENYLIST_LOCK:
        exp = _TOKEN_DENYLIST.get(chave)
    if exp is None:
        return False
    if float(exp) <= agora():
        with _DENYLIST_LOCK:
            _TOKEN_DENYLIST.pop(chave, None)
        return False
    return True


def token_denylist_limpar_expirados() -> int:
    return _limpar_denylist_expirados()


def auditoria_seguranca_registrar(
    ator: str,
    acao: str,
    alvo: str,
    resultado: str,
    id_requisicao: str | None = None,
    id_traco: str | None = None,
    origem: str | None = None,
    detalhes: dict[str, object] | None = None,
) -> dict[str, object]:
    evento = {
        "id_evento": novo_id("aud"),
        "ator": str(ator or "anonimo"),
        "acao": str(acao or "desconhecida"),
        "alvo": str(alvo or ""),
        "timestamp": agora(),
        "timestamp_iso": agora_iso(),
        "resultado": str(resultado or "desconhecido"),
        "id_requisicao": str(id_requisicao or ""),
        "id_traco": str(id_traco or ""),
        "origem": str(origem or ""),
        "detalhes": dict(detalhes or {}),
    }
    with _AUDITORIA_LOCK:
        _AUDITORIA_ADMIN.append(evento)
        if len(_AUDITORIA_ADMIN) > 20000:
            del _AUDITORIA_ADMIN[: len(_AUDITORIA_ADMIN) - 20000]
    _emitir_metrica("auditoria_registro", labels={"acao": evento["acao"], "resultado": evento["resultado"]})
    return {"ok": True, "evento": dict(evento)}


def auditoria_seguranca_listar(
    limite: int = 100,
    ator: str | None = None,
    acao: str | None = None,
) -> list[dict[str, object]]:
    lim = max(int(limite), 1)
    ator_f = str(ator) if ator is not None else None
    acao_f = str(acao) if acao is not None else None
    with _AUDITORIA_LOCK:
        itens = list(reversed(_AUDITORIA_ADMIN))
    out: list[dict[str, object]] = []
    for item in itens:
        if ator_f is not None and str(item.get("ator")) != ator_f:
            continue
        if acao_f is not None and str(item.get("acao")) != acao_f:
            continue
        out.append(dict(item))
        if len(out) >= lim:
            break
    return out


def _lista(valor: object) -> list[object]:
    if isinstance(valor, list):
        return list(valor)
    if valor is None:
        return []
    return [valor]


def _match_campo(regra: object, atual: object) -> bool:
    itens = _lista(regra)
    if not itens:
        return True
    atual_s = str(atual)
    for item in itens:
        item_s = str(item)
        if item_s == "*":
            return True
        if item_s == atual_s:
            return True
    return False


def autorizacao_politicas_criar(
    regras: list[dict[str, object]],
    efeito_padrao: str = "negar",
) -> dict[str, object]:
    padrao = str(efeito_padrao or "negar").strip().lower()
    if padrao not in {"permitir", "negar"}:
        raise SecurityError("efeito_padrao de políticas deve ser 'permitir' ou 'negar'.")
    regras_norm: list[dict[str, object]] = []
    for idx, item in enumerate(list(regras or [])):
        regra = dict(item or {})
        efeito = str(regra.get("efeito") or "negar").strip().lower()
        if efeito not in {"permitir", "negar"}:
            raise SecurityError(f"regra de política inválida no índice {idx}: efeito deve ser 'permitir' ou 'negar'.")
        regra["efeito"] = efeito
        if not str(regra.get("id") or "").strip():
            regra["id"] = f"regra_{idx + 1}"
        regras_norm.append(regra)
    return {
        "ok": True,
        "versao": "v2.1.22",
        "efeito_padrao": padrao,
        "regras": regras_norm,
    }


def autorizacao_politicas_avaliar(
    modelo: dict[str, object],
    ator: dict[str, object],
    acao: str,
    recurso: dict[str, object] | None = None,
    contexto: dict[str, object] | None = None,
) -> dict[str, object]:
    ator_id = str(ator.get("id") or "")
    ator_papeis = [str(x) for x in list(ator.get("papeis") or [])]
    recurso_obj = dict(recurso or {})
    contexto_obj = dict(contexto or {})
    acao_s = str(acao or "")
    if not acao_s:
        raise SecurityError("ação é obrigatória para avaliação de políticas.")

    regras = list(dict(modelo or {}).get("regras") or [])
    for item in regras:
        regra = dict(item or {})
        regra_id = str(regra.get("id") or "")
        efeito = str(regra.get("efeito") or "negar").lower()
        ator_regra = dict(regra.get("ator") or {})
        ids_regra = _lista(ator_regra.get("ids"))
        papeis_regra = _lista(ator_regra.get("papeis"))
        if ids_regra and not _match_campo(ids_regra, ator_id):
            continue
        if papeis_regra and not any(_match_campo(papeis_regra, p) for p in ator_papeis):
            continue
        if not _match_campo(regra.get("acao"), acao_s):
            continue

        recurso_regra = regra.get("recurso")
        if isinstance(recurso_regra, dict):
            recurso_rule = dict(recurso_regra)
            if "tipo" in recurso_rule and not _match_campo(recurso_rule.get("tipo"), recurso_obj.get("tipo")):
                continue
            if "id" in recurso_rule and not _match_campo(recurso_rule.get("id"), recurso_obj.get("id")):
                continue

        contexto_regra = regra.get("contexto")
        if isinstance(contexto_regra, dict):
            ok_ctx = True
            for k, esperado in dict(contexto_regra).items():
                if not _match_campo(esperado, contexto_obj.get(str(k))):
                    ok_ctx = False
                    break
            if not ok_ctx:
                continue

        permitido = efeito == "permitir"
        _emitir_metrica(
            "autorizacao_politica_aplicada",
            labels={"efeito": efeito, "regra": regra_id or "sem_id"},
        )
        return {
            "ok": True,
            "permitido": bool(permitido),
            "decisao_explicita": True,
            "regra_id": regra_id,
            "efeito_aplicado": efeito,
            "motivo": "regra_politica_aplicada",
        }

    padrao = str(dict(modelo or {}).get("efeito_padrao") or "negar").lower()
    permitido_padrao = padrao == "permitir"
    return {
        "ok": True,
        "permitido": bool(permitido_padrao),
        "decisao_explicita": False,
        "regra_id": "",
        "efeito_aplicado": padrao,
        "motivo": "efeito_padrao_politica",
    }


@dataclass
class _RateEvento:
    tentativas: int
    reset_em: float


class _RateBackendMemoria:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._dados: dict[str, _RateEvento] = {}

    def aplicar(self, chave: str, janela_segundos: float) -> tuple[int, float]:
        now = agora()
        with self._lock:
            item = self._dados.get(chave)
            if item is None or float(item.reset_em) <= now:
                item = _RateEvento(tentativas=0, reset_em=now + max(float(janela_segundos), 0.1))
                self._dados[chave] = item
            item.tentativas += 1
            return int(item.tentativas), float(item.reset_em)


class RateLimitDistribuido:
    def __init__(
        self,
        grupo: str = "padrao",
        id_instancia: str | None = None,
        backend: str = "memoria",
        redis_url: str | None = None,
        chave_prefixo: str = "trama:seguranca:rl",
    ) -> None:
        self.grupo = str(grupo or "padrao").strip() or "padrao"
        self.id_instancia = str(id_instancia or novo_id("rl"))
        self.backend = str(backend or "memoria").strip().lower()
        self.redis_url = str(redis_url or "").strip() or None
        self.chave_prefixo = str(chave_prefixo or "trama:seguranca:rl").strip(":")
        self._mem = _RateBackendMemoria()
        self._fallback = _RateBackendMemoria()
        self._redis = None
        self._degradado = False
        self._forcado_degradado = False
        if self.backend == "redis":
            if not self.redis_url:
                raise SecurityError("rate_limit_distribuido redis exige redis_url.")
            try:
                redis_mod = __import__("redis")
                self._redis = redis_mod.Redis.from_url(self.redis_url, decode_responses=True)
                self._redis.ping()
            except Exception as exc:  # noqa: BLE001
                raise SecurityError(f"falha_redis_rate_limit: {exc}") from exc

    def _chave_global(self, chave: str) -> str:
        return f"{self.chave_prefixo}:{self.grupo}:{str(chave)}"

    def permitir(self, chave: str, max_requisicoes: int, janela_segundos: float) -> dict[str, object]:
        maximo = max(int(max_requisicoes), 1)
        janela = max(float(janela_segundos), 0.1)
        inicio = time.perf_counter()
        tentativas = 0
        reset_em = agora() + janela
        degradado = bool(self._degradado or self._forcado_degradado)
        try:
            if self.backend == "redis" and self._redis is not None:
                k = self._chave_global(chave)
                pipe = self._redis.pipeline()
                pipe.incr(k)
                pipe.pttl(k)
                atual, ttl_ms = pipe.execute()
                tentativas = int(atual)
                if int(ttl_ms) < 0:
                    self._redis.pexpire(k, int(janela * 1000))
                    ttl_ms = int(janela * 1000)
                reset_em = agora() + (float(ttl_ms) / 1000.0)
            else:
                tentativas, reset_em = self._mem.aplicar(self._chave_global(chave), janela)
            self._degradado = False
            degradado = bool(self._forcado_degradado)
        except Exception:  # noqa: BLE001
            degradado = True
            self._degradado = True
            tentativas, reset_em = self._fallback.aplicar(self._chave_global(chave), janela)
            _emitir_metrica("rate_limit_backend_indisponivel", labels={"backend": self.backend})

        permitido = tentativas <= maximo
        restante = max(0, maximo - tentativas)
        _emitir_metrica(
            "rate_limit_consulta",
            labels={
                "permitido": str(bool(permitido)).lower(),
                "backend": self.backend,
                "degradado": str(bool(degradado)).lower(),
            },
        )
        observability_runtime.metrica_observar(
            "seguranca.rate_limit.latencia_ms",
            (time.perf_counter() - inicio) * 1000.0,
            {"backend": self.backend, "grupo": self.grupo, "instancia": self.id_instancia},
        )
        return {
            "ok": True,
            "permitido": bool(permitido),
            "tentativas": int(tentativas),
            "restante": int(restante),
            "maximo": int(maximo),
            "reset_em": float(reset_em),
            "degradado": bool(degradado),
        }

    def status(self) -> dict[str, object]:
        return {
            "ok": True,
            "grupo": self.grupo,
            "instancia": self.id_instancia,
            "backend": self.backend,
            "degradado": bool(self._degradado or self._forcado_degradado),
        }


_RATE_LIMIT_INSTANCIAS_LOCK = threading.RLock()
_RATE_LIMIT_INSTANCIAS: dict[str, RateLimitDistribuido] = {}


def rate_limit_distribuido_obter_instancia(
    grupo: str = "padrao",
    id_instancia: str | None = None,
    backend: str = "memoria",
    redis_url: str | None = None,
    chave_prefixo: str = "trama:seguranca:rl",
) -> RateLimitDistribuido:
    key = "|".join(
        [
            str(grupo or "padrao"),
            str(backend or "memoria"),
            str(redis_url or ""),
            str(chave_prefixo or "trama:seguranca:rl"),
        ]
    )
    with _RATE_LIMIT_INSTANCIAS_LOCK:
        inst = _RATE_LIMIT_INSTANCIAS.get(key)
        if inst is None:
            try:
                inst = RateLimitDistribuido(
                    grupo=grupo,
                    id_instancia=id_instancia,
                    backend=backend,
                    redis_url=redis_url,
                    chave_prefixo=chave_prefixo,
                )
            except SecurityError:
                inst = RateLimitDistribuido(
                    grupo=grupo,
                    id_instancia=id_instancia,
                    backend="memoria",
                    redis_url=None,
                    chave_prefixo=chave_prefixo,
                )
                inst._degradado = True
                inst._forcado_degradado = True
                _emitir_metrica("rate_limit_backend_indisponivel", labels={"backend": str(backend)})
            _RATE_LIMIT_INSTANCIAS[key] = inst
        return inst


def rate_limit_distribuido_permitir(
    chave: str,
    max_requisicoes: int,
    janela_segundos: float,
    *,
    grupo: str = "padrao",
    id_instancia: str | None = None,
    backend: str = "memoria",
    redis_url: str | None = None,
    chave_prefixo: str = "trama:seguranca:rl",
) -> dict[str, object]:
    inst = rate_limit_distribuido_obter_instancia(
        grupo=grupo,
        id_instancia=id_instancia,
        backend=backend,
        redis_url=redis_url,
        chave_prefixo=chave_prefixo,
    )
    return inst.permitir(chave=chave, max_requisicoes=max_requisicoes, janela_segundos=janela_segundos)
