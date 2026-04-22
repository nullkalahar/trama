"""Modelos compartilhados do runtime web da Trama."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import time


def _route_to_regex(path: str) -> tuple[re.Pattern[str], list[str]]:
    names: list[str] = []
    chunks = path.strip("/").split("/") if path.strip("/") else []
    parts: list[str] = ["^"]
    if not chunks:
        parts.append("/$")
        return re.compile("".join(parts)), names
    parts.append("/")
    for idx, chunk in enumerate(chunks):
        if chunk.startswith(":") and len(chunk) > 1:
            name = chunk[1:]
            names.append(name)
            parts.append(r"(?P<" + re.escape(name) + r">[^/]+)")
        else:
            parts.append(re.escape(chunk))
        if idx < len(chunks) - 1:
            parts.append("/")
    parts.append("$")
    return re.compile("".join(parts)), names


@dataclass
class WebRoute:
    method: str
    path: str
    kind: str
    data: dict[str, object]
    regex: re.Pattern[str] | None = None
    param_names: list[str] = field(default_factory=list)

    @staticmethod
    def dynamic(
        method: str,
        path: str,
        handler: object,
        schema: dict[str, object] | None = None,
        options: dict[str, object] | None = None,
    ) -> "WebRoute":
        regex, names = _route_to_regex(path)
        return WebRoute(
            method=method.upper(),
            path=path,
            kind="handler",
            data={"handler": handler, "schema": dict(schema or {}), "options": dict(options or {})},
            regex=regex,
            param_names=names,
        )


@dataclass
class RateLimitPolicy:
    method: str
    path: str
    max_requisicoes: int
    janela_segundos: float
    by_key: dict[str, list[float]] = field(default_factory=dict)

    def allow(self, key: str) -> bool:
        now = time.time()
        bucket = self.by_key.setdefault(key, [])
        min_ts = now - self.janela_segundos
        while bucket and bucket[0] < min_ts:
            bucket.pop(0)
        if len(bucket) >= self.max_requisicoes:
            return False
        bucket.append(now)
        return True


@dataclass
class RateLimitDistribuidoPolicy:
    method: str
    path: str
    max_requisicoes: int
    janela_segundos: float
    chaves: list[str] = field(default_factory=lambda: ["rota", "ip"])
    grupo: str = "padrao"
    id_instancia: str | None = None
    backend: str = "memoria"
    redis_url: str | None = None
    chave_prefixo: str = "trama:seguranca:rl"
