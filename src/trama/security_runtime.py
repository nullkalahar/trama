"""Runtime de segurança (v0.7): JWT, hash de senha e RBAC."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

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
