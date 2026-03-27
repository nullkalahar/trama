"""Builtins padrão da linguagem trama."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import inspect
import json
import mimetypes
import os
from pathlib import Path
import threading
import time
from typing import Any
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlparse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
    if lowered in {"verdadeiro", "true"}:
        return True
    if lowered in {"falso", "false"}:
        return False
    if lowered in {"nulo", "null"}:
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


class _WebRoute:
    def __init__(self, method: str, path: str, kind: str, data: dict[str, object]) -> None:
        self.method = method.upper()
        self.path = path
        self.kind = kind
        self.data = data


class _WebApp:
    def __init__(self) -> None:
        self.routes: list[_WebRoute] = []
        self.middlewares: set[str] = set()
        self.cors_enabled = False
        self.cors_origin = "*"
        self.cors_methods = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        self.cors_headers = "Content-Type,Authorization"
        self.health_path = "/health"
        self.health_enabled = True
        self.static_prefix: str | None = None
        self.static_dir: Path | None = None


class _WebRuntime:
    def __init__(self, app: _WebApp, host: str, port: int, out: Callable[[str], None]) -> None:
        self.app = app
        self.host = host
        self.port = port
        self.out = out
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        app = self.app
        out = self.out

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
                return

            def _send_json(
                self,
                status: int,
                payload: dict[str, object],
                extra_headers: dict[str, str] | None = None,
            ) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                if app.cors_enabled:
                    self.send_header("Access-Control-Allow-Origin", app.cors_origin)
                    self.send_header("Access-Control-Allow-Methods", app.cors_methods)
                    self.send_header("Access-Control-Allow-Headers", app.cors_headers)
                if extra_headers:
                    for k, v in extra_headers.items():
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def _send_file(self, file_path: Path, request_id: str | None = None) -> None:
                data = file_path.read_bytes()
                mime, _ = mimetypes.guess_type(str(file_path))
                content_type = mime or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                if request_id:
                    self.send_header("X-Request-Id", request_id)
                if app.cors_enabled:
                    self.send_header("Access-Control-Allow-Origin", app.cors_origin)
                    self.send_header("Access-Control-Allow-Methods", app.cors_methods)
                    self.send_header("Access-Control-Allow-Headers", app.cors_headers)
                self.end_headers()
                self.wfile.write(data)

            def _read_json_body(self) -> tuple[dict[str, object] | None, tuple[int, dict[str, object]] | None]:
                raw_len = self.headers.get("Content-Length", "0")
                try:
                    length = int(raw_len)
                except ValueError:
                    return None, (
                        400,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "CONTENT_LENGTH_INVALIDO",
                                "mensagem": "Content-Length inválido.",
                                "detalhes": None,
                            },
                        },
                    )
                if length <= 0:
                    return {}, None
                if length > 2 * 1024 * 1024:
                    return None, (
                        413,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "PAYLOAD_GRANDE",
                                "mensagem": "Payload excede o limite de 2MB.",
                                "detalhes": None,
                            },
                        },
                    )
                data = self.rfile.read(length)
                text = data.decode("utf-8", errors="replace")
                if not text.strip():
                    return {}, None
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as exc:
                    return None, (
                        400,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "JSON_INVALIDO",
                                "mensagem": "Corpo JSON inválido.",
                                "detalhes": str(exc),
                            },
                        },
                    )
                if not isinstance(parsed, dict):
                    return None, (
                        422,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "PAYLOAD_INVALIDO",
                                "mensagem": "Payload deve ser um objeto JSON.",
                                "detalhes": None,
                            },
                        },
                    )
                return parsed, None

            def _handle_request(self) -> None:
                start = time.perf_counter()
                request_id = str(uuid.uuid4()) if "request_id" in app.middlewares else None

                if self.command == "OPTIONS" and app.cors_enabled:
                    self.send_response(204)
                    self.send_header("Connection", "close")
                    self.send_header("Access-Control-Allow-Origin", app.cors_origin)
                    self.send_header("Access-Control-Allow-Methods", app.cors_methods)
                    self.send_header("Access-Control-Allow-Headers", app.cors_headers)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

                parsed_url = urlparse(self.path)
                path = parsed_url.path

                if app.health_enabled and path == app.health_path:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(200, {"ok": True, "status": "up"}, headers)
                    return

                if app.static_prefix and app.static_dir and path.startswith(app.static_prefix):
                    rel = path[len(app.static_prefix) :].lstrip("/")
                    safe_target = (app.static_dir / rel).resolve()
                    base = app.static_dir.resolve()
                    if not str(safe_target).startswith(str(base)):
                        headers = {"X-Request-Id": request_id} if request_id else None
                        self._send_json(
                            403,
                            {
                                "ok": False,
                                "erro": {
                                    "codigo": "STATIC_FORBIDDEN",
                                    "mensagem": "Acesso ao arquivo negado.",
                                    "detalhes": None,
                                },
                            },
                            headers,
                        )
                        return
                    if safe_target.is_file():
                        self._send_file(safe_target, request_id=request_id)
                        return
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(
                        404,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "STATIC_NOT_FOUND",
                                "mensagem": "Arquivo estático não encontrado.",
                                "detalhes": None,
                            },
                        },
                        headers,
                    )
                    return

                route = next(
                    (r for r in app.routes if r.method == self.command and r.path == path),
                    None,
                )
                if route is None:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(
                        404,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "ROTA_NAO_ENCONTRADA",
                                "mensagem": "Rota não encontrada.",
                                "detalhes": {"metodo": self.command, "caminho": path},
                            },
                        },
                        headers,
                    )
                    return

                query = {k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(parsed_url.query).items()}
                body, body_error = self._read_json_body()
                if body_error:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(body_error[0], body_error[1], headers)
                    return

                status = int(route.data.get("status", 200))
                response_payload: dict[str, object]

                if route.kind == "json_static":
                    response_payload = {"ok": True, "dados": route.data.get("body")}
                elif route.kind == "echo_json":
                    required = list(route.data.get("required", []))
                    missing = [field for field in required if field not in (body or {})]
                    if missing:
                        headers = {"X-Request-Id": request_id} if request_id else None
                        self._send_json(
                            422,
                            {
                                "ok": False,
                                "erro": {
                                    "codigo": "VALIDACAO_FALHOU",
                                    "mensagem": "Campos obrigatórios ausentes.",
                                    "detalhes": {"faltando": missing},
                                },
                            },
                            headers,
                        )
                        return
                    response_payload = {
                        "ok": True,
                        "dados": {
                            "metodo": self.command,
                            "caminho": path,
                            "query": query,
                            "payload": body or {},
                        },
                    }
                else:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(
                        500,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "ROTA_INVALIDA",
                                "mensagem": "Tipo de rota não suportado.",
                                "detalhes": route.kind,
                            },
                        },
                        headers,
                    )
                    return

                headers = {"X-Request-Id": request_id} if request_id else None
                self._send_json(status, response_payload, headers)

                if "log_requisicao" in app.middlewares:
                    ms = (time.perf_counter() - start) * 1000.0
                    out(
                        f"[WEB] {self.command} {path} -> {status} "
                        f"({ms:.2f}ms, request_id={request_id or 'n/a'})"
                    )

            def do_GET(self) -> None:  # noqa: N802
                self._handle_request()

            def do_POST(self) -> None:  # noqa: N802
                self._handle_request()

            def do_PUT(self) -> None:  # noqa: N802
                self._handle_request()

            def do_PATCH(self) -> None:  # noqa: N802
                self._handle_request()

            def do_DELETE(self) -> None:  # noqa: N802
                self._handle_request()

            def do_OPTIONS(self) -> None:  # noqa: N802
                self._handle_request()

        self.server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.port = int(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=2.0)


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

    def web_criar_app() -> object:
        return _WebApp()

    def _as_app(app: object) -> _WebApp:
        if isinstance(app, _WebApp):
            return app
        raise TypeError("objeto de app web inválido")

    def web_adicionar_rota_json(
        app: object,
        metodo: str,
        caminho: str,
        corpo: object,
        status: int = 200,
    ) -> None:
        web_app = _as_app(app)
        web_app.routes.append(
            _WebRoute(metodo, caminho, "json_static", {"body": corpo, "status": int(status)})
        )
        return None

    def web_adicionar_rota_echo_json(
        app: object,
        metodo: str,
        caminho: str,
        campos_obrigatorios: list[str] | None = None,
    ) -> None:
        web_app = _as_app(app)
        required = list(campos_obrigatorios or [])
        web_app.routes.append(
            _WebRoute(metodo, caminho, "echo_json", {"required": required, "status": 200})
        )
        return None

    def web_usar_middleware(app: object, nome: str) -> None:
        web_app = _as_app(app)
        allowed = {"log_requisicao", "request_id"}
        if nome not in allowed:
            raise ValueError(f"Middleware não suportado: {nome}")
        web_app.middlewares.add(nome)
        return None

    def web_configurar_cors(
        app: object,
        origem: str = "*",
        metodos: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        headers: str = "Content-Type,Authorization",
    ) -> None:
        web_app = _as_app(app)
        web_app.cors_enabled = True
        web_app.cors_origin = origem
        web_app.cors_methods = metodos
        web_app.cors_headers = headers
        return None

    def web_ativar_healthcheck(app: object, caminho: str = "/health") -> None:
        web_app = _as_app(app)
        web_app.health_enabled = True
        web_app.health_path = caminho
        return None

    def web_servir_estaticos(app: object, prefixo: str, diretorio: str) -> None:
        web_app = _as_app(app)
        web_app.static_prefix = prefixo if prefixo.startswith("/") else f"/{prefixo}"
        web_app.static_dir = Path(diretorio).resolve()
        return None

    async def web_iniciar(
        app: object,
        host: str = "127.0.0.1",
        porta: int = 8080,
    ) -> dict[str, object]:
        web_app = _as_app(app)
        runtime = _WebRuntime(web_app, host, int(porta), out)
        await asyncio.to_thread(runtime.start)
        return {
            "host": host,
            "porta": runtime.port,
            "base_url": f"http://{host}:{runtime.port}",
            "runtime": runtime,
        }

    async def web_parar(handle: dict[str, object]) -> None:
        runtime = handle.get("runtime")
        if isinstance(runtime, _WebRuntime):
            await asyncio.to_thread(runtime.stop)
        return None

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
        "web_criar_app": web_criar_app,
        "web_adicionar_rota_json": web_adicionar_rota_json,
        "web_adicionar_rota_echo_json": web_adicionar_rota_echo_json,
        "web_usar_middleware": web_usar_middleware,
        "web_configurar_cors": web_configurar_cors,
        "web_ativar_healthcheck": web_ativar_healthcheck,
        "web_servir_estaticos": web_servir_estaticos,
        "web_iniciar": web_iniciar,
        "web_parar": web_parar,
    }
