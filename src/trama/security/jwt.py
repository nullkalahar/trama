"""Módulo de JWT e hash de senha."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import time
from typing import Any

from .comum import SecurityError, b64url_decode, b64url_encode, json_bytes

try:
    import bcrypt  # type: ignore
except Exception:  # pragma: no cover - opcional
    bcrypt = None

try:
    from argon2 import PasswordHasher  # type: ignore
except Exception:  # pragma: no cover - opcional
    PasswordHasher = None  # type: ignore[assignment]

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
except Exception:  # pragma: no cover - opcional
    hashes = None  # type: ignore[assignment]
    serialization = None  # type: ignore[assignment]
    padding = None  # type: ignore[assignment]
    rsa = None  # type: ignore[assignment]


def _json_obj_utf8(data: bytes) -> dict[str, Any]:
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise SecurityError("JSON do token deve ser objeto.")
    return value


def _agora_claims(
    payload: dict[str, Any],
    exp_segundos: int | None,
) -> dict[str, Any]:
    now = int(time.time())
    claims = dict(payload)
    claims.setdefault("iat", now)
    if exp_segundos is not None:
        claims["exp"] = now + int(exp_segundos)
    return claims


def _jwt_parse(token: str) -> tuple[str, str, str, dict[str, Any], dict[str, Any]]:
    parts = token.split(".")
    if len(parts) != 3:
        raise SecurityError("token JWT inválido.")
    h_enc, p_enc, s_enc = parts
    try:
        header = _json_obj_utf8(b64url_decode(h_enc))
        payload = _json_obj_utf8(b64url_decode(p_enc))
    except Exception as exc:  # noqa: BLE001
        raise SecurityError("token JWT malformado.") from exc
    return h_enc, p_enc, s_enc, header, payload


def _validar_claims_tempo(payload: dict[str, Any], leeway_segundos: int = 0) -> None:
    now = int(time.time())
    leeway = int(leeway_segundos)
    exp = payload.get("exp")
    nbf = payload.get("nbf")
    if exp is not None and now > int(exp) + leeway:
        raise SecurityError("token JWT expirado.")
    if nbf is not None and now < int(nbf) - leeway:
        raise SecurityError("token JWT ainda não é válido.")


def _validar_claims_contexto(
    payload: dict[str, Any],
    emissor: str | None = None,
    audiencia: str | list[str] | None = None,
) -> None:
    if emissor is not None and str(payload.get("iss") or "") != str(emissor):
        raise SecurityError("claim 'iss' inválida para o emissor esperado.")
    if audiencia is None:
        return
    esperado = [str(audiencia)] if isinstance(audiencia, str) else [str(x) for x in list(audiencia)]
    claim_aud = payload.get("aud")
    atual: list[str] = []
    if isinstance(claim_aud, str):
        atual = [claim_aud]
    elif isinstance(claim_aud, list):
        atual = [str(x) for x in claim_aud]
    if not atual or not any(item in atual for item in esperado):
        raise SecurityError("claim 'aud' inválida para a audiência esperada.")


def _resolver_material_chave(valor: str) -> bytes:
    bruto = str(valor or "").strip()
    if not bruto:
        raise SecurityError("chave JWT não pode ser vazia.")
    try:
        possivel_arquivo = Path(bruto)
        if possivel_arquivo.exists() and possivel_arquivo.is_file():
            return possivel_arquivo.read_bytes()
    except OSError:
        pass
    return bruto.encode("utf-8")


def _assinar_hs256(signing_input: bytes, segredo: str) -> bytes:
    if not segredo:
        raise SecurityError("segredo JWT não pode ser vazio.")
    return hmac.new(segredo.encode("utf-8"), signing_input, hashlib.sha256).digest()


def _assinar_rs256(signing_input: bytes, chave_privada: str, senha: str | None = None) -> bytes:
    if serialization is None or padding is None or hashes is None:
        raise SecurityError("suporte RS256 indisponível: instale dependência 'cryptography'.")
    material = _resolver_material_chave(chave_privada)
    senha_bytes = str(senha).encode("utf-8") if senha else None
    try:
        private_key = serialization.load_pem_private_key(material, password=senha_bytes)
    except Exception as exc:  # noqa: BLE001
        raise SecurityError("chave privada RS256 inválida.") from exc
    try:
        return private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    except Exception as exc:  # noqa: BLE001
        raise SecurityError("falha ao assinar JWT com RS256.") from exc


def _verificar_rs256_assinatura(signing_input: bytes, assinatura: bytes, chave_publica: str) -> None:
    if serialization is None or padding is None or hashes is None:
        raise SecurityError("suporte RS256 indisponível: instale dependência 'cryptography'.")
    material = _resolver_material_chave(chave_publica)
    try:
        public_key = serialization.load_pem_public_key(material)
    except Exception as exc:  # noqa: BLE001
        raise SecurityError("chave pública RS256 inválida.") from exc
    try:
        public_key.verify(assinatura, signing_input, padding.PKCS1v15(), hashes.SHA256())
    except Exception as exc:  # noqa: BLE001
        raise SecurityError("assinatura JWT inválida.") from exc


def jwt_criar(
    payload: dict[str, Any],
    segredo: str,
    exp_segundos: int | None = None,
    algoritmo: str = "HS256",
    *,
    kid: str | None = None,
    senha_chave: str | None = None,
) -> str:
    if not isinstance(payload, dict):
        raise SecurityError("payload JWT deve ser mapa.")
    alg = str(algoritmo or "HS256").upper()
    claims = _agora_claims(payload, exp_segundos)
    header: dict[str, Any] = {"alg": alg, "typ": "JWT"}
    if kid:
        header["kid"] = str(kid)
    h_enc = b64url_encode(json_bytes(header))
    p_enc = b64url_encode(json_bytes(claims))
    signing_input = f"{h_enc}.{p_enc}".encode("ascii")
    if alg == "HS256":
        sig = _assinar_hs256(signing_input, segredo)
    elif alg == "RS256":
        sig = _assinar_rs256(signing_input, segredo, senha=senha_chave)
    else:
        raise SecurityError(f"algoritmo JWT não suportado: {alg}")
    return f"{h_enc}.{p_enc}.{b64url_encode(sig)}"


def jwt_verificar(
    token: str,
    segredo: str,
    leeway_segundos: int = 0,
    *,
    emissor: str | None = None,
    audiencia: str | list[str] | None = None,
) -> dict[str, Any]:
    h_enc, p_enc, s_enc, header, payload = _jwt_parse(token)
    signing_input = f"{h_enc}.{p_enc}".encode("ascii")
    assinatura = b64url_decode(s_enc)
    alg = str(header.get("alg") or "").upper()
    if alg == "HS256":
        expected = _assinar_hs256(signing_input, segredo)
        if not hmac.compare_digest(expected, assinatura):
            raise SecurityError("assinatura JWT inválida.")
    elif alg == "RS256":
        _verificar_rs256_assinatura(signing_input, assinatura, segredo)
    else:
        raise SecurityError("algoritmo JWT não suportado.")

    _validar_claims_tempo(payload, leeway_segundos=leeway_segundos)
    _validar_claims_contexto(payload, emissor=emissor, audiencia=audiencia)
    return payload


def jwt_ler_cabecalho(token: str) -> dict[str, Any]:
    _, _, _, header, _ = _jwt_parse(token)
    return header


def jwt_validar_claims(
    payload: dict[str, Any],
    *,
    leeway_segundos: int = 0,
    emissor: str | None = None,
    audiencia: str | list[str] | None = None,
) -> dict[str, Any]:
    _validar_claims_tempo(payload, leeway_segundos=leeway_segundos)
    _validar_claims_contexto(payload, emissor=emissor, audiencia=audiencia)
    return dict(payload)


def jwt_publica_de_jwk(jwk: dict[str, Any]) -> str:
    if rsa is None or serialization is None:
        raise SecurityError("suporte RS256/JWK indisponível: instale dependência 'cryptography'.")
    if str(jwk.get("kty") or "").upper() != "RSA":
        raise SecurityError("apenas JWK RSA é suportada.")
    n_s = str(jwk.get("n") or "")
    e_s = str(jwk.get("e") or "")
    if not n_s or not e_s:
        raise SecurityError("JWK RSA inválida: campos 'n' e 'e' são obrigatórios.")
    try:
        n = int.from_bytes(b64url_decode(n_s), "big")
        e = int.from_bytes(b64url_decode(e_s), "big")
        pub = rsa.RSAPublicNumbers(e=e, n=n).public_key()
        pem = pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        raise SecurityError("falha ao converter JWK RSA para PEM.") from exc


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
        return f"pbkdf2${iterations}${b64url_encode(salt)}${b64url_encode(dk)}"

    raise SecurityError(f"algoritmo de hash não suportado: {algoritmo}")


def senha_verificar(senha: str, hash_armazenado: str) -> bool:
    if not isinstance(senha, str) or not isinstance(hash_armazenado, str):
        return False

    if hash_armazenado.startswith("pbkdf2$"):
        try:
            _, it_s, salt_s, digest_s = hash_armazenado.split("$", 3)
            iterations = int(it_s)
            salt = b64url_decode(salt_s)
            expected = b64url_decode(digest_s)
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
