"""Utilitários compartilhados de segurança."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time


class SecurityError(RuntimeError):
    """Erro do runtime de segurança."""


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(data: str) -> bytes:
    pad = "=" * ((4 - (len(data) % 4)) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


def json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def agora() -> float:
    return time.time()


def agora_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(agora()))


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def novo_id(prefixo: str) -> str:
    base = f"{prefixo}:{agora()}:{os.urandom(16).hex()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]
