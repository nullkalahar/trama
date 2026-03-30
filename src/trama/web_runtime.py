"""Runtime HTTP programável da Trama (v1.0)."""

from __future__ import annotations

from dataclasses import dataclass, field
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse
import uuid

from . import observability_runtime
from . import security_runtime


def _parse_multipart_form_data(content_type: str, data: bytes) -> tuple[dict[str, object], dict[str, object]]:
    ctype = content_type.lower()
    if "multipart/form-data" not in ctype:
        return {}, {}
    if "boundary=" not in ctype:
        raise ValueError("multipart/form-data sem boundary.")

    raw = (
        f"Content-Type: {content_type}\r\n"
        "MIME-Version: 1.0\r\n"
        "\r\n"
    ).encode("utf-8") + data
    msg = BytesParser(policy=default).parsebytes(raw)
    if not msg.is_multipart():
        return {}, {}

    form: dict[str, object] = {}
    files: dict[str, object] = {}
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_param("filename", header="content-disposition")
        payload = part.get_payload(decode=True) or b""
        if filename:
            entry = {
                "campo": str(name),
                "nome_arquivo": str(filename),
                "content_type": str(part.get_content_type() or "application/octet-stream"),
                "tamanho": len(payload),
                "bytes": payload,
            }
            if name in files:
                atual = files[name]
                if isinstance(atual, list):
                    atual.append(entry)
                else:
                    files[name] = [atual, entry]
            else:
                files[name] = [entry]
        else:
            value = payload.decode("utf-8", errors="replace")
            if name in form:
                atual = form[name]
                if isinstance(atual, list):
                    atual.append(value)
                else:
                    form[name] = [atual, value]
            else:
                form[name] = value
    return form, files


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


class WebApp:
    def __init__(self) -> None:
        self.routes: list[WebRoute] = []
        self.middlewares_pre: list[object] = []
        self.middlewares_pos: list[object] = []
        self.error_handler: object | None = None
        self.middlewares: set[str] = set()
        self.cors_enabled = False
        self.cors_origin = "*"
        self.cors_methods = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
        self.cors_headers = "Content-Type,Authorization"
        self.health_path = "/saude"
        self.readiness_path = "/pronto"
        self.liveness_path = "/vivo"
        self.health_enabled = True
        self.static_prefix: str | None = None
        self.static_dir: Path | None = None
        self.rate_limits: list[RateLimitPolicy] = []
        self.api_versions: set[str] = set()
        self.observabilidade_ativa = False
        self.observabilidade_path = "/observabilidade"
        self.alertas_path = "/alertas"
        self.alertas_config: dict[str, object] = {}


class WebRuntime:
    def __init__(
        self,
        app: WebApp,
        host: str,
        port: int,
        out: Callable[[str], None],
        invoke_callable_sync: Callable[[object, list[object]], object] | None = None,
    ) -> None:
        self.app = app
        self.host = host
        self.port = port
        self.out = out
        self.invoke_callable_sync = invoke_callable_sync
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def _invoke(self, fn: object, args: list[object]) -> object:
        if self.invoke_callable_sync is None:
            raise RuntimeError("Runtime sem ponte de execução para handlers da linguagem.")
        return self.invoke_callable_sync(fn, args)

    def start(self) -> None:
        app = self.app
        out = self.out
        invoke = self._invoke

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
                return

            def _add_common_headers(self, headers: dict[str, str] | None = None) -> None:
                self.send_header("Connection", "close")
                id_req = getattr(self, "_trama_id_requisicao", None)
                id_traco = getattr(self, "_trama_id_traco", None)
                if id_req:
                    self.send_header("X-Id-Requisicao", str(id_req))
                    self.send_header("X-Request-Id", str(id_req))
                if id_traco:
                    self.send_header("X-Id-Traco", str(id_traco))
                    self.send_header("X-Trace-Id", str(id_traco))
                if app.cors_enabled:
                    self.send_header("Access-Control-Allow-Origin", app.cors_origin)
                    self.send_header("Access-Control-Allow-Methods", app.cors_methods)
                    self.send_header("Access-Control-Allow-Headers", app.cors_headers)
                if headers:
                    for k, v in headers.items():
                        self.send_header(k, v)

            def _registrar_observabilidade_resposta(self, status: int) -> None:
                if getattr(self, "_trama_obs_done", False):
                    return
                self._trama_obs_done = True

                inicio = getattr(self, "_trama_inicio_perf", None)
                if inicio is None:
                    return
                lat_ms = (time.perf_counter() - float(inicio)) * 1000.0
                metodo = str(getattr(self, "_trama_metodo", self.command))
                rota = str(getattr(self, "_trama_rota", urlparse(self.path).path))
                id_req = getattr(self, "_trama_id_requisicao", None)
                id_traco = getattr(self, "_trama_id_traco", None)
                id_usr = getattr(self, "_trama_id_usuario", None)

                observability_runtime.registrar_http_metrica(
                    metodo=metodo,
                    rota=rota,
                    status=int(status),
                    latencia_ms=lat_ms,
                    id_requisicao=str(id_req) if id_req else None,
                    id_traco=str(id_traco) if id_traco else None,
                    id_usuario=str(id_usr) if id_usr else None,
                )

                span = getattr(self, "_trama_span_raiz", None)
                if isinstance(span, dict):
                    observability_runtime.traco_evento(span, "http.resposta", {"status": int(status), "latencia_ms": lat_ms})
                    observability_runtime.traco_finalizar(
                        span,
                        status="ok" if int(status) < 500 else "erro",
                        erro=None if int(status) < 500 else f"http_status_{int(status)}",
                    )

                observability_runtime.correlacao_limpar()

            def _send_bytes(
                self,
                status: int,
                payload: bytes,
                content_type: str,
                headers: dict[str, str] | None = None,
            ) -> None:
                self._registrar_observabilidade_resposta(int(status))
                self.send_response(int(status))
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self._add_common_headers(headers)
                self.end_headers()
                self.wfile.write(payload)

            def _send_json(
                self,
                status: int,
                payload: dict[str, object],
                headers: dict[str, str] | None = None,
            ) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._send_bytes(status, body, "application/json; charset=utf-8", headers)

            def _send_text(
                self,
                status: int,
                texto: str,
                headers: dict[str, str] | None = None,
            ) -> None:
                self._send_bytes(status, texto.encode("utf-8"), "text/plain; charset=utf-8", headers)

            def _send_file(self, file_path: Path, request_id: str | None = None) -> None:
                data = file_path.read_bytes()
                mime, _ = mimetypes.guess_type(str(file_path))
                h: dict[str, str] = {}
                if request_id:
                    h["X-Request-Id"] = request_id
                self._send_bytes(200, data, mime or "application/octet-stream", h)

            def _read_body(
                self,
            ) -> tuple[bytes, dict[str, object] | None, dict[str, object], dict[str, object], tuple[int, dict[str, object]] | None]:
                raw_len = self.headers.get("Content-Length", "0")
                try:
                    length = int(raw_len)
                except ValueError:
                    return b"", None, {}, {}, (
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
                    return b"", {}, {}, {}, None
                if length > 5 * 1024 * 1024:
                    return b"", None, {}, {}, (
                        413,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "PAYLOAD_GRANDE",
                                "mensagem": "Payload excede o limite de 5MB.",
                                "detalhes": None,
                            },
                        },
                    )
                data = self.rfile.read(length)
                ctype = (self.headers.get("Content-Type") or "")
                ctype_l = ctype.lower()
                if "multipart/form-data" in ctype_l:
                    try:
                        form, files = _parse_multipart_form_data(ctype, data)
                    except Exception as exc:  # noqa: BLE001
                        return b"", None, {}, {}, (
                            400,
                            {
                                "ok": False,
                                "erro": {
                                    "codigo": "MULTIPART_INVALIDO",
                                    "mensagem": "Corpo multipart/form-data inválido.",
                                    "detalhes": str(exc),
                                },
                            },
                        )
                    return data, {}, form, files, None
                if "application/json" not in ctype_l:
                    return data, {}, {}, {}, None
                text = data.decode("utf-8", errors="replace")
                if not text.strip():
                    return data, {}, {}, {}, None
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError as exc:
                    return data, None, {}, {}, (
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
                    return data, None, {}, {}, (
                        422,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "PAYLOAD_INVALIDO",
                                "mensagem": "Payload deve ser objeto JSON.",
                                "detalhes": None,
                            },
                        },
                    )
                return data, parsed, {}, {}, None

            def _route_match(self, method: str, path: str) -> tuple[WebRoute | None, dict[str, str]]:
                for r in app.routes:
                    if r.method != method:
                        continue
                    if r.kind == "handler":
                        assert r.regex is not None
                        m = r.regex.match(path)
                        if m:
                            return r, {k: v for k, v in m.groupdict().items()}
                        continue
                    if r.path == path:
                        return r, {}
                return None, {}

            def _apply_rate_limit(
                self,
                method: str,
                path: str,
                request_id: str | None,
                req: dict[str, object],
            ) -> tuple[bool, tuple[int, dict[str, object]] | None]:
                ip = str(req.get("ip", "unknown"))
                for p in app.rate_limits:
                    if p.method not in {"*", method}:
                        continue
                    if p.path != "*" and p.path != path:
                        continue
                    key = f"{ip}:{method}:{path}"
                    if not p.allow(key):
                        headers = {"X-Request-Id": request_id} if request_id else {}
                        _ = headers
                        return False, (
                            429,
                            {
                                "ok": False,
                                "erro": {
                                    "codigo": "RATE_LIMIT_EXCEDIDO",
                                    "mensagem": "Limite de requisições excedido.",
                                    "detalhes": {"metodo": method, "caminho": path},
                                },
                            },
                        )
                return True, None

            @staticmethod
            def _validate_schema(req: dict[str, object], schema: dict[str, object]) -> list[str]:
                missing: list[str] = []
                body = req.get("corpo", {})
                query = req.get("consulta", {})
                params = req.get("parametros", {})
                for k in list(schema.get("corpo_obrigatorio", [])):
                    if not isinstance(body, dict) or k not in body:
                        missing.append(f"corpo.{k}")
                for k in list(schema.get("consulta_obrigatoria", [])):
                    if not isinstance(query, dict) or k not in query:
                        missing.append(f"consulta.{k}")
                for k in list(schema.get("parametros_obrigatorios", [])):
                    if not isinstance(params, dict) or k not in params:
                        missing.append(f"parametros.{k}")
                form = req.get("formulario", {})
                for k in list(schema.get("form_obrigatorio", [])):
                    if not isinstance(form, dict) or k not in form:
                        missing.append(f"formulario.{k}")
                files = req.get("arquivos", {})
                for k in list(schema.get("arquivos_obrigatorios", [])):
                    if not isinstance(files, dict) or k not in files:
                        missing.append(f"arquivos.{k}")
                return missing

            def _apply_auth(
                self,
                req: dict[str, object],
                options: dict[str, object],
            ) -> tuple[bool, tuple[int, dict[str, object]] | None]:
                segredo = str(options.get("jwt_segredo", "") or "")
                if not segredo:
                    return True, None
                auth = str(req["cabecalhos"].get("authorization", ""))  # type: ignore[index]
                if not auth.lower().startswith("bearer "):
                    return False, (
                        401,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "NAO_AUTENTICADO",
                                "mensagem": "Token Bearer ausente.",
                                "detalhes": None,
                            },
                        },
                    )
                token = auth.split(" ", 1)[1].strip()
                try:
                    claims = security_runtime.jwt_verificar(token, segredo)
                except Exception as exc:  # noqa: BLE001
                    return False, (
                        401,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "TOKEN_INVALIDO",
                                "mensagem": "Token inválido.",
                                "detalhes": str(exc),
                            },
                        },
                    )
                req["usuario"] = claims
                id_usuario = claims.get("id_usuario") or claims.get("user_id") or claims.get("sub")
                if id_usuario is not None:
                    req["id_usuario"] = id_usuario
                    req["user_id"] = id_usuario
                    self._trama_id_usuario = str(id_usuario)
                    observability_runtime.correlacao_definir(id_usuario=id_usuario)
                required = list(options.get("rbac_permissoes", []))
                if required:
                    user_perms = set(list(claims.get("permissoes", [])))
                    if not all(p in user_perms for p in required):
                        return False, (
                            403,
                            {
                                "ok": False,
                                "erro": {
                                    "codigo": "SEM_PERMISSAO",
                                    "mensagem": "Permissão insuficiente.",
                                    "detalhes": {"necessarias": required},
                                },
                            },
                        )
                return True, None

            def _as_response(self, value: object) -> tuple[int, dict[str, str], bytes, str]:
                if isinstance(value, dict):
                    status = int(value.get("status", 200))
                    headers_raw = value.get("cabecalhos", {})
                    headers = {str(k): str(v) for k, v in dict(headers_raw).items()} if isinstance(headers_raw, dict) else {}
                    if "texto" in value:
                        return status, headers, str(value.get("texto", "")).encode("utf-8"), "text/plain; charset=utf-8"
                    if "bytes" in value and isinstance(value["bytes"], (bytes, bytearray)):
                        ctype = str(value.get("content_type", "application/octet-stream"))
                        return status, headers, bytes(value["bytes"]), ctype
                    if "json" in value and isinstance(value["json"], dict):
                        payload = json.dumps(value["json"], ensure_ascii=False).encode("utf-8")
                        return status, headers, payload, "application/json; charset=utf-8"
                    if "corpo" in value and isinstance(value["corpo"], dict):
                        payload = json.dumps(value["corpo"], ensure_ascii=False).encode("utf-8")
                        return status, headers, payload, "application/json; charset=utf-8"
                payload = json.dumps({"ok": True, "dados": value}, ensure_ascii=False).encode("utf-8")
                return 200, {}, payload, "application/json; charset=utf-8"

            @staticmethod
            def _validate_response_contract(value: object, options: dict[str, object]) -> tuple[bool, str | None]:
                contrato = dict(options.get("contrato_resposta", {}))
                if not contrato:
                    return True, None
                required_top = list(contrato.get("campos_obrigatorios", []))
                exigir_envelope = bool(contrato.get("envelope", False))
                if not isinstance(value, dict):
                    return False, "resposta deve ser mapa para contrato"
                payload: dict[str, object]
                if "json" in value and isinstance(value["json"], dict):
                    payload = value["json"]  # type: ignore[assignment]
                elif "corpo" in value and isinstance(value["corpo"], dict):
                    payload = value["corpo"]  # type: ignore[assignment]
                else:
                    payload = value
                if exigir_envelope:
                    for k in ["ok", "dados", "erro", "meta"]:
                        if k not in payload:
                            return False, f"campo obrigatório de envelope ausente: {k}"
                for k in required_top:
                    if k not in payload:
                        return False, f"campo obrigatório ausente: {k}"
                return True, None

            def _handle_request(self) -> None:
                start = time.perf_counter()
                headers_in = {k.lower(): v for k, v in self.headers.items()}
                request_id = (
                    headers_in.get("x-id-requisicao")
                    or headers_in.get("x-request-id")
                    or str(uuid.uuid4())
                )
                trace_id = (
                    headers_in.get("x-id-traco")
                    or headers_in.get("x-trace-id")
                    or str(uuid.uuid4())
                )
                user_id_hdr = headers_in.get("x-id-usuario") or headers_in.get("x-user-id")

                self._trama_inicio_perf = start
                self._trama_obs_done = False
                self._trama_id_requisicao = str(request_id)
                self._trama_id_traco = str(trace_id)
                self._trama_id_usuario = str(user_id_hdr) if user_id_hdr else None
                self._trama_span_raiz = observability_runtime.traco_iniciar(
                    "http.requisicao",
                    {
                        "metodo": self.command,
                        "caminho": urlparse(self.path).path,
                        "id_requisicao": self._trama_id_requisicao,
                        "id_traco": self._trama_id_traco,
                    },
                )
                observability_runtime.correlacao_definir(
                    id_requisicao=self._trama_id_requisicao,
                    id_traco=self._trama_id_traco,
                    id_usuario=self._trama_id_usuario,
                )
                self._trama_metodo = self.command

                if self.command == "OPTIONS" and app.cors_enabled:
                    self._send_bytes(204, b"", "text/plain; charset=utf-8", {})
                    return

                parsed_url = urlparse(self.path)
                path = parsed_url.path
                self._trama_rota = path
                query = {k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(parsed_url.query).items()}

                if app.observabilidade_ativa and path == app.observabilidade_path:
                    resumo = observability_runtime.observabilidade_resumo(app.alertas_config)
                    self._send_json(200, resumo, {})
                    return
                if app.observabilidade_ativa and path == app.alertas_path:
                    alertas = observability_runtime.alertas_avaliar(app.alertas_config)
                    self._send_json(200, {"ok": True, "alertas": alertas}, {})
                    return

                if app.health_enabled and path in {app.health_path, app.readiness_path, app.liveness_path}:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    status = "up"
                    if path == app.readiness_path:
                        status = "ready"
                    if path == app.liveness_path:
                        status = "alive"
                    self._send_json(200, {"ok": True, "status": status}, headers)
                    return

                if app.static_prefix and app.static_dir and path.startswith(app.static_prefix):
                    rel = path[len(app.static_prefix) :].lstrip("/")
                    safe = (app.static_dir / rel).resolve()
                    base = app.static_dir.resolve()
                    if not str(safe).startswith(str(base)):
                        headers = {"X-Request-Id": request_id} if request_id else None
                        self._send_json(403, {"ok": False, "erro": {"codigo": "STATIC_FORBIDDEN"}}, headers)
                        return
                    if safe.is_file():
                        self._send_file(safe, request_id=request_id)
                        return
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(404, {"ok": False, "erro": {"codigo": "STATIC_NOT_FOUND"}}, headers)
                    return

                route, path_params = self._route_match(self.command, path)
                if route is None:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(
                        404,
                        {"ok": False, "erro": {"codigo": "ROTA_NAO_ENCONTRADA", "detalhes": {"metodo": self.command, "caminho": path}}},
                        headers,
                    )
                    return
                self._trama_rota = route.path

                if app.api_versions and route.kind == "handler":
                    if not any(path.startswith(prefix + "/") or path == prefix for prefix in app.api_versions):
                        headers = {"X-Request-Id": request_id} if request_id else None
                        self._send_json(
                            404,
                            {
                                "ok": False,
                                "erro": {
                                    "codigo": "VERSAO_API_INVALIDA",
                                    "mensagem": "Caminho não corresponde a versão de API registrada.",
                                    "detalhes": {"caminho": path},
                                },
                            },
                            headers,
                        )
                        return

                raw_body, body, form_data, files_data, body_err = self._read_body()
                if body_err:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(body_err[0], body_err[1], headers)
                    return

                headers_map = {k.lower(): v for k, v in self.headers.items()}
                req: dict[str, object] = {
                    "metodo": self.command,
                    "caminho": path,
                    "consulta": query,
                    "parametros": path_params,
                    "cabecalhos": headers_map,
                    "corpo": body or {},
                    "formulario": form_data or {},
                    "arquivos": files_data or {},
                    "corpo_raw": raw_body,
                    "ip": self.client_address[0] if self.client_address else "0.0.0.0",
                    "id_requisicao": request_id,
                    "request_id": request_id,
                    "id_traco": trace_id,
                    "trace_id": trace_id,
                    "id_usuario": self._trama_id_usuario,
                    "user_id": self._trama_id_usuario,
                }
                req["request"] = req
                req["query"] = req["consulta"]
                req["params"] = req["parametros"]
                req["headers"] = req["cabecalhos"]
                req["body"] = req["corpo"]
                req["form"] = req["formulario"]
                req["files"] = req["arquivos"]

                ok_rl, rl_err = self._apply_rate_limit(self.command, path, request_id, req)
                if not ok_rl and rl_err is not None:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(rl_err[0], rl_err[1], headers)
                    return

                if route.kind in {"json_static", "echo_json"}:
                    if route.kind == "json_static":
                        payload = {"ok": True, "dados": route.data.get("body")}
                        headers = {"X-Request-Id": request_id} if request_id else None
                        self._send_json(int(route.data.get("status", 200)), payload, headers)
                        return
                    required = list(route.data.get("required", []))
                    missing = [field for field in required if field not in (body or {})]
                    if missing:
                        headers = {"X-Request-Id": request_id} if request_id else None
                        self._send_json(
                            422,
                            {"ok": False, "erro": {"codigo": "VALIDACAO_FALHOU", "detalhes": {"faltando": missing}}},
                            headers,
                        )
                        return
                    payload = {"ok": True, "dados": {"metodo": self.command, "caminho": path, "query": query, "payload": body or {}}}
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(int(route.data.get("status", 200)), payload, headers)
                    return

                schema = dict(route.data.get("schema", {}))
                options = dict(route.data.get("options", {}))
                miss = self._validate_schema(req, schema)
                if miss:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(
                        422,
                        {"ok": False, "erro": {"codigo": "VALIDACAO_FALHOU", "detalhes": {"faltando": miss}}},
                        headers,
                    )
                    return

                auth_ok, auth_err = self._apply_auth(req, options)
                if not auth_ok and auth_err is not None:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(auth_err[0], auth_err[1], headers)
                    return

                try:
                    for mw in app.middlewares_pre:
                        mw_res = invoke(mw, [req])
                        if isinstance(mw_res, dict) and mw_res.get("parar") is True:
                            status, hdrs, body_bytes, ctype = self._as_response(mw_res.get("resposta"))
                            if request_id:
                                hdrs["X-Request-Id"] = request_id
                            self._send_bytes(status, body_bytes, ctype, hdrs)
                            return

                    result = invoke(route.data["handler"], [req])
                    ok_contract, contract_err = self._validate_response_contract(result, options)
                    if not ok_contract:
                        headers = {"X-Request-Id": request_id} if request_id else None
                        self._send_json(
                            500,
                            {
                                "ok": False,
                                "erro": {
                                    "codigo": "CONTRATO_INVALIDO",
                                    "mensagem": "Resposta do handler violou contrato da API.",
                                    "detalhes": contract_err,
                                },
                            },
                            headers,
                        )
                        return
                    status, hdrs, body_bytes, ctype = self._as_response(result)
                    resp_map: dict[str, object] = {"status": status, "cabecalhos": hdrs, "tipo": ctype}

                    for mw in app.middlewares_pos:
                        post_res = invoke(mw, [req, resp_map])
                        if isinstance(post_res, dict):
                            if "status" in post_res:
                                resp_map["status"] = int(post_res["status"])
                            if "cabecalhos" in post_res and isinstance(post_res["cabecalhos"], dict):
                                merged = dict(resp_map.get("cabecalhos", {}))
                                merged.update(post_res["cabecalhos"])
                                resp_map["cabecalhos"] = merged

                    final_headers = {str(k): str(v) for k, v in dict(resp_map.get("cabecalhos", {})).items()}
                    if request_id:
                        final_headers["X-Request-Id"] = request_id
                    self._send_bytes(int(resp_map.get("status", status)), body_bytes, ctype, final_headers)
                except Exception as exc:  # noqa: BLE001
                    if app.error_handler is not None:
                        err_payload = invoke(app.error_handler, [req, {"mensagem": str(exc)}])
                        s, h, b, c = self._as_response(err_payload)
                        if request_id:
                            h["X-Request-Id"] = request_id
                        self._send_bytes(s, b, c, h)
                        return
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(
                        500,
                        {
                            "ok": False,
                            "erro": {"codigo": "ERRO_INTERNO", "mensagem": "Falha interna no handler.", "detalhes": str(exc)},
                        },
                        headers,
                    )
                    return

                if "log_requisicao" in app.middlewares:
                    ms = (time.perf_counter() - start) * 1000.0
                    out(
                        f"[WEB] {self.command} {path} "
                        f"({ms:.2f}ms, id_requisicao={request_id}, id_traco={trace_id}, id_usuario={self._trama_id_usuario or 'n/a'})"
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
