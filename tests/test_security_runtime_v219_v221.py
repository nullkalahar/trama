from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import pytest

from trama import security_runtime

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
except Exception:  # pragma: no cover - dependência opcional
    serialization = None  # type: ignore[assignment]
    rsa = None  # type: ignore[assignment]


def _gerar_par_chaves_rsa() -> tuple[str, str]:
    if rsa is None or serialization is None:
        raise RuntimeError("cryptography indisponível")
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = priv.public_key()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return priv_pem, pub_pem


def _b64u(data: bytes) -> str:
    from trama.security.comum import b64url_encode

    return b64url_encode(data)


def _jwk_rsa(pub_pem: str, kid: str) -> dict[str, object]:
    if serialization is None:
        raise RuntimeError("cryptography indisponível")
    pub = serialization.load_pem_public_key(pub_pem.encode("utf-8"))
    nums = pub.public_numbers()
    n_b = int(nums.n).to_bytes((int(nums.n).bit_length() + 7) // 8, "big")
    e_b = int(nums.e).to_bytes((int(nums.e).bit_length() + 7) // 8, "big")
    return {
        "kty": "RSA",
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
        "n": _b64u(n_b),
        "e": _b64u(e_b),
    }


class _EstadoServidor:
    def __init__(self, issuer: str) -> None:
        self.lock = threading.RLock()
        self.issuer = issuer
        self.jwks: dict[str, object] = {"keys": []}


class _HandlerOidc(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        estado: _EstadoServidor = self.server.estado  # type: ignore[attr-defined]
        if self.path == "/.well-known/openid-configuration":
            body = {
                "issuer": estado.issuer,
                "jwks_uri": f"{estado.issuer}/jwks.json",
            }
            self._json(body)
            return
        if self.path == "/jwks.json":
            with estado.lock:
                body = dict(estado.jwks)
            self._json(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _json(self, body: dict[str, object]) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.mark.skipif(serialization is None or rsa is None, reason="cryptography não disponível")
def test_v219_rs256_local_com_kid() -> None:
    priv_pem, pub_pem = _gerar_par_chaves_rsa()
    token = security_runtime.jwt_criar(
        {"sub": "u_v219", "iss": "trama", "aud": "api"},
        priv_pem,
        exp_segundos=60,
        algoritmo="RS256",
        kid="k-local",
    )
    header = security_runtime.jwt_ler_cabecalho(token)
    assert header["alg"] == "RS256"
    assert header["kid"] == "k-local"
    claims = security_runtime.jwt_verificar(token, pub_pem, emissor="trama", audiencia="api")
    assert claims["sub"] == "u_v219"


@pytest.mark.skipif(serialization is None or rsa is None, reason="cryptography não disponível")
def test_v220_jwks_cache_rotacao_e_validacao_iss_aud() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _HandlerOidc)
    issuer = f"http://127.0.0.1:{server.server_port}"
    estado = _EstadoServidor(issuer=issuer)
    server.estado = estado  # type: ignore[attr-defined]
    thr = threading.Thread(target=server.serve_forever, daemon=True)
    thr.start()
    try:
        priv1, pub1 = _gerar_par_chaves_rsa()
        priv2, pub2 = _gerar_par_chaves_rsa()
        with estado.lock:
            estado.jwks = {"keys": [_jwk_rsa(pub1, "k1")]}

        token1 = security_runtime.jwt_criar(
            {"sub": "u1", "iss": issuer, "aud": "trama-api"},
            priv1,
            exp_segundos=60,
            algoritmo="RS256",
            kid="k1",
        )
        claims1 = security_runtime.jwt_verificar_jwks(
            token1,
            f"{issuer}/jwks.json",
            emissor=issuer,
            audiencia="trama-api",
            cache_ttl_segundos=600.0,
        )
        assert claims1["sub"] == "u1"

        with estado.lock:
            estado.jwks = {"keys": [_jwk_rsa(pub2, "k2")]}
        token2 = security_runtime.jwt_criar(
            {"sub": "u2", "iss": issuer, "aud": "trama-api"},
            priv2,
            exp_segundos=60,
            algoritmo="RS256",
            kid="k2",
        )
        claims2 = security_runtime.jwt_verificar_jwks(
            token2,
            f"{issuer}/jwks.json",
            emissor=issuer,
            audiencia="trama-api",
            cache_ttl_segundos=600.0,
        )
        assert claims2["sub"] == "u2"
    finally:
        server.shutdown()
        server.server_close()
        thr.join(timeout=2.0)


@pytest.mark.skipif(serialization is None or rsa is None, reason="cryptography não disponível")
def test_v221_oidc_base_descoberta_configuracao_e_validacao() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _HandlerOidc)
    issuer = f"http://127.0.0.1:{server.server_port}"
    estado = _EstadoServidor(issuer=issuer)
    server.estado = estado  # type: ignore[attr-defined]
    thr = threading.Thread(target=server.serve_forever, daemon=True)
    thr.start()
    try:
        priv, pub = _gerar_par_chaves_rsa()
        with estado.lock:
            estado.jwks = {"keys": [_jwk_rsa(pub, "oidc-k1")]}

        cfg = security_runtime.oidc_descobrir_configuracao(issuer)
        assert str(cfg["issuer"]).rstrip("/") == issuer
        assert str(cfg["jwks_uri"]).endswith("/jwks.json")

        out_cfg = security_runtime.oidc_configurar_provedor(
            "provedor_teste",
            issuer,
            audiencia="trama-app",
            cache_ttl_jwks_segundos=300.0,
        )
        assert out_cfg["nome"] == "provedor_teste"

        token = security_runtime.jwt_criar(
            {"sub": "u_oidc", "email": "u@trama.dev", "name": "Usuario OIDC", "iss": issuer, "aud": "trama-app"},
            priv,
            exp_segundos=60,
            algoritmo="RS256",
            kid="oidc-k1",
        )
        valid = security_runtime.oidc_validar_token("provedor_teste", token)
        assert valid["ok"] is True
        assert valid["identidade"]["id_usuario_externo"] == "u_oidc"
        assert valid["identidade"]["email"] == "u@trama.dev"

        with pytest.raises(security_runtime.SecurityError, match="aud"):
            security_runtime.oidc_validar_token("provedor_teste", token, audiencia="outra-app")
    finally:
        security_runtime.oidc_remover_provedor("provedor_teste")
        server.shutdown()
        server.server_close()
        thr.join(timeout=2.0)
