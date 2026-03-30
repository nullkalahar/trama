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

from . import db_runtime
from . import cache_runtime
from . import config_runtime
from . import jobs_runtime
from . import media_runtime
from . import observability_runtime
from . import resiliencia_runtime
from . import security_runtime
from . import storage_runtime
from . import web_runtime
from .bytecode import program_to_dict
from .compiler import compile_source


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


def make_builtins(
    print_fn: Callable[[str], None] | None = None,
    invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
) -> dict[str, Callable[..., object]]:
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

    def tamanho(valor: object) -> int:
        if isinstance(valor, (str, bytes, bytearray, list, tuple, dict, set)):
            return len(valor)
        raise TypeError("tamanho espera texto, lista, mapa, tupla, bytes ou conjunto")

    def lista_adicionar(lista: object, valor: object) -> int:
        if not isinstance(lista, list):
            raise TypeError("lista_adicionar espera lista no primeiro argumento")
        lista.append(valor)
        return len(lista)

    def mapa_obter(mapa: object, chave: object, padrao: object | None = None) -> object:
        if not isinstance(mapa, dict):
            raise TypeError("mapa_obter espera mapa no primeiro argumento")
        return mapa.get(chave, padrao)

    def mapa_definir(mapa: object, chave: object, valor: object) -> object:
        if not isinstance(mapa, dict):
            raise TypeError("mapa_definir espera mapa no primeiro argumento")
        mapa[chave] = valor
        return valor

    def mapa_chaves(mapa: object) -> list[object]:
        if not isinstance(mapa, dict):
            raise TypeError("mapa_chaves espera mapa no primeiro argumento")
        return list(mapa.keys())

    def trama_compilar_fonte(codigo: str) -> dict[str, object]:
        if not isinstance(codigo, str):
            raise TypeError("trama_compilar_fonte espera texto")
        program = compile_source(codigo)
        return program_to_dict(program)

    def trama_compilar_arquivo(caminho_fonte: str) -> dict[str, object]:
        if not isinstance(caminho_fonte, str):
            raise TypeError("trama_compilar_arquivo espera caminho texto")
        codigo = Path(caminho_fonte).read_text(encoding="utf-8")
        program = compile_source(codigo)
        return program_to_dict(program)

    def trama_compilar_para_arquivo(caminho_fonte: str, caminho_saida: str) -> dict[str, object]:
        payload = trama_compilar_arquivo(caminho_fonte)
        Path(caminho_saida).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"ok": True, "fonte": caminho_fonte, "saida": caminho_saida}

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
        return config_runtime.config_carregar_ambiente(padrao, prefixo=prefixo)

    def config_carregar_ambiente(
        padrao: dict[str, object],
        prefixo: str = "TRAMA_",
        obrigatorios: list[str] | None = None,
        schema: dict[str, str] | None = None,
    ) -> dict[str, object]:
        return config_runtime.config_carregar_ambiente(
            padrao,
            prefixo=prefixo,
            obrigatorios=obrigatorios,
            schema=schema,
        )

    def config_validar(
        config: dict[str, object],
        obrigatorios: list[str] | None = None,
        schema: dict[str, str] | None = None,
    ) -> dict[str, object]:
        return config_runtime.config_validar(config, obrigatorios=obrigatorios, schema=schema)

    def segredo_obter(
        nome: str,
        padrao: object | None = None,
        obrigatorio: bool = False,
        permitir_vazio: bool = False,
    ) -> object:
        return config_runtime.segredo_obter(
            nome,
            padrao=padrao,
            obrigatorio=obrigatorio,
            permitir_vazio=permitir_vazio,
        )

    def segredo_mascarar(valor: object, visivel: int = 2) -> str:
        return config_runtime.segredo_mascarar(valor, visivel=visivel)

    def cache_definir(
        chave: str,
        valor: object,
        ttl_segundos: float | None = None,
        namespace: str = "padrao",
    ) -> object:
        return cache_runtime.cache_definir(chave, valor, ttl_segundos=ttl_segundos, namespace=namespace)

    def cache_obter(chave: str, padrao: object | None = None, namespace: str = "padrao") -> object:
        return cache_runtime.cache_obter(chave, padrao=padrao, namespace=namespace)

    def cache_existe(chave: str, namespace: str = "padrao") -> bool:
        return cache_runtime.cache_existe(chave, namespace=namespace)

    def cache_remover(chave: str, namespace: str = "padrao") -> bool:
        return cache_runtime.cache_remover(chave, namespace=namespace)

    def cache_invalidar_padrao(padrao: str, namespace: str = "padrao") -> int:
        return cache_runtime.cache_invalidar_padrao(padrao, namespace=namespace)

    def cache_limpar(namespace: str | None = None) -> int:
        return cache_runtime.cache_limpar(namespace=namespace)

    def cache_aquecer(
        itens: dict[str, object] | list[dict[str, object]] | list[list[object]] | list[tuple[object, ...]],
        ttl_segundos: float | None = None,
        namespace: str = "padrao",
    ) -> int:
        return cache_runtime.cache_aquecer(itens, ttl_segundos=ttl_segundos, namespace=namespace)

    def cache_stats(namespace: str = "padrao") -> dict[str, object]:
        return cache_runtime.cache_stats(namespace=namespace)

    async def resiliencia_executar(
        nome: str,
        operacao_fn: object,
        argumentos: list[object] | None = None,
        opcoes: dict[str, object] | None = None,
    ) -> object:
        args = list(argumentos or [])
        opts = dict(opcoes or {})
        tentativas = int(opts.get("tentativas", 3))
        timeout_segundos = opts.get("timeout_segundos")
        max_falhas = int(opts.get("max_falhas", 5))
        reset_timeout_segundos = float(opts.get("reset_timeout_segundos", 30.0))
        base_backoff_segundos = float(opts.get("base_backoff_segundos", 0.1))
        max_backoff_segundos = float(opts.get("max_backoff_segundos", 2.0))
        jitter_segundos = float(opts.get("jitter_segundos", 0.05))

        nao_retentaveis_map: dict[str, type[BaseException]] = {
            "ValueError": ValueError,
            "TypeError": TypeError,
            "RuntimeError": RuntimeError,
            "KeyError": KeyError,
            "AssertionError": AssertionError,
        }
        nomes_nao_retentaveis = opts.get("nao_retentaveis", [])
        nao_retentaveis: tuple[type[BaseException], ...] = tuple(
            nao_retentaveis_map.get(str(nome), RuntimeError)
            for nome in (nomes_nao_retentaveis if isinstance(nomes_nao_retentaveis, list) else [])
        )

        async def _operacao() -> object:
            if invoke_callable_sync is not None:
                result = await asyncio.to_thread(invoke_callable_sync, operacao_fn, args)
            else:
                if not callable(operacao_fn):
                    raise TypeError("resiliencia_executar exige função chamável em 'operacao_fn'.")
                result = operacao_fn(*args)
            if inspect.isawaitable(result):
                return await result
            return result

        timeout_f = None if timeout_segundos is None else float(timeout_segundos)
        return await resiliencia_runtime.executar(
            str(nome),
            _operacao,
            tentativas=tentativas,
            timeout_segundos=timeout_f,
            max_falhas=max_falhas,
            reset_timeout_segundos=reset_timeout_segundos,
            base_backoff_segundos=base_backoff_segundos,
            max_backoff_segundos=max_backoff_segundos,
            jitter_segundos=jitter_segundos,
            excecoes_nao_retentaveis=nao_retentaveis,
        )

    def circuito_status(nome: str) -> dict[str, object]:
        return resiliencia_runtime.circuito_status(nome)

    def circuito_resetar(nome: str | None = None) -> None:
        resiliencia_runtime.circuito_reset(nome=nome)
        return None

    def armazenamento_criar_local(base_dir: str) -> object:
        return storage_runtime.LocalStorage(Path(base_dir))

    def armazenamento_criar_s3(
        bucket: str,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
        prefixo: str = "",
    ) -> object:
        return storage_runtime.S3CompatStorage(
            bucket=bucket,
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            prefixo=prefixo,
        )

    def _as_storage(storage: object) -> object:
        if isinstance(storage, (storage_runtime.LocalStorage, storage_runtime.S3CompatStorage)):
            return storage
        raise TypeError("storage inválido")

    def armazenamento_salvar(
        storage: object,
        chave: str,
        conteudo: object,
        content_type: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        st = _as_storage(storage)
        return st.put(chave, conteudo, content_type=content_type, metadata=metadata)

    def armazenamento_ler(storage: object, chave: str) -> dict[str, object]:
        st = _as_storage(storage)
        return st.get(chave)

    def armazenamento_remover(storage: object, chave: str) -> bool:
        st = _as_storage(storage)
        return bool(st.delete(chave))

    def armazenamento_listar(storage: object, prefixo: str = "") -> list[str]:
        st = _as_storage(storage)
        return list(st.list(prefix=prefixo))

    def armazenamento_url(storage: object, chave: str, expira_em: int = 3600) -> str:
        st = _as_storage(storage)
        if isinstance(st, storage_runtime.S3CompatStorage):
            return st.url(chave, expires_in=expira_em)
        return st.url(chave)

    def midia_ler_arquivo(caminho: str) -> bytes:
        return media_runtime.midia_ler_arquivo(caminho)

    def midia_salvar_arquivo(caminho: str, conteudo: object) -> dict[str, object]:
        return media_runtime.midia_salvar_arquivo(caminho, conteudo)

    def midia_comprimir_gzip(conteudo: object, nivel: int = 6) -> bytes:
        return media_runtime.midia_comprimir_gzip(conteudo, nivel=nivel)

    def midia_descomprimir_gzip(conteudo: object) -> bytes:
        return media_runtime.midia_descomprimir_gzip(conteudo)

    def midia_sha256(conteudo: object) -> str:
        return media_runtime.midia_sha256(conteudo)

    def midia_redimensionar_imagem(
        conteudo: object,
        largura: int,
        altura: int,
        manter_aspecto: bool = True,
        formato_saida: str | None = None,
        qualidade: int = 85,
    ) -> dict[str, object]:
        return media_runtime.midia_redimensionar_imagem(
            conteudo,
            largura,
            altura,
            manter_aspecto=manter_aspecto,
            formato_saida=formato_saida,
            qualidade=qualidade,
        )

    def midia_converter_imagem(conteudo: object, formato_saida: str, qualidade: int = 85) -> dict[str, object]:
        return media_runtime.midia_converter_imagem(conteudo, formato_saida, qualidade=qualidade)

    def midia_pipeline(conteudo: object, opcoes: dict[str, object] | None = None) -> dict[str, object]:
        return media_runtime.midia_pipeline(conteudo, opcoes=opcoes)

    def agora_iso() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    def timestamp() -> float:
        return datetime.now(timezone.utc).timestamp()

    def web_criar_app() -> object:
        return web_runtime.WebApp()

    def _as_app(app: object) -> web_runtime.WebApp:
        if isinstance(app, web_runtime.WebApp):
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
            web_runtime.WebRoute(metodo.upper(), caminho, "json_static", {"body": corpo, "status": int(status)})
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
            web_runtime.WebRoute(metodo.upper(), caminho, "echo_json", {"required": required, "status": 200})
        )
        return None

    def web_usar_middleware(app: object, nome: str) -> None:
        web_app = _as_app(app)
        aliases = {"id_requisicao": "request_id", "id_traco": "request_id"}
        nome_norm = aliases.get(nome, nome)
        allowed = {"log_requisicao", "request_id"}
        if nome_norm not in allowed:
            raise ValueError(f"Middleware não suportado: {nome}")
        web_app.middlewares.add(nome_norm)
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

    def web_ativar_healthcheck(app: object, caminho: str = "/saude") -> None:
        web_app = _as_app(app)
        web_app.health_enabled = True
        web_app.health_path = caminho
        return None

    def web_servir_estaticos(app: object, prefixo: str, diretorio: str) -> None:
        web_app = _as_app(app)
        web_app.static_prefix = prefixo if prefixo.startswith("/") else f"/{prefixo}"
        web_app.static_dir = Path(diretorio).resolve()
        return None

    def web_rota(
        app: object,
        metodo: str,
        caminho: str,
        handler_fn: object,
        schema: dict[str, object] | None = None,
        opcoes: dict[str, object] | None = None,
    ) -> None:
        web_app = _as_app(app)
        web_app.routes.append(
            web_runtime.WebRoute.dynamic(
                method=metodo,
                path=caminho,
                handler=handler_fn,
                schema=schema or {},
                options=opcoes or {},
            )
        )
        return None

    def web_rota_contrato(
        app: object,
        metodo: str,
        caminho: str,
        handler_fn: object,
        versao_api: str,
        contrato_resposta: dict[str, object],
        schema: dict[str, object] | None = None,
        opcoes: dict[str, object] | None = None,
    ) -> None:
        opts = dict(opcoes or {})
        opts["contrato_resposta"] = dict(contrato_resposta or {})
        web_rota(app, metodo, caminho, handler_fn, schema or {}, opts)
        _ = web_api_versionar(app, versao_api)
        return None

    def web_middleware(app: object, middleware_fn: object, fase: str = "pre") -> None:
        web_app = _as_app(app)
        if fase == "pos":
            web_app.middlewares_pos.append(middleware_fn)
            return None
        web_app.middlewares_pre.append(middleware_fn)
        return None

    def web_tratador_erro(app: object, handler_fn: object) -> None:
        web_app = _as_app(app)
        web_app.error_handler = handler_fn
        return None

    def web_rate_limit(
        app: object,
        max_requisicoes: int,
        janela_segundos: float,
        caminho: str = "*",
        metodo: str = "*",
    ) -> None:
        web_app = _as_app(app)
        web_app.rate_limits.append(
            web_runtime.RateLimitPolicy(
                method=metodo.upper(),
                path=caminho,
                max_requisicoes=int(max_requisicoes),
                janela_segundos=float(janela_segundos),
            )
        )
        return None

    def web_api_versionar(app: object, versao: str, base: str = "/api") -> str:
        web_app = _as_app(app)
        prefixo = f"{base.rstrip('/')}/{versao.strip('/')}"
        web_app.api_versions.add(prefixo)
        return prefixo

    def web_saude_paths(
        app: object,
        saude: str = "/saude",
        pronto: str = "/pronto",
        vivo: str = "/vivo",
    ) -> None:
        web_app = _as_app(app)
        web_app.health_path = saude
        web_app.readiness_path = pronto
        web_app.liveness_path = vivo
        return None

    def web_ativar_observabilidade(
        app: object,
        caminho_observabilidade: str = "/observabilidade",
        caminho_alertas: str = "/alertas",
        config_alertas: dict[str, object] | None = None,
    ) -> None:
        web_app = _as_app(app)
        web_app.observabilidade_ativa = True
        web_app.observabilidade_path = caminho_observabilidade
        web_app.alertas_path = caminho_alertas
        web_app.alertas_config = dict(config_alertas or {})
        return None

    def web_tempo_real_rota(
        app: object,
        caminho: str,
        handler_fn: object,
        opcoes: dict[str, object] | None = None,
    ) -> None:
        web_app = _as_app(app)
        web_app.tempo_real.registrar_rota(caminho, handler_fn, opcoes or {})
        return None

    def web_tempo_real_ativar_fallback(
        app: object,
        prefixo: str = "/tempo-real/fallback",
        timeout_segundos: float = 20.0,
    ) -> None:
        web_app = _as_app(app)
        web_app.tempo_real.ativar_fallback(prefixo=prefixo, timeout_segundos=float(timeout_segundos))
        return None

    def web_tempo_real_definir_limites(app: object, limites: dict[str, object]) -> None:
        web_app = _as_app(app)
        web_app.tempo_real.definir_limites(limites)
        return None

    def web_tempo_real_emitir_sala(
        app: object,
        canal: str,
        sala: str,
        evento: str,
        dados: object | None = None,
    ) -> int:
        web_app = _as_app(app)
        return web_app.tempo_real.emitir(canal, evento, dados if dados is not None else {}, sala=sala)

    def web_tempo_real_emitir_usuario(
        app: object,
        canal: str,
        id_usuario: str,
        evento: str,
        dados: object | None = None,
    ) -> int:
        web_app = _as_app(app)
        return web_app.tempo_real.emitir(canal, evento, dados if dados is not None else {}, id_usuario=id_usuario)

    def web_tempo_real_emitir_conexao(
        app: object,
        canal: str,
        id_conexao: str,
        evento: str,
        dados: object | None = None,
    ) -> int:
        web_app = _as_app(app)
        return web_app.tempo_real.emitir(canal, evento, dados if dados is not None else {}, id_conexao=id_conexao)

    def web_tempo_real_status(app: object, canal: str | None = None) -> dict[str, object]:
        web_app = _as_app(app)
        return web_app.tempo_real.snapshot(canal)

    async def web_iniciar(
        app: object,
        host: str = "127.0.0.1",
        porta: int = 8080,
    ) -> dict[str, object]:
        web_app = _as_app(app)
        runtime = web_runtime.WebRuntime(
            web_app,
            host,
            int(porta),
            out,
            invoke_callable_sync=invoke_callable_sync,
        )
        await asyncio.to_thread(runtime.start)
        return {
            "host": host,
            "porta": runtime.port,
            "base_url": f"http://{host}:{runtime.port}",
            "runtime": runtime,
        }

    async def web_parar(handle: dict[str, object]) -> None:
        runtime = handle.get("runtime")
        if isinstance(runtime, web_runtime.WebRuntime):
            await asyncio.to_thread(runtime.stop)
        return None

    def fila_criar(nome: str) -> object:
        return jobs_runtime.JobQueue(nome, invoke_callable_sync=invoke_callable_sync)

    def _as_fila(queue: object) -> jobs_runtime.JobQueue:
        if not isinstance(queue, jobs_runtime.JobQueue):
            raise TypeError("fila inválida")
        return queue

    async def fila_enfileirar(
        queue: object,
        handler_fn: object,
        payload: object,
        tentativas: int = 3,
        timeout_segundos: float = 30.0,
        chave_idempotencia: str | None = None,
    ) -> dict[str, object]:
        q = _as_fila(queue)
        return await q.enqueue(
            handler=handler_fn,
            payload=payload,
            retries=int(tentativas),
            timeout_seconds=float(timeout_segundos),
            idempotency_key=chave_idempotencia,
        )

    async def fila_processar(queue: object) -> dict[str, object]:
        q = _as_fila(queue)
        return await q.process_all()

    def fila_status(queue: object) -> dict[str, object]:
        q = _as_fila(queue)
        return q.status()

    async def webhook_enviar(
        url: str,
        payload: dict[str, object],
        segredo: str | None = None,
        tentativas: int = 3,
        timeout_segundos: float = 10.0,
    ) -> dict[str, object]:
        return await jobs_runtime.send_webhook(
            url=url,
            payload=payload,
            secret=segredo,
            retries=int(tentativas),
            timeout_seconds=float(timeout_segundos),
        )

    async def pg_conectar(dsn: str) -> object:
        return await db_runtime.conectar(dsn)

    async def pg_fechar(conn: object) -> None:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        await db_runtime.fechar(conn)
        return None

    async def pg_executar(
        conn: object,
        sql: str,
        params: list[object] | None = None,
    ) -> dict[str, object]:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.executar(conn, sql, params or [])

    async def pg_consultar(
        conn: object,
        sql: str,
        params: list[object] | None = None,
    ) -> list[dict[str, object]]:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.consultar(conn, sql, params or [])

    async def pg_transacao_iniciar(conn: object) -> object:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.transacao_iniciar(conn)

    async def pg_transacao_commit(tx: object) -> None:
        if not isinstance(tx, db_runtime.DbTransaction):
            raise TypeError("transação inválida")
        await db_runtime.transacao_commit(tx)
        return None

    async def pg_transacao_rollback(tx: object) -> None:
        if not isinstance(tx, db_runtime.DbTransaction):
            raise TypeError("transação inválida")
        await db_runtime.transacao_rollback(tx)
        return None

    async def pg_tx_executar(tx: object, sql: str, params: list[object] | None = None) -> dict[str, object]:
        if not isinstance(tx, db_runtime.DbTransaction):
            raise TypeError("transação inválida")
        return await db_runtime.tx_executar(tx, sql, params or [])

    async def pg_tx_consultar(
        tx: object,
        sql: str,
        params: list[object] | None = None,
    ) -> list[dict[str, object]]:
        if not isinstance(tx, db_runtime.DbTransaction):
            raise TypeError("transação inválida")
        return await db_runtime.tx_consultar(tx, sql, params or [])

    def qb_select(tabela: str, colunas: list[str] | None = None) -> dict[str, object]:
        return db_runtime.qb_select(tabela, colunas)

    def qb_where_eq(query: dict[str, object], campo: str, valor: object) -> dict[str, object]:
        return db_runtime.qb_where_eq(query, campo, valor)

    def qb_order_by(query: dict[str, object], campo: str, direcao: str = "ASC") -> dict[str, object]:
        return db_runtime.qb_order_by(query, campo, direcao)

    def qb_limite(query: dict[str, object], limite: int) -> dict[str, object]:
        return db_runtime.qb_limite(query, limite)

    def qb_sql(query: dict[str, object]) -> dict[str, object]:
        return db_runtime.qb_sql(query)

    async def qb_consultar(conn: object, query: dict[str, object]) -> list[dict[str, object]]:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.qb_consultar(conn, query)

    async def orm_inserir(conn: object, tabela: str, dados: dict[str, object]) -> int:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.orm_inserir(conn, tabela, dados)

    async def orm_atualizar(
        conn: object,
        tabela: str,
        dados: dict[str, object],
        where: dict[str, object],
    ) -> int:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.orm_atualizar(conn, tabela, dados, where)

    async def orm_buscar_por_id(conn: object, tabela: str, id_value: object) -> object:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.orm_buscar_por_id(conn, tabela, id_value)

    async def migracao_aplicar(conn: object, nome: str, sql: str) -> dict[str, object]:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.migracao_aplicar(conn, nome, sql)

    async def seed_aplicar(conn: object, nome: str, sql: str) -> dict[str, object]:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.seed_aplicar(conn, nome, sql)

    async def migracao_aplicar_versionada(
        conn: object,
        versao: str,
        nome: str,
        up_sql: str,
        down_sql: str = "",
        dry_run: bool = False,
        lock_owner: str = "trama",
    ) -> dict[str, object]:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.migracao_aplicar_versionada(
            conn,
            versao,
            nome,
            up_sql,
            down_sql,
            dry_run=dry_run,
            lock_owner=lock_owner,
        )

    async def migracao_status(conn: object) -> list[dict[str, object]]:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.migracao_status(conn)

    async def migracao_reverter_ultima(conn: object) -> dict[str, object]:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.migracao_reverter_ultima(conn)

    async def migracao_validar_compatibilidade(
        conn: object,
        versao: str,
        up_sql: str,
    ) -> dict[str, object]:
        if not isinstance(conn, db_runtime.DbConnection):
            raise TypeError("conexão inválida")
        return await db_runtime.migracao_validar_compatibilidade(conn, versao, up_sql)

    def jwt_criar(
        payload: dict[str, object],
        segredo: str,
        exp_segundos: int | None = None,
        algoritmo: str = "HS256",
    ) -> str:
        return security_runtime.jwt_criar(payload, segredo, exp_segundos, algoritmo)

    def jwt_verificar(token: str, segredo: str, leeway_segundos: int = 0) -> dict[str, object]:
        return security_runtime.jwt_verificar(token, segredo, leeway_segundos)

    def senha_hash(senha: str, algoritmo: str = "pbkdf2") -> str:
        return security_runtime.senha_hash(senha, algoritmo)

    def senha_verificar(senha: str, hash_armazenado: str) -> bool:
        return security_runtime.senha_verificar(senha, hash_armazenado)

    def rbac_criar(
        papeis_permissoes: dict[str, list[str]],
        heranca_papeis: dict[str, list[str]] | None = None,
    ) -> dict[str, object]:
        return security_runtime.rbac_criar(papeis_permissoes, heranca_papeis)

    def rbac_atribuir(
        usuarios_papeis: dict[str, list[str]],
        usuario: str,
        papel: str,
    ) -> dict[str, list[str]]:
        return security_runtime.rbac_atribuir(usuarios_papeis, usuario, papel)

    def rbac_papeis_usuario(usuarios_papeis: dict[str, list[str]], usuario: str) -> list[str]:
        return security_runtime.rbac_papeis_usuario(usuarios_papeis, usuario)

    def rbac_tem_papel(usuarios_papeis: dict[str, list[str]], usuario: str, papel: str) -> bool:
        return security_runtime.rbac_tem_papel(usuarios_papeis, usuario, papel)

    def rbac_tem_permissao(
        modelo: dict[str, object],
        usuarios_papeis: dict[str, list[str]],
        usuario: str,
        permissao: str,
    ) -> bool:
        return security_runtime.rbac_tem_permissao(modelo, usuarios_papeis, usuario, permissao)

    def log_estruturado(
        nivel: str,
        mensagem: object,
        contexto: dict[str, object] | None = None,
    ) -> dict[str, object]:
        entry = observability_runtime.log_estruturado(nivel, mensagem, contexto)
        out(json.dumps(entry, ensure_ascii=False, sort_keys=True))
        return entry

    def log_estruturado_json(
        nivel: str,
        mensagem: object,
        contexto: dict[str, object] | None = None,
    ) -> str:
        return observability_runtime.log_estruturado_json(nivel, mensagem, contexto)

    def metrica_incrementar(nome: str, valor: float = 1.0, labels: dict[str, object] | None = None) -> None:
        observability_runtime.metrica_incrementar(nome, valor, labels)
        return None

    def metrica_observar(nome: str, valor: float, labels: dict[str, object] | None = None) -> None:
        observability_runtime.metrica_observar(nome, valor, labels)
        return None

    def metricas_snapshot() -> dict[str, object]:
        return observability_runtime.metricas_snapshot()

    def metricas_reset() -> None:
        observability_runtime.metricas_reset()
        return None

    def traco_iniciar(nome: str, atributos: dict[str, object] | None = None) -> dict[str, object]:
        return observability_runtime.traco_iniciar(nome, atributos)

    def traco_evento(
        span: dict[str, object],
        nome: str,
        atributos: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return observability_runtime.traco_evento(span, nome, atributos)

    def traco_finalizar(
        span: dict[str, object],
        status: str = "ok",
        erro: object | None = None,
    ) -> dict[str, object]:
        return observability_runtime.traco_finalizar(span, status, erro)

    def tracos_snapshot() -> dict[str, object]:
        return observability_runtime.tracos_snapshot()

    def tracos_reset() -> None:
        observability_runtime.tracos_reset()
        return None

    def observabilidade_resumo(config_alerta: dict[str, object] | None = None) -> dict[str, object]:
        return observability_runtime.observabilidade_resumo(config_alerta=config_alerta)

    def alertas_avaliar(config_alerta: dict[str, object] | None = None) -> dict[str, object]:
        return observability_runtime.alertas_avaliar(config=config_alerta)

    # Aliases oficiais em pt-BR (mantém compatibilidade com nomes anteriores)
    banco_conectar = pg_conectar
    banco_fechar = pg_fechar
    banco_executar = pg_executar
    banco_consultar = pg_consultar
    transacao_iniciar = pg_transacao_iniciar
    transacao_confirmar = pg_transacao_commit
    transacao_cancelar = pg_transacao_rollback
    transacao_executar = pg_tx_executar
    transacao_consultar = pg_tx_consultar
    consulta_selecionar = qb_select
    consulta_onde_igual = qb_where_eq
    consulta_ordenar_por = qb_order_by
    consulta_limite = qb_limite
    consulta_sql = qb_sql
    consulta_executar = qb_consultar
    modelo_inserir = orm_inserir
    modelo_atualizar = orm_atualizar
    modelo_buscar_por_id = orm_buscar_por_id
    semente_aplicar = seed_aplicar
    migracao_versionada_aplicar = migracao_aplicar_versionada
    migracao_listar = migracao_status
    migracao_desfazer_ultima = migracao_reverter_ultima
    migracao_compatibilidade_validar = migracao_validar_compatibilidade
    token_criar = jwt_criar
    token_verificar = jwt_verificar
    senha_gerar_hash = senha_hash
    senha_validar = senha_verificar
    papel_criar_modelo = rbac_criar
    papel_atribuir = rbac_atribuir
    papel_listar_usuario = rbac_papeis_usuario
    papel_tem = rbac_tem_papel
    permissao_tem = rbac_tem_permissao
    metrica_inc = metrica_incrementar
    traca_iniciar = traco_iniciar
    traca_evento = traco_evento
    traca_finalizar = traco_finalizar
    tracas_snapshot = tracos_snapshot
    tracas_reset = tracos_reset
    requisicao = "requisicao"
    resposta = "resposta"
    http_obter = http_get
    http_postar = http_post
    web_limite_taxa = web_rate_limit
    web_api_versao = web_api_versionar
    web_rota_com_contrato = web_rota_contrato
    web_observabilidade_ativar = web_ativar_observabilidade
    web_socket_rota = web_tempo_real_rota
    web_websocket_rota = web_tempo_real_rota
    web_realtime_rota = web_tempo_real_rota
    web_realtime_ativar_fallback = web_tempo_real_ativar_fallback
    web_realtime_definir_limites = web_tempo_real_definir_limites
    web_realtime_emitir_sala = web_tempo_real_emitir_sala
    web_realtime_emitir_usuario = web_tempo_real_emitir_usuario
    web_realtime_emitir_conexao = web_tempo_real_emitir_conexao
    web_realtime_status = web_tempo_real_status
    segredo_ler = segredo_obter
    cache_invalida_padrao = cache_invalidar_padrao
    armazenamento_local_criar = armazenamento_criar_local
    armazenamento_s3_criar = armazenamento_criar_s3
    midia_gzip_comprimir = midia_comprimir_gzip
    midia_gzip_descomprimir = midia_descomprimir_gzip
    compilar_trama_fonte = trama_compilar_fonte
    compilar_trama_arquivo = trama_compilar_arquivo
    compilar_trama_para_arquivo = trama_compilar_para_arquivo

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
        "tamanho": tamanho,
        "lista_adicionar": lista_adicionar,
        "mapa_obter": mapa_obter,
        "mapa_definir": mapa_definir,
        "mapa_chaves": mapa_chaves,
        "ler_texto_async": ler_texto_async,
        "escrever_texto_async": escrever_texto_async,
        "trama_compilar_fonte": trama_compilar_fonte,
        "trama_compilar_arquivo": trama_compilar_arquivo,
        "trama_compilar_para_arquivo": trama_compilar_para_arquivo,
        "compilar_trama_fonte": compilar_trama_fonte,
        "compilar_trama_arquivo": compilar_trama_arquivo,
        "compilar_trama_para_arquivo": compilar_trama_para_arquivo,
        "http_get": http_get,
        "http_post": http_post,
        "http_obter": http_obter,
        "http_postar": http_postar,
        "env_obter": env_obter,
        "env_todos": env_todos,
        "config_carregar": config_carregar,
        "config_carregar_ambiente": config_carregar_ambiente,
        "config_validar": config_validar,
        "segredo_obter": segredo_obter,
        "segredo_ler": segredo_ler,
        "segredo_mascarar": segredo_mascarar,
        "cache_definir": cache_definir,
        "cache_obter": cache_obter,
        "cache_existe": cache_existe,
        "cache_remover": cache_remover,
        "cache_invalidar_padrao": cache_invalidar_padrao,
        "cache_invalida_padrao": cache_invalida_padrao,
        "cache_limpar": cache_limpar,
        "cache_aquecer": cache_aquecer,
        "cache_stats": cache_stats,
        "resiliencia_executar": resiliencia_executar,
        "circuito_status": circuito_status,
        "circuito_resetar": circuito_resetar,
        "armazenamento_criar_local": armazenamento_criar_local,
        "armazenamento_criar_s3": armazenamento_criar_s3,
        "armazenamento_local_criar": armazenamento_local_criar,
        "armazenamento_s3_criar": armazenamento_s3_criar,
        "armazenamento_salvar": armazenamento_salvar,
        "armazenamento_ler": armazenamento_ler,
        "armazenamento_remover": armazenamento_remover,
        "armazenamento_listar": armazenamento_listar,
        "armazenamento_url": armazenamento_url,
        "midia_ler_arquivo": midia_ler_arquivo,
        "midia_salvar_arquivo": midia_salvar_arquivo,
        "midia_comprimir_gzip": midia_comprimir_gzip,
        "midia_descomprimir_gzip": midia_descomprimir_gzip,
        "midia_gzip_comprimir": midia_gzip_comprimir,
        "midia_gzip_descomprimir": midia_gzip_descomprimir,
        "midia_sha256": midia_sha256,
        "midia_redimensionar_imagem": midia_redimensionar_imagem,
        "midia_converter_imagem": midia_converter_imagem,
        "midia_pipeline": midia_pipeline,
        "agora_iso": agora_iso,
        "timestamp": timestamp,
        "web_criar_app": web_criar_app,
        "web_adicionar_rota_json": web_adicionar_rota_json,
        "web_adicionar_rota_echo_json": web_adicionar_rota_echo_json,
        "web_usar_middleware": web_usar_middleware,
        "web_configurar_cors": web_configurar_cors,
        "web_ativar_healthcheck": web_ativar_healthcheck,
        "web_servir_estaticos": web_servir_estaticos,
        "web_rota": web_rota,
        "web_rota_contrato": web_rota_contrato,
        "web_rota_com_contrato": web_rota_com_contrato,
        "web_middleware": web_middleware,
        "web_tratador_erro": web_tratador_erro,
        "web_rate_limit": web_rate_limit,
        "web_limite_taxa": web_limite_taxa,
        "web_api_versionar": web_api_versionar,
        "web_api_versao": web_api_versao,
        "web_saude_paths": web_saude_paths,
        "web_ativar_observabilidade": web_ativar_observabilidade,
        "web_observabilidade_ativar": web_observabilidade_ativar,
        "web_tempo_real_rota": web_tempo_real_rota,
        "web_tempo_real_ativar_fallback": web_tempo_real_ativar_fallback,
        "web_tempo_real_definir_limites": web_tempo_real_definir_limites,
        "web_tempo_real_emitir_sala": web_tempo_real_emitir_sala,
        "web_tempo_real_emitir_usuario": web_tempo_real_emitir_usuario,
        "web_tempo_real_emitir_conexao": web_tempo_real_emitir_conexao,
        "web_tempo_real_status": web_tempo_real_status,
        "web_socket_rota": web_socket_rota,
        "web_websocket_rota": web_websocket_rota,
        "web_realtime_rota": web_realtime_rota,
        "web_realtime_ativar_fallback": web_realtime_ativar_fallback,
        "web_realtime_definir_limites": web_realtime_definir_limites,
        "web_realtime_emitir_sala": web_realtime_emitir_sala,
        "web_realtime_emitir_usuario": web_realtime_emitir_usuario,
        "web_realtime_emitir_conexao": web_realtime_emitir_conexao,
        "web_realtime_status": web_realtime_status,
        "web_iniciar": web_iniciar,
        "web_parar": web_parar,
        "pg_conectar": pg_conectar,
        "pg_fechar": pg_fechar,
        "pg_executar": pg_executar,
        "pg_consultar": pg_consultar,
        "pg_transacao_iniciar": pg_transacao_iniciar,
        "pg_transacao_commit": pg_transacao_commit,
        "pg_transacao_rollback": pg_transacao_rollback,
        "pg_tx_executar": pg_tx_executar,
        "pg_tx_consultar": pg_tx_consultar,
        "qb_select": qb_select,
        "qb_where_eq": qb_where_eq,
        "qb_order_by": qb_order_by,
        "qb_limite": qb_limite,
        "qb_sql": qb_sql,
        "qb_consultar": qb_consultar,
        "orm_inserir": orm_inserir,
        "orm_atualizar": orm_atualizar,
        "orm_buscar_por_id": orm_buscar_por_id,
        "migracao_aplicar": migracao_aplicar,
        "seed_aplicar": seed_aplicar,
        "migracao_aplicar_versionada": migracao_aplicar_versionada,
        "migracao_status": migracao_status,
        "migracao_reverter_ultima": migracao_reverter_ultima,
        "migracao_validar_compatibilidade": migracao_validar_compatibilidade,
        "banco_conectar": banco_conectar,
        "banco_fechar": banco_fechar,
        "banco_executar": banco_executar,
        "banco_consultar": banco_consultar,
        "transacao_iniciar": transacao_iniciar,
        "transacao_confirmar": transacao_confirmar,
        "transacao_cancelar": transacao_cancelar,
        "transacao_executar": transacao_executar,
        "transacao_consultar": transacao_consultar,
        "consulta_selecionar": consulta_selecionar,
        "consulta_onde_igual": consulta_onde_igual,
        "consulta_ordenar_por": consulta_ordenar_por,
        "consulta_limite": consulta_limite,
        "consulta_sql": consulta_sql,
        "consulta_executar": consulta_executar,
        "modelo_inserir": modelo_inserir,
        "modelo_atualizar": modelo_atualizar,
        "modelo_buscar_por_id": modelo_buscar_por_id,
        "semente_aplicar": semente_aplicar,
        "migracao_versionada_aplicar": migracao_versionada_aplicar,
        "migracao_listar": migracao_listar,
        "migracao_desfazer_ultima": migracao_desfazer_ultima,
        "migracao_compatibilidade_validar": migracao_compatibilidade_validar,
        "jwt_criar": jwt_criar,
        "jwt_verificar": jwt_verificar,
        "senha_hash": senha_hash,
        "senha_verificar": senha_verificar,
        "rbac_criar": rbac_criar,
        "rbac_atribuir": rbac_atribuir,
        "rbac_papeis_usuario": rbac_papeis_usuario,
        "rbac_tem_papel": rbac_tem_papel,
        "rbac_tem_permissao": rbac_tem_permissao,
        "token_criar": token_criar,
        "token_verificar": token_verificar,
        "senha_gerar_hash": senha_gerar_hash,
        "senha_validar": senha_validar,
        "papel_criar_modelo": papel_criar_modelo,
        "papel_atribuir": papel_atribuir,
        "papel_listar_usuario": papel_listar_usuario,
        "papel_tem": papel_tem,
        "permissao_tem": permissao_tem,
        "log_estruturado": log_estruturado,
        "log_estruturado_json": log_estruturado_json,
        "metrica_incrementar": metrica_incrementar,
        "metrica_observar": metrica_observar,
        "metricas_snapshot": metricas_snapshot,
        "metricas_reset": metricas_reset,
        "traco_iniciar": traco_iniciar,
        "traco_evento": traco_evento,
        "traco_finalizar": traco_finalizar,
        "tracos_snapshot": tracos_snapshot,
        "tracos_reset": tracos_reset,
        "observabilidade_resumo": observabilidade_resumo,
        "alertas_avaliar": alertas_avaliar,
        "metrica_inc": metrica_inc,
        "traca_iniciar": traca_iniciar,
        "traca_evento": traca_evento,
        "traca_finalizar": traca_finalizar,
        "tracas_snapshot": tracas_snapshot,
        "tracas_reset": tracas_reset,
        "fila_criar": fila_criar,
        "fila_enfileirar": fila_enfileirar,
        "fila_processar": fila_processar,
        "fila_status": fila_status,
        "webhook_enviar": webhook_enviar,
    }
