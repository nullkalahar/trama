"""Runtime de segurança (v0.7): JWT, hash de senha e RBAC."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import os
import threading
import time
from typing import Any

from . import observability_runtime

try:
    import bcrypt  # type: ignore
except Exception:  # pragma: no cover - opcional
    bcrypt = None

try:
    from argon2 import PasswordHasher  # type: ignore
except Exception:  # pragma: no cover - opcional
    PasswordHasher = None  # type: ignore[assignment]


class SecurityError(RuntimeError):
    """Erro do runtime de segurança."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * ((4 - (len(data) % 4)) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def jwt_criar(
    payload: dict[str, Any],
    segredo: str,
    exp_segundos: int | None = None,
    algoritmo: str = "HS256",
) -> str:
    if algoritmo != "HS256":
        raise SecurityError("Apenas HS256 é suportado atualmente.")
    if not isinstance(payload, dict):
        raise SecurityError("payload JWT deve ser mapa.")
    if not segredo:
        raise SecurityError("segredo JWT não pode ser vazio.")

    now = int(time.time())
    claims = dict(payload)
    claims.setdefault("iat", now)
    if exp_segundos is not None:
        claims["exp"] = now + int(exp_segundos)

    header = {"alg": "HS256", "typ": "JWT"}
    h_enc = _b64url_encode(_json_bytes(header))
    p_enc = _b64url_encode(_json_bytes(claims))
    signing_input = f"{h_enc}.{p_enc}".encode("ascii")
    sig = hmac.new(segredo.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s_enc = _b64url_encode(sig)
    return f"{h_enc}.{p_enc}.{s_enc}"


def jwt_verificar(token: str, segredo: str, leeway_segundos: int = 0) -> dict[str, Any]:
    if not segredo:
        raise SecurityError("segredo JWT não pode ser vazio.")
    parts = token.split(".")
    if len(parts) != 3:
        raise SecurityError("token JWT inválido.")

    h_enc, p_enc, s_enc = parts
    signing_input = f"{h_enc}.{p_enc}".encode("ascii")
    sig = hmac.new(segredo.encode("utf-8"), signing_input, hashlib.sha256).digest()
    expected = _b64url_encode(sig)
    if not hmac.compare_digest(expected, s_enc):
        raise SecurityError("assinatura JWT inválida.")

    try:
        header = json.loads(_b64url_decode(h_enc).decode("utf-8"))
        payload = json.loads(_b64url_decode(p_enc).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SecurityError("token JWT malformado.") from exc

    if header.get("alg") != "HS256":
        raise SecurityError("algoritmo JWT não suportado.")

    now = int(time.time())
    leeway = int(leeway_segundos)
    exp = payload.get("exp")
    nbf = payload.get("nbf")
    if exp is not None and now > int(exp) + leeway:
        raise SecurityError("token JWT expirado.")
    if nbf is not None and now < int(nbf) - leeway:
        raise SecurityError("token JWT ainda não é válido.")

    return payload


def senha_hash(senha: str, algoritmo: str = "pbkdf2") -> str:
    if not isinstance(senha, str) or not senha:
        raise SecurityError("senha inválida.")

    alg = algoritmo.lower()
    if alg == "bcrypt":
        if bcrypt is None:
            raise SecurityError("bcrypt não está disponível neste ambiente.")
        return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    if alg in {"argon2", "argon2id"}:
        if PasswordHasher is None:
            raise SecurityError("argon2 não está disponível neste ambiente.")
        ph = PasswordHasher()
        return ph.hash(senha)

    if alg == "pbkdf2":
        salt = os.urandom(16)
        iterations = 120_000
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iterations, dklen=32)
        return f"pbkdf2${iterations}${_b64url_encode(salt)}${_b64url_encode(dk)}"

    raise SecurityError(f"algoritmo de hash não suportado: {algoritmo}")


def senha_verificar(senha: str, hash_armazenado: str) -> bool:
    if not isinstance(senha, str) or not isinstance(hash_armazenado, str):
        return False

    if hash_armazenado.startswith("pbkdf2$"):
        try:
            _, it_s, salt_s, digest_s = hash_armazenado.split("$", 3)
            iterations = int(it_s)
            salt = _b64url_decode(salt_s)
            expected = _b64url_decode(digest_s)
        except Exception:  # noqa: BLE001
            return False
        got = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(got, expected)

    if hash_armazenado.startswith("$2") and bcrypt is not None:
        try:
            return bool(bcrypt.checkpw(senha.encode("utf-8"), hash_armazenado.encode("utf-8")))
        except Exception:  # noqa: BLE001
            return False

    if hash_armazenado.startswith("$argon2") and PasswordHasher is not None:
        try:
            ph = PasswordHasher()
            return bool(ph.verify(hash_armazenado, senha))
        except Exception:  # noqa: BLE001
            return False

    return False


def rbac_criar(
    papeis_permissoes: dict[str, list[str]],
    heranca_papeis: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    return {
        "papeis_permissoes": {
            str(p): sorted(set(str(x) for x in perms))
            for p, perms in dict(papeis_permissoes).items()
        },
        "heranca_papeis": {
            str(p): sorted(set(str(x) for x in pais))
            for p, pais in dict(heranca_papeis or {}).items()
        },
    }


def rbac_atribuir(
    usuarios_papeis: dict[str, list[str]],
    usuario: str,
    papel: str,
) -> dict[str, list[str]]:
    out = {str(u): list(v) for u, v in dict(usuarios_papeis).items()}
    papeis = set(out.get(usuario, []))
    papeis.add(papel)
    out[usuario] = sorted(papeis)
    return out


def rbac_papeis_usuario(usuarios_papeis: dict[str, list[str]], usuario: str) -> list[str]:
    return list(dict(usuarios_papeis).get(usuario, []))


def _rbac_expandir_papeis(modelo: dict[str, object], papeis: list[str]) -> set[str]:
    heranca = dict(modelo.get("heranca_papeis", {}))
    visitados: set[str] = set()
    pilha = list(papeis)
    while pilha:
        atual = str(pilha.pop())
        if atual in visitados:
            continue
        visitados.add(atual)
        for pai in list(heranca.get(atual, [])):
            pilha.append(str(pai))
    return visitados


def rbac_tem_papel(usuarios_papeis: dict[str, list[str]], usuario: str, papel: str) -> bool:
    return papel in set(rbac_papeis_usuario(usuarios_papeis, usuario))


def rbac_tem_permissao(
    modelo: dict[str, object],
    usuarios_papeis: dict[str, list[str]],
    usuario: str,
    permissao: str,
) -> bool:
    papeis_base = rbac_papeis_usuario(usuarios_papeis, usuario)
    papeis = _rbac_expandir_papeis(modelo, papeis_base)
    papeis_permissoes = dict(modelo.get("papeis_permissoes", {}))
    for papel in papeis:
        if permissao in set(list(papeis_permissoes.get(papel, []))):
            return True
    return False


def _agora() -> float:
    return time.time()


def _agora_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_agora()))


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


@dataclass
class _SessaoAuth:
    id_sessao: str
    id_usuario: str
    id_dispositivo: str
    refresh_jti_atual: str
    ativa: bool = True
    criada_em: float = field(default_factory=_agora)
    atualizada_em: float = field(default_factory=_agora)
    expira_em: float | None = None
    metadados: dict[str, object] = field(default_factory=dict)


_DENYLIST_LOCK = threading.RLock()
_TOKEN_DENYLIST: dict[str, float] = {}

_SESSAO_LOCK = threading.RLock()
_SESSOES: dict[str, _SessaoAuth] = {}
_SESSAO_POR_USUARIO: dict[str, set[str]] = {}
_SESSAO_POR_DISPOSITIVO: dict[tuple[str, str], set[str]] = {}

_AUDITORIA_LOCK = threading.RLock()
_AUDITORIA_ADMIN: list[dict[str, object]] = []


def _emitir_metrica(evento: str, valor: float = 1.0, labels: dict[str, object] | None = None) -> None:
    observability_runtime.registrar_runtime_metrica("seguranca", evento, valor=float(valor), labels=dict(labels or {}))


def _limpar_denylist_expirados(now: float | None = None) -> int:
    atual = _agora() if now is None else float(now)
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
    expira_em = _agora() + ttl
    chave = _token_fingerprint(token)
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
    chave = _token_fingerprint(token)
    with _DENYLIST_LOCK:
        exp = _TOKEN_DENYLIST.get(chave)
    if exp is None:
        return False
    if float(exp) <= _agora():
        with _DENYLIST_LOCK:
            _TOKEN_DENYLIST.pop(chave, None)
        return False
    return True


def token_denylist_limpar_expirados() -> int:
    return _limpar_denylist_expirados()


def _novo_id(prefixo: str) -> str:
    base = f"{prefixo}:{_agora()}:{os.urandom(16).hex()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]


def sessao_criar(
    id_usuario: str,
    id_dispositivo: str | None = None,
    ttl_refresh_segundos: int = 30 * 24 * 3600,
    metadados: dict[str, object] | None = None,
) -> dict[str, object]:
    usuario = str(id_usuario or "").strip()
    if not usuario:
        raise SecurityError("id_usuario é obrigatório para criar sessão.")
    dispositivo = str(id_dispositivo or "dispositivo_padrao").strip() or "dispositivo_padrao"
    id_sessao = _novo_id("sessao")
    refresh_jti = _novo_id("refresh")
    ttl = max(int(ttl_refresh_segundos), 1)
    agora = _agora()
    sessao = _SessaoAuth(
        id_sessao=id_sessao,
        id_usuario=usuario,
        id_dispositivo=dispositivo,
        refresh_jti_atual=refresh_jti,
        ativa=True,
        criada_em=agora,
        atualizada_em=agora,
        expira_em=agora + ttl,
        metadados=dict(metadados or {}),
    )
    with _SESSAO_LOCK:
        _SESSOES[id_sessao] = sessao
        _SESSAO_POR_USUARIO.setdefault(usuario, set()).add(id_sessao)
        _SESSAO_POR_DISPOSITIVO.setdefault((usuario, dispositivo), set()).add(id_sessao)
    _emitir_metrica("sessao_criada")
    return {
        "ok": True,
        "id_sessao": id_sessao,
        "id_usuario": usuario,
        "id_dispositivo": dispositivo,
        "refresh_jti": refresh_jti,
        "expira_em": sessao.expira_em,
    }


def sessao_obter(id_sessao: str) -> dict[str, object] | None:
    sid = str(id_sessao or "").strip()
    if not sid:
        return None
    with _SESSAO_LOCK:
        s = _SESSOES.get(sid)
        if s is None:
            return None
        return {
            "id_sessao": s.id_sessao,
            "id_usuario": s.id_usuario,
            "id_dispositivo": s.id_dispositivo,
            "refresh_jti_atual": s.refresh_jti_atual,
            "ativa": bool(s.ativa),
            "criada_em": float(s.criada_em),
            "atualizada_em": float(s.atualizada_em),
            "expira_em": s.expira_em,
            "metadados": dict(s.metadados),
        }


def sessao_ativa(id_sessao: str) -> bool:
    sid = str(id_sessao or "").strip()
    if not sid:
        return False
    now = _agora()
    with _SESSAO_LOCK:
        s = _SESSOES.get(sid)
        if s is None or not s.ativa:
            return False
        if s.expira_em is not None and float(s.expira_em) <= now:
            s.ativa = False
            s.atualizada_em = now
            return False
        return True


def _revogar_sessao_ids(ids: set[str], motivo: str) -> int:
    now = _agora()
    total = 0
    with _SESSAO_LOCK:
        for sid in set(ids):
            s = _SESSOES.get(sid)
            if s is None:
                continue
            if s.ativa:
                total += 1
            s.ativa = False
            s.atualizada_em = now
    if total > 0:
        _emitir_metrica("sessao_revogada", total, {"motivo": str(motivo)})
    return total


def sessao_revogar(id_sessao: str, motivo: str = "manual") -> dict[str, object]:
    qtd = _revogar_sessao_ids({str(id_sessao or "")}, motivo=motivo)
    return {"ok": True, "revogadas": int(qtd), "motivo": str(motivo)}


def sessao_revogar_dispositivo(id_usuario: str, id_dispositivo: str, motivo: str = "dispositivo") -> dict[str, object]:
    chave = (str(id_usuario or ""), str(id_dispositivo or ""))
    with _SESSAO_LOCK:
        ids = set(_SESSAO_POR_DISPOSITIVO.get(chave, set()))
    qtd = _revogar_sessao_ids(ids, motivo=motivo)
    return {"ok": True, "revogadas": int(qtd), "motivo": str(motivo)}


def sessao_revogar_usuario(id_usuario: str, motivo: str = "usuario") -> dict[str, object]:
    usr = str(id_usuario or "")
    with _SESSAO_LOCK:
        ids = set(_SESSAO_POR_USUARIO.get(usr, set()))
    qtd = _revogar_sessao_ids(ids, motivo=motivo)
    return {"ok": True, "revogadas": int(qtd), "motivo": str(motivo)}


def token_acesso_emitir(
    id_usuario: str,
    segredo: str,
    exp_segundos: int = 900,
    id_sessao: str | None = None,
    id_dispositivo: str | None = None,
    permissoes: list[str] | None = None,
    claims_extras: dict[str, object] | None = None,
) -> str:
    payload: dict[str, object] = {
        "sub": str(id_usuario),
        "id_usuario": str(id_usuario),
        "tipo_token": "acesso",
        "permissoes": list(permissoes or []),
    }
    if id_sessao:
        payload["sid"] = str(id_sessao)
        payload["id_sessao"] = str(id_sessao)
    if id_dispositivo:
        payload["did"] = str(id_dispositivo)
        payload["id_dispositivo"] = str(id_dispositivo)
    payload.update(dict(claims_extras or {}))
    _emitir_metrica("token_acesso_emitido")
    return jwt_criar(payload, segredo, exp_segundos=exp_segundos)


def refresh_token_emitir(
    id_usuario: str,
    segredo: str,
    id_sessao: str,
    id_dispositivo: str | None = None,
    exp_segundos: int = 30 * 24 * 3600,
    claims_extras: dict[str, object] | None = None,
) -> str:
    sid = str(id_sessao or "").strip()
    if not sid:
        raise SecurityError("id_sessao é obrigatório para refresh token.")
    with _SESSAO_LOCK:
        sessao = _SESSOES.get(sid)
        if sessao is None:
            raise SecurityError("sessao_inexistente")
        if not sessao.ativa:
            raise SecurityError("sessao_revogada")
        jti = _novo_id("rt")
        sessao.refresh_jti_atual = jti
        sessao.atualizada_em = _agora()
    payload: dict[str, object] = {
        "sub": str(id_usuario),
        "id_usuario": str(id_usuario),
        "sid": sid,
        "id_sessao": sid,
        "did": str(id_dispositivo or sessao.id_dispositivo),
        "id_dispositivo": str(id_dispositivo or sessao.id_dispositivo),
        "jti": jti,
        "tipo_token": "refresh",
    }
    payload.update(dict(claims_extras or {}))
    _emitir_metrica("refresh_emitido")
    return jwt_criar(payload, segredo, exp_segundos=exp_segundos)


def refresh_token_trocar(
    token_refresh: str,
    segredo: str,
    exp_segundos: int = 30 * 24 * 3600,
) -> dict[str, object]:
    claims = jwt_verificar(token_refresh, segredo)
    tipo = str(claims.get("tipo_token") or "")
    if tipo != "refresh":
        raise SecurityError("token_nao_refresh")
    sid = str(claims.get("sid") or claims.get("id_sessao") or "").strip()
    jti = str(claims.get("jti") or "").strip()
    uid = str(claims.get("id_usuario") or claims.get("sub") or "").strip()
    did = str(claims.get("id_dispositivo") or claims.get("did") or "").strip() or "dispositivo_padrao"
    if not sid or not jti or not uid:
        raise SecurityError("refresh_token_malformado")
    now = _agora()
    with _SESSAO_LOCK:
        sessao = _SESSOES.get(sid)
        if sessao is None or not sessao.ativa:
            raise SecurityError("sessao_revogada")
        if sessao.expira_em is not None and float(sessao.expira_em) <= now:
            sessao.ativa = False
            sessao.atualizada_em = now
            raise SecurityError("sessao_expirada")
        if jti != sessao.refresh_jti_atual:
            sessao.ativa = False
            sessao.atualizada_em = now
            ttl_reuso = max(float(claims.get("exp", now + 60)) - now, 60.0)
            token_bloquear(token_refresh, ttl_reuso, motivo="refresh_reuso_detectado")
            _emitir_metrica("refresh_reuso_detectado")
            raise SecurityError("refresh_reuso_detectado")
        novo_jti = _novo_id("rt")
        sessao.refresh_jti_atual = novo_jti
        sessao.atualizada_em = now
    if token_esta_bloqueado(token_refresh):
        _emitir_metrica("refresh_negado", labels={"motivo": "denylist"})
        raise SecurityError("refresh_token_revogado")
    ttl_antigo = max(float(claims.get("exp", now + 60)) - now, 60.0)
    token_bloquear(token_refresh, ttl_antigo, motivo="refresh_rotacionado")
    payload_novo = {
        "sub": uid,
        "id_usuario": uid,
        "sid": sid,
        "id_sessao": sid,
        "did": did,
        "id_dispositivo": did,
        "jti": novo_jti,
        "tipo_token": "refresh",
    }
    novo_refresh = jwt_criar(payload_novo, segredo, exp_segundos=exp_segundos)
    _emitir_metrica("refresh_rotacionado")
    return {
        "ok": True,
        "id_usuario": uid,
        "id_sessao": sid,
        "id_dispositivo": did,
        "refresh_token": novo_refresh,
        "refresh_jti": novo_jti,
    }


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
        "id_evento": _novo_id("aud"),
        "ator": str(ator or "anonimo"),
        "acao": str(acao or "desconhecida"),
        "alvo": str(alvo or ""),
        "timestamp": _agora(),
        "timestamp_iso": _agora_iso(),
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


@dataclass
class _RateEvento:
    tentativas: int
    reset_em: float


class _RateBackendMemoria:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._dados: dict[str, _RateEvento] = {}

    def aplicar(self, chave: str, janela_segundos: float) -> tuple[int, float]:
        now = _agora()
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
        self.id_instancia = str(id_instancia or _novo_id("rl"))
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
        reset_em = _agora() + janela
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
                reset_em = _agora() + (float(ttl_ms) / 1000.0)
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
