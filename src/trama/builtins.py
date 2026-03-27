"""Builtins padrão da linguagem trama."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import inspect
import json
import os
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request
from collections.abc import Callable


def _to_coroutine(awaitable: object):
    if inspect.iscoroutine(awaitable):
        return awaitable

    if inspect.isawaitable(awaitable):
        async def _wrapper():
            return await awaitable  # type: ignore[misc]

        return _wrapper()

    raise TypeError("valor não aguardável")


def _parse_env_value(value: str) -> object:
    lowered = value.strip().lower()
    if lowered == "verdadeiro" or lowered == "true":
        return True
    if lowered == "falso" or lowered == "false":
        return False
    if lowered == "nulo" or lowered == "null":
        return None

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _http_request(
    method: str,
    url: str,
    body: object | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> dict[str, object]:
    req_headers = dict(headers or {})
    data: bytes | None = None

    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/json; charset=utf-8")
        elif isinstance(body, str):
            data = body.encode("utf-8")
        elif isinstance(body, (bytes, bytearray)):
            data = bytes(body)
        else:
            data = str(body).encode("utf-8")

    request = urllib.request.Request(url=url, method=method.upper(), data=data, headers=req_headers)

    status: int
    resp_headers: dict[str, str]
    raw_body: bytes

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.getcode() or 0)
            resp_headers = dict(response.headers.items())
            raw_body = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        resp_headers = dict(exc.headers.items()) if exc.headers is not None else {}
        raw_body = exc.read()

    text = raw_body.decode("utf-8", errors="replace")
    body_json: object | None
    try:
        body_json = json.loads(text)
    except json.JSONDecodeError:
        body_json = None

    return {
        "status": status,
        "headers": resp_headers,
        "corpo": text,
        "json": body_json,
    }


def make_builtins(print_fn: Callable[[str], None] | None = None) -> dict[str, Callable[..., object]]:
    out = print_fn or print

    def exibir(*args: object) -> None:
        out(" ".join(str(a) for a in args))
        return None

    def log(nivel: str, mensagem: object) -> None:
        ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        out(f"[{ts}] [{str(nivel).upper()}] {mensagem}")
        return None

    def log_info(mensagem: object) -> None:
        return log("INFO", mensagem)

    def log_erro(mensagem: object) -> None:
        return log("ERRO", mensagem)

    def json_parse(payload: str) -> object:
        if not isinstance(payload, str):
            raise TypeError("json_parse espera texto")
        return json.loads(payload)

    def json_parse_seguro(payload: str) -> dict[str, object]:
        if not isinstance(payload, str):
            return {"ok": False, "erro": "json_parse_seguro espera texto", "valor": None}
        try:
            return {"ok": True, "erro": None, "valor": json.loads(payload)}
        except json.JSONDecodeError as exc:
            return {"ok": False, "erro": str(exc), "valor": None}

    def json_stringify(value: object) -> str:
        return json.dumps(value, ensure_ascii=False)

    def json_stringify_pretty(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)

    def criar_tarefa(awaitable: object) -> object:
        return asyncio.create_task(_to_coroutine(awaitable))

    def cancelar_tarefa(task: object) -> None:
        task.cancel()  # type: ignore[attr-defined]
        return None

    async def dormir(segundos: float) -> None:
        await asyncio.sleep(segundos)
        return None

    async def com_timeout(awaitable: object, segundos: float) -> object:
        return await asyncio.wait_for(_to_coroutine(awaitable), timeout=segundos)

    def ler_texto(caminho: str) -> str:
        return Path(caminho).read_text(encoding="utf-8")

    def escrever_texto(caminho: str, conteudo: str) -> None:
        Path(caminho).write_text(conteudo, encoding="utf-8")
        return None

    def arquivo_existe(caminho: str) -> bool:
        return Path(caminho).exists()

    def listar_diretorio(caminho: str) -> list[str]:
        path = Path(caminho)
        return sorted([p.name for p in path.iterdir()])

    async def ler_texto_async(caminho: str) -> str:
        path = Path(caminho)
        return await asyncio.to_thread(path.read_text, encoding="utf-8")

    async def escrever_texto_async(caminho: str, conteudo: str) -> None:
        path = Path(caminho)
        await asyncio.to_thread(path.write_text, conteudo, encoding="utf-8")
        return None

    async def http_get(url: str, headers: dict[str, str] | None = None) -> dict[str, object]:
        return await asyncio.to_thread(_http_request, "GET", url, None, headers)

    async def http_post(
        url: str,
        body: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, object]:
        return await asyncio.to_thread(_http_request, "POST", url, body, headers)

    def env_obter(nome: str, padrao: object | None = None) -> object:
        return os.getenv(nome, padrao)

    def env_todos(prefixo: str | None = None) -> dict[str, str]:
        if not prefixo:
            return dict(os.environ)
        return {k: v for k, v in os.environ.items() if k.startswith(prefixo)}

    def config_carregar(padrao: dict[str, object], prefixo: str = "TRAMA_") -> dict[str, object]:
        if not isinstance(padrao, dict):
            raise TypeError("config_carregar espera mapa no primeiro argumento")

        cfg = dict(padrao)
        for key, value in os.environ.items():
            if not key.startswith(prefixo):
                continue
            field = key[len(prefixo) :].lower()
            cfg[field] = _parse_env_value(value)
        return cfg

    def agora_iso() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    def timestamp() -> float:
        return datetime.now(timezone.utc).timestamp()

    return {
        "exibir": exibir,
        "log": log,
        "log_info": log_info,
        "log_erro": log_erro,
        "json_parse": json_parse,
        "json_parse_seguro": json_parse_seguro,
        "json_stringify": json_stringify,
        "json_stringify_pretty": json_stringify_pretty,
        "criar_tarefa": criar_tarefa,
        "cancelar_tarefa": cancelar_tarefa,
        "dormir": dormir,
        "com_timeout": com_timeout,
        "ler_texto": ler_texto,
        "escrever_texto": escrever_texto,
        "arquivo_existe": arquivo_existe,
        "listar_diretorio": listar_diretorio,
        "ler_texto_async": ler_texto_async,
        "escrever_texto_async": escrever_texto_async,
        "http_get": http_get,
        "http_post": http_post,
        "env_obter": env_obter,
        "env_todos": env_todos,
        "config_carregar": config_carregar,
        "agora_iso": agora_iso,
        "timestamp": timestamp,
    }
