"""Runtime HTTP programável da Trama (v1.0)."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import socket
import struct
import threading
import time
from typing import Callable
from urllib.parse import parse_qs, urlparse
import uuid
import unicodedata

from . import cache_runtime
from . import observability_runtime
from . import security_runtime
from .realtime_core import TempoRealConexao, TempoRealHub
from .realtime_fallback_http import processar_fallback_tempo_real_http
from .realtime_websocket import processar_upgrade_websocket_tempo_real
from .web_app_model import ConfiguracaoWebApp, aplicar_configuracao_web_app
from .web_engine import EngineHttpAsgiReal, EngineHttpServerLegado, EngineRuntimeHttp
from .web_model import RateLimitDistribuidoPolicy, RateLimitPolicy, WebRoute


def _erro_campo_validacao(
    codigo: str,
    campo: str,
    mensagem: str,
    detalhes: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "codigo": str(codigo),
        "campo": str(campo),
        "mensagem": str(mensagem),
        "detalhes": dict(detalhes or {}),
    }


def _coagir_logico(valor: object) -> tuple[bool, bool]:
    if isinstance(valor, bool):
        return True, valor
    if isinstance(valor, (int, float)):
        if float(valor) == 1.0:
            return True, True
        if float(valor) == 0.0:
            return True, False
        return False, False
    if isinstance(valor, str):
        v = valor.strip().lower()
        if v in {"1", "true", "verdadeiro", "sim", "s", "on"}:
            return True, True
        if v in {"0", "false", "falso", "nao", "não", "n", "off"}:
            return True, False
    return False, False


def _normalizar_texto(valor: str, sanitizar: dict[str, object]) -> str:
    out = valor
    if bool(sanitizar.get("trim", True)):
        out = out.strip()
    if bool(sanitizar.get("colapsar_espacos", False)):
        out = re.sub(r"\s+", " ", out)
    if bool(sanitizar.get("minusculo", False)):
        out = out.lower()
    if bool(sanitizar.get("maiusculo", False)):
        out = out.upper()
    if bool(sanitizar.get("remover_acentos", False)):
        decomposed = unicodedata.normalize("NFD", out)
        out = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    if bool(sanitizar.get("remover_html", False)):
        out = re.sub(r"<[^>]+>", "", out)
    return out


def _normalizar_spec_dto(spec: object) -> dict[str, object]:
    if isinstance(spec, str):
        return {"tipo": spec}
    if not isinstance(spec, dict):
        return {}
    obj = dict(spec)
    if "tipo" in obj:
        return obj
    if "campos" in obj or "propriedades" in obj:
        obj["tipo"] = obj.get("tipo", "objeto")
        return obj
    # shorthand: mapa de campos
    if obj and all(isinstance(k, str) for k in obj.keys()):
        return {"tipo": "objeto", "campos": obj}
    return obj


def _validar_dto_valor(
    valor: object,
    spec_raw: object,
    *,
    campo: str,
    erros: list[dict[str, object]],
    aplicar_padrao: bool = True,
) -> object:
    spec = _normalizar_spec_dto(spec_raw)
    tipo = str(spec.get("tipo", "qualquer")).lower()

    if valor is None:
        if "padrao" in spec and aplicar_padrao:
            return spec.get("padrao")
        if bool(spec.get("permitir_nulo", False)):
            return None
        erros.append(
            _erro_campo_validacao(
                "CAMPO_NULO_NAO_PERMITIDO",
                campo,
                "Campo não permite valor nulo.",
                {"tipo_esperado": tipo},
            )
        )
        return None

    if "enum" in spec:
        enum_vals = list(spec.get("enum", []))
        if valor not in enum_vals:
            erros.append(
                _erro_campo_validacao(
                    "VALOR_FORA_ENUM",
                    campo,
                    "Valor fora do conjunto permitido.",
                    {"permitidos": enum_vals},
                )
            )
            return valor

    coagir = bool(spec.get("coagir", False))
    if tipo in {"texto", "string"}:
        texto: str
        if isinstance(valor, str):
            texto = valor
        elif coagir:
            texto = str(valor)
        else:
            erros.append(_erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "texto"}))
            return valor
        texto = _normalizar_texto(texto, dict(spec.get("sanitizar", {})))
        tmin = spec.get("tamanho_min")
        tmax = spec.get("tamanho_max")
        if isinstance(tmin, (int, float)) and len(texto) < int(tmin):
            erros.append(
                _erro_campo_validacao(
                    "TAMANHO_MINIMO_INVALIDO",
                    campo,
                    "Texto abaixo do tamanho mínimo.",
                    {"tamanho_min": int(tmin), "tamanho_atual": len(texto)},
                )
            )
        if isinstance(tmax, (int, float)) and len(texto) > int(tmax):
            erros.append(
                _erro_campo_validacao(
                    "TAMANHO_MAXIMO_INVALIDO",
                    campo,
                    "Texto acima do tamanho máximo.",
                    {"tamanho_max": int(tmax), "tamanho_atual": len(texto)},
                )
            )
        return texto

    if tipo in {"inteiro", "int"}:
        out: int
        if isinstance(valor, bool):
            erros.append(_erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "inteiro"}))
            return valor
        if isinstance(valor, int):
            out = valor
        elif coagir and isinstance(valor, str) and re.fullmatch(r"[+-]?\d+", valor.strip()):
            out = int(valor.strip())
        elif coagir and isinstance(valor, float) and float(valor).is_integer():
            out = int(valor)
        else:
            erros.append(_erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "inteiro"}))
            return valor
        minimo = spec.get("minimo")
        maximo = spec.get("maximo")
        if isinstance(minimo, (int, float)) and out < int(minimo):
            erros.append(
                _erro_campo_validacao(
                    "VALOR_MINIMO_INVALIDO",
                    campo,
                    "Valor abaixo do mínimo.",
                    {"minimo": int(minimo), "valor": out},
                )
            )
        if isinstance(maximo, (int, float)) and out > int(maximo):
            erros.append(
                _erro_campo_validacao(
                    "VALOR_MAXIMO_INVALIDO",
                    campo,
                    "Valor acima do máximo.",
                    {"maximo": int(maximo), "valor": out},
                )
            )
        return out

    if tipo in {"numero", "float", "decimal"}:
        out_num: float
        if isinstance(valor, bool):
            erros.append(_erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "numero"}))
            return valor
        if isinstance(valor, (int, float)):
            out_num = float(valor)
        elif coagir and isinstance(valor, str):
            try:
                out_num = float(valor.strip())
            except ValueError:
                erros.append(_erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "numero"}))
                return valor
        else:
            erros.append(_erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "numero"}))
            return valor
        minimo = spec.get("minimo")
        maximo = spec.get("maximo")
        if isinstance(minimo, (int, float)) and out_num < float(minimo):
            erros.append(
                _erro_campo_validacao(
                    "VALOR_MINIMO_INVALIDO",
                    campo,
                    "Valor abaixo do mínimo.",
                    {"minimo": float(minimo), "valor": out_num},
                )
            )
        if isinstance(maximo, (int, float)) and out_num > float(maximo):
            erros.append(
                _erro_campo_validacao(
                    "VALOR_MAXIMO_INVALIDO",
                    campo,
                    "Valor acima do máximo.",
                    {"maximo": float(maximo), "valor": out_num},
                )
            )
        return out_num

    if tipo in {"logico", "bool", "booleano"}:
        ok_log, out_log = _coagir_logico(valor) if coagir or isinstance(valor, bool) else (False, False)
        if not ok_log:
            erros.append(_erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "logico"}))
            return valor
        return out_log

    if tipo in {"lista", "array"}:
        if not isinstance(valor, list):
            if coagir and isinstance(valor, tuple):
                valor = list(valor)
            else:
                erros.append(_erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "lista"}))
                return valor
        itens_spec = spec.get("itens")
        out_list: list[object] = []
        for idx, item in enumerate(valor):
            item_campo = f"{campo}[{idx}]"
            if itens_spec is None:
                out_list.append(item)
            else:
                out_list.append(_validar_dto_valor(item, itens_spec, campo=item_campo, erros=erros, aplicar_padrao=False))
        tmin = spec.get("tamanho_min")
        tmax = spec.get("tamanho_max")
        if isinstance(tmin, (int, float)) and len(out_list) < int(tmin):
            erros.append(
                _erro_campo_validacao(
                    "TAMANHO_MINIMO_INVALIDO",
                    campo,
                    "Lista abaixo do tamanho mínimo.",
                    {"tamanho_min": int(tmin), "tamanho_atual": len(out_list)},
                )
            )
        if isinstance(tmax, (int, float)) and len(out_list) > int(tmax):
            erros.append(
                _erro_campo_validacao(
                    "TAMANHO_MAXIMO_INVALIDO",
                    campo,
                    "Lista acima do tamanho máximo.",
                    {"tamanho_max": int(tmax), "tamanho_atual": len(out_list)},
                )
            )
        return out_list

    if tipo in {"mapa", "objeto", "dict"}:
        if not isinstance(valor, dict):
            erros.append(_erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "objeto"}))
            return valor
        campos = spec.get("campos")
        if not isinstance(campos, dict):
            campos = spec.get("propriedades")
        campos_map = dict(campos or {})
        permitir_extras = bool(spec.get("permitir_campos_extras", True))
        out_obj: dict[str, object] = {}
        for nome_raw, campo_spec in campos_map.items():
            nome = str(nome_raw)
            campo_path = f"{campo}.{nome}" if campo else nome
            if nome not in valor:
                norm_spec = _normalizar_spec_dto(campo_spec)
                if "padrao" in norm_spec:
                    out_obj[nome] = norm_spec.get("padrao")
                    continue
                if bool(norm_spec.get("obrigatorio", False)):
                    erros.append(
                        _erro_campo_validacao(
                            "CAMPO_OBRIGATORIO_AUSENTE",
                            campo_path,
                            "Campo obrigatório ausente.",
                            {},
                        )
                    )
                continue
            out_obj[nome] = _validar_dto_valor(valor.get(nome), campo_spec, campo=campo_path, erros=erros)
        if permitir_extras:
            for k, v in valor.items():
                if str(k) not in campos_map:
                    out_obj[str(k)] = v
        return out_obj

    # tipo qualquer/desconhecido: preserva valor
    return valor


def dto_validar_payload(
    dto_requisicao: dict[str, object],
    payload: object,
    *,
    contexto: str = "corpo",
) -> dict[str, object]:
    dto = dict(dto_requisicao or {})
    contexto_norm = str(contexto or "corpo")
    spec_contexto = dto.get(contexto_norm, dto)
    if isinstance(spec_contexto, dict) and contexto_norm in {"corpo", "consulta", "parametros", "formulario"}:
        # Se recebeu um mapa com múltiplos contextos e o contexto existe, usa apenas ele.
        if any(k in dto for k in ["corpo", "consulta", "parametros", "formulario"]) and contexto_norm in dto:
            spec_contexto = dto[contexto_norm]
    erros: list[dict[str, object]] = []
    dados = _validar_dto_valor(payload, spec_contexto, campo=contexto_norm, erros=erros)
    return {"ok": len(erros) == 0, "dados": dados, "erros": erros}


def dto_gerar_exemplos(dto_requisicao: dict[str, object], *, contexto: str = "corpo") -> dict[str, object]:
    dto = dict(dto_requisicao or {})
    contexto_norm = str(contexto or "corpo")
    spec_contexto = dto.get(contexto_norm, dto)
    if isinstance(spec_contexto, dict) and any(k in dto for k in ["corpo", "consulta", "parametros", "formulario"]):
        spec_contexto = dto.get(contexto_norm, {})
    exemplo_base = _gerar_exemplo_por_spec(spec_contexto)
    invalidos = _gerar_exemplos_invalidos_por_spec(spec_contexto, contexto_norm)
    return {"validos": [exemplo_base], "invalidos": invalidos}


def _gerar_exemplo_por_spec(spec_raw: object) -> object:
    spec = _normalizar_spec_dto(spec_raw)
    tipo = str(spec.get("tipo", "qualquer")).lower()
    if "padrao" in spec:
        return spec.get("padrao")
    if "enum" in spec:
        enum_vals = list(spec.get("enum", []))
        if enum_vals:
            return enum_vals[0]
    if tipo in {"texto", "string"}:
        return "texto"
    if tipo in {"inteiro", "int"}:
        return 1
    if tipo in {"numero", "float", "decimal"}:
        return 1.5
    if tipo in {"logico", "bool", "booleano"}:
        return True
    if tipo in {"lista", "array"}:
        item = _gerar_exemplo_por_spec(spec.get("itens", {"tipo": "texto"}))
        return [item]
    if tipo in {"mapa", "objeto", "dict"}:
        campos = spec.get("campos")
        if not isinstance(campos, dict):
            campos = spec.get("propriedades")
        out: dict[str, object] = {}
        for k, v in dict(campos or {}).items():
            s = _normalizar_spec_dto(v)
            if bool(s.get("obrigatorio", False)) or "padrao" in s:
                out[str(k)] = _gerar_exemplo_por_spec(v)
        return out
    return "valor"


def _gerar_exemplos_invalidos_por_spec(spec_raw: object, campo: str) -> list[dict[str, object]]:
    spec = _normalizar_spec_dto(spec_raw)
    tipo = str(spec.get("tipo", "qualquer")).lower()
    invalidos: list[dict[str, object]] = []
    if tipo in {"inteiro", "int", "numero", "float", "decimal"}:
        invalidos.append(
            {
                "descricao": "tipo_invalido",
                "entrada": "abc",
                "erro_esperado": _erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": tipo}),
            }
        )
    elif tipo in {"logico", "bool", "booleano"}:
        invalidos.append(
            {
                "descricao": "tipo_invalido",
                "entrada": "talvez",
                "erro_esperado": _erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "logico"}),
            }
        )
    elif tipo in {"texto", "string"}:
        invalidos.append(
            {
                "descricao": "tipo_invalido",
                "entrada": 123,
                "erro_esperado": _erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "texto"}),
            }
        )
    elif tipo in {"mapa", "objeto", "dict"}:
        invalidos.append(
            {
                "descricao": "tipo_invalido",
                "entrada": "nao_objeto",
                "erro_esperado": _erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "objeto"}),
            }
        )
    elif tipo in {"lista", "array"}:
        invalidos.append(
            {
                "descricao": "tipo_invalido",
                "entrada": {},
                "erro_esperado": _erro_campo_validacao("TIPO_INVALIDO", campo, "Tipo inválido.", {"tipo_esperado": "lista"}),
            }
        )
    else:
        invalidos.append(
            {
                "descricao": "campo_ausente",
                "entrada": None,
                "erro_esperado": _erro_campo_validacao(
                    "CAMPO_NULO_NAO_PERMITIDO",
                    campo,
                    "Campo não permite valor nulo.",
                    {"tipo_esperado": tipo},
                ),
            }
        )
    return invalidos


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


@dataclass
class WebApp:
    def __init__(self) -> None:
        self.routes: list[WebRoute] = []
        self.middlewares_pre: list[object] = []
        self.middlewares_pos: list[object] = []
        self.error_handler: object | None = None
        self.middlewares: set[str] = set()
        self.rate_limits: list[RateLimitPolicy] = []
        self.rate_limits_distribuidos: list[RateLimitDistribuidoPolicy] = []
        cfg = ConfiguracaoWebApp()
        cfg.static_dir = None
        aplicar_configuracao_web_app(self, cfg)
        self.static_dir: Path | None = None
        self.tempo_real = TempoRealHub()


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
        self._proxy_server: ThreadingHTTPServer | None = None
        self._proxy_thread: threading.Thread | None = None
        self._proxy_port: int | None = None
        self._asgi_server: object | None = None
        self._asgi_thread: threading.Thread | None = None
        self._estado_inicializado = False
        self._estado_pronto = False
        self._estado_drenando = False
        self._estado_falha: str | None = None
        self._engine_ativa_nome = "legada"
        self.engine_http: EngineRuntimeHttp = EngineHttpServerLegado(
            iniciar=self._start_legacy_httpserver,
            parar=self._stop_legacy_httpserver,
        )
        self._configurar_engine_preferida()

    def _configurar_engine_preferida(self) -> None:
        preferida = str(getattr(self.app, "engine_http_preferida", "legada") or "legada").strip().lower()
        if preferida in {"asgi", "asgi_real"}:
            self.engine_http = EngineHttpAsgiReal(
                iniciar=self._start_asgi_httpserver,
                parar=self._stop_asgi_httpserver,
            )
            return
        self.engine_http = EngineHttpServerLegado(
            iniciar=self._start_legacy_httpserver,
            parar=self._stop_legacy_httpserver,
        )

    def _limites_engine(self) -> dict[str, object]:
        engine = str(getattr(self, "_engine_ativa_nome", getattr(self.engine_http, "nome", "legada")) or "legada")
        mapa = dict(getattr(self.app, "limites_operacionais_por_engine", {}) or {})
        base = dict(mapa.get("legada", {}))
        if engine in mapa:
            base.update(dict(mapa.get(engine, {})))
        return base

    def _limite_payload_bytes(self) -> int:
        limite = self._limites_engine().get("max_body_bytes", 5 * 1024 * 1024)
        try:
            out = int(limite)
        except Exception:
            out = 5 * 1024 * 1024
        return max(out, 1024)

    def _status_saude(self, tipo: str) -> tuple[int, dict[str, object]]:
        engine = str(getattr(self.engine_http, "nome", "legada"))
        base = {
            "ok": True,
            "engine": engine,
            "status": "up",
            "drenando": bool(self._estado_drenando),
            "pronto": bool(self._estado_pronto),
            "inicializado": bool(self._estado_inicializado),
            "limites": self._limites_engine(),
        }
        if self._estado_falha:
            base["ok"] = False
            base["status"] = "erro"
            base["falha"] = str(self._estado_falha)
            return 503, base
        if tipo == "liveness":
            if not self._estado_inicializado:
                base["ok"] = False
                base["status"] = "iniciando"
                return 503, base
            base["status"] = "alive"
            return 200, base
        if tipo == "readiness":
            if not self._estado_pronto or self._estado_drenando:
                base["ok"] = False
                base["status"] = "not_ready" if not self._estado_drenando else "draining"
                return 503, base
            base["status"] = "ready"
            return 200, base
        if not self._estado_inicializado:
            base["ok"] = False
            base["status"] = "iniciando"
            return 503, base
        if not self._estado_pronto or self._estado_drenando:
            base["ok"] = False
            base["status"] = "degradado"
            return 503, base
        return 200, base

    def _invoke(self, fn: object, args: list[object]) -> object:
        if self.invoke_callable_sync is None:
            raise RuntimeError("Runtime sem ponte de execução para handlers da linguagem.")
        return self.invoke_callable_sync(fn, args)

    def start(self) -> None:
        self._estado_inicializado = False
        self._estado_pronto = False
        self._estado_drenando = False
        self._estado_falha = None
        self._engine_ativa_nome = str(getattr(self.engine_http, "nome", "legada"))
        fallback = bool(getattr(self.app, "engine_http_fallback_automatico", True))
        try:
            self.engine_http.iniciar()
            self._estado_inicializado = True
            self._estado_pronto = True
            self._engine_ativa_nome = str(getattr(self.engine_http, "nome", "legada"))
        except Exception as exc:
            self._estado_falha = str(exc)
            if fallback and str(getattr(self.engine_http, "nome", "")) == "asgi":
                self.out(f"[WEB] fallback para engine legada: {exc}")
                self.engine_http = EngineHttpServerLegado(
                    iniciar=self._start_legacy_httpserver,
                    parar=self._stop_legacy_httpserver,
                )
                self._estado_falha = None
                self.engine_http.iniciar()
                self._estado_inicializado = True
                self._estado_pronto = True
                self._engine_ativa_nome = "legada"
                return
            raise

    def _start_asgi_httpserver(self) -> None:
        try:
            import uvicorn  # type: ignore
        except Exception as exc:  # pragma: no cover - dependência opcional
            raise RuntimeError("Engine ASGI requer dependência opcional 'uvicorn'.") from exc

        host_publico = self.host
        porta_publica = int(self.port)
        self._start_proxy_legacy_backend()
        if self._proxy_port is None:
            raise RuntimeError("Falha ao iniciar backend legado interno para ASGI.")

        limite_payload = self._limite_payload_bytes()
        timeout_leitura = float(self._limites_engine().get("timeout_leitura_segundos", 20.0) or 20.0)
        proxy_port = int(self._proxy_port)

        async def asgi_app(scope: dict[str, object], receive: object, send: object) -> None:
            if str(scope.get("type")) != "http":
                await send({"type": "http.response.start", "status": 501, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
                await send({"type": "http.response.body", "body": b"tipo ASGI nao suportado", "more_body": False})
                return

            metodo = str(scope.get("method", "GET")).upper()
            raw_path = str(scope.get("raw_path", b"").decode("latin-1") if isinstance(scope.get("raw_path"), (bytes, bytearray)) else "")
            if not raw_path:
                raw_path = str(scope.get("path", "/"))
            raw_query = scope.get("query_string", b"")
            query = raw_query.decode("latin-1") if isinstance(raw_query, (bytes, bytearray)) else ""
            destino = raw_path + (f"?{query}" if query else "")

            headers_scope = list(scope.get("headers", []))
            headers_dict: dict[str, str] = {}
            for item in headers_scope:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    continue
                k_raw, v_raw = item
                if not isinstance(k_raw, (bytes, bytearray)) or not isinstance(v_raw, (bytes, bytearray)):
                    continue
                headers_dict[k_raw.decode("latin-1")] = v_raw.decode("latin-1")

            body = bytearray()
            while True:
                evento = await receive()
                if not isinstance(evento, dict):
                    break
                if str(evento.get("type")) != "http.request":
                    break
                chunk = evento.get("body", b"")
                if isinstance(chunk, (bytes, bytearray)):
                    body.extend(chunk)
                if len(body) > limite_payload:
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 413,
                            "headers": [(b"content-type", b"application/json; charset=utf-8")],
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": json.dumps(
                                {"ok": False, "erro": {"codigo": "PAYLOAD_GRANDE", "mensagem": "Payload excede o limite da engine ASGI."}},
                                ensure_ascii=False,
                            ).encode("utf-8"),
                            "more_body": False,
                        }
                    )
                    return
                if not bool(evento.get("more_body", False)):
                    break

            conn = http.client.HTTPConnection("127.0.0.1", proxy_port, timeout=timeout_leitura)
            try:
                conn.request(metodo, destino, body=bytes(body), headers=headers_dict)
                resp = conn.getresponse()
                status = int(resp.status)
                payload = resp.read()
                headers_out: list[tuple[bytes, bytes]] = []
                for hk, hv in resp.getheaders():
                    hk_l = str(hk).lower()
                    if hk_l in {"connection", "transfer-encoding", "keep-alive"}:
                        continue
                    headers_out.append((str(hk).encode("latin-1"), str(hv).encode("latin-1")))
                await send({"type": "http.response.start", "status": status, "headers": headers_out})
                await send({"type": "http.response.body", "body": payload, "more_body": False})
            except Exception as exc:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 502,
                        "headers": [(b"content-type", b"application/json; charset=utf-8")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": json.dumps(
                            {"ok": False, "erro": {"codigo": "ASGI_PROXY_FALHA", "mensagem": "Falha no proxy ASGI interno.", "detalhes": str(exc)}},
                            ensure_ascii=False,
                        ).encode("utf-8"),
                        "more_body": False,
                    }
                )
            finally:
                conn.close()

        try:
            config = uvicorn.Config(  # type: ignore[attr-defined]
                asgi_app,
                host=host_publico,
                port=porta_publica,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(config)  # type: ignore[attr-defined]
            th = threading.Thread(target=server.run, daemon=True)
            th.start()

            limite_espera = time.time() + 8.0
            while time.time() < limite_espera:
                if bool(getattr(server, "started", False)):
                    break
                if not th.is_alive():
                    raise RuntimeError("Engine ASGI encerrou durante bootstrap.")
                time.sleep(0.05)
            if not bool(getattr(server, "started", False)):
                raise RuntimeError("Timeout ao iniciar engine ASGI.")

            self._asgi_server = server
            self._asgi_thread = th
            try:
                servers = list(getattr(server, "servers", []) or [])
                if servers:
                    sockets = list(getattr(servers[0], "sockets", []) or [])
                    if sockets:
                        self.port = int(sockets[0].getsockname()[1])
            except Exception:
                pass
        except Exception:
            self._stop_proxy_legacy_backend()
            raise

    def _stop_asgi_httpserver(self) -> None:
        self._estado_drenando = True
        timeout = float(getattr(self.app, "shutdown_gracioso_segundos", 5.0) or 5.0)
        server = self._asgi_server
        th = self._asgi_thread
        if server is not None:
            try:
                setattr(server, "should_exit", True)
            except Exception:
                pass
        if th is not None and th.is_alive():
            th.join(timeout=max(timeout, 0.1))
        self._asgi_server = None
        self._asgi_thread = None
        self._stop_proxy_legacy_backend()

    def _start_proxy_legacy_backend(self) -> None:
        old_host, old_port = self.host, int(self.port)
        old_server, old_thread = self.server, self.thread
        try:
            self.host = "127.0.0.1"
            self.port = 0
            self._start_legacy_httpserver()
            self._proxy_server = self.server
            self._proxy_thread = self.thread
            self._proxy_port = int(self.port)
        finally:
            self.server = old_server
            self.thread = old_thread
            self.host = old_host
            self.port = old_port

    def _stop_proxy_legacy_backend(self) -> None:
        if self._proxy_server is not None:
            self._proxy_server.shutdown()
            self._proxy_server.server_close()
        if self._proxy_thread is not None and self._proxy_thread.is_alive():
            timeout = float(getattr(self.app, "shutdown_gracioso_segundos", 5.0) or 5.0)
            self._proxy_thread.join(timeout=max(timeout, 0.1))
        self._proxy_server = None
        self._proxy_thread = None
        self._proxy_port = None

    def _start_legacy_httpserver(self) -> None:
        app = self.app
        out = self.out
        invoke = self._invoke
        runtime_ref = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
                return

            @staticmethod
            def _origens_configuradas_por_ambiente(app_obj: WebApp, ambiente: str) -> list[str]:
                if app_obj.cors_enabled and str(app_obj.cors_origin).strip():
                    return [x.strip() for x in str(app_obj.cors_origin).split(",") if x.strip()]
                return list(app_obj.cors_origens_por_ambiente.get(ambiente, []))

            def _resolver_cors(self, origem: str | None) -> tuple[bool, str | None]:
                ambiente = str(app.ambiente or "dev").strip().lower() or "dev"
                origem_txt = str(origem or "").strip()
                permitidas = self._origens_configuradas_por_ambiente(app, ambiente)
                if not origem_txt:
                    return True, None
                if not permitidas:
                    return False, None
                if "*" in permitidas:
                    if ambiente == "producao":
                        return False, None
                    return True, "*"
                if origem_txt in permitidas:
                    return True, origem_txt
                return False, None

            def _headers_cors(self) -> dict[str, str]:
                origem = str(self.headers.get("Origin", "") or "")
                ok, origem_resp = self._resolver_cors(origem)
                if not ok:
                    return {}
                out_h: dict[str, str] = {}
                if not origem_resp and not origem:
                    ambiente = str(app.ambiente or "dev").strip().lower() or "dev"
                    if app.cors_enabled and str(app.cors_origin).strip() == "*" and ambiente != "producao":
                        origem_resp = "*"
                if origem_resp:
                    out_h["Access-Control-Allow-Origin"] = origem_resp
                    out_h["Vary"] = "Origin"
                out_h["Access-Control-Allow-Methods"] = app.cors_methods
                out_h["Access-Control-Allow-Headers"] = app.cors_headers
                out_h["Access-Control-Expose-Headers"] = "X-Request-Id,X-Id-Requisicao,X-Trace-Id,X-Id-Traco"
                return out_h

            def _add_common_headers(self, headers: dict[str, str] | None = None) -> None:
                eh_upgrade_ws = str(self.headers.get("Upgrade", "")).lower() == "websocket"
                if not eh_upgrade_ws:
                    self.send_header("Connection", "close")
                id_req = getattr(self, "_trama_id_requisicao", None)
                id_traco = getattr(self, "_trama_id_traco", None)
                if id_req:
                    self.send_header("X-Id-Requisicao", str(id_req))
                    self.send_header("X-Request-Id", str(id_req))
                if id_traco:
                    self.send_header("X-Id-Traco", str(id_traco))
                    self.send_header("X-Trace-Id", str(id_traco))
                for hk, hv in self._headers_cors().items():
                    self.send_header(hk, hv)
                csp = str(app.csp_por_ambiente.get(str(app.ambiente or "dev"), "") or "").strip()
                if csp:
                    self.send_header("Content-Security-Policy", csp)
                for hk, hv in app.seguranca_http_headers.items():
                    self.send_header(str(hk), str(hv))
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
                limite_payload = runtime_ref._limite_payload_bytes()
                if length > limite_payload:
                    return b"", None, {}, {}, (
                        413,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "PAYLOAD_GRANDE",
                                "mensagem": "Payload excede o limite operacional da engine.",
                                "detalhes": {"limite_bytes": int(limite_payload)},
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

            @staticmethod
            def _ws_accept_key(sec_key: str) -> str:
                seed = (str(sec_key).strip() + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("utf-8")
                return base64.b64encode(hashlib.sha1(seed).digest()).decode("ascii")

            @staticmethod
            def _ws_send_frame(sock: socket.socket, payload: bytes, opcode: int = 0x1) -> None:
                b1 = 0x80 | (opcode & 0x0F)
                ln = len(payload)
                if ln <= 125:
                    header = bytes([b1, ln])
                elif ln <= 65535:
                    header = bytes([b1, 126]) + struct.pack("!H", ln)
                else:
                    header = bytes([b1, 127]) + struct.pack("!Q", ln)
                sock.sendall(header + payload)

            @staticmethod
            def _ws_recv_exact(sock: socket.socket, n: int) -> bytes:
                chunks: list[bytes] = []
                total = 0
                while total < n:
                    part = sock.recv(n - total)
                    if not part:
                        raise ConnectionError("conexão websocket encerrada")
                    chunks.append(part)
                    total += len(part)
                return b"".join(chunks)

            def _ws_recv_frame(self, sock: socket.socket) -> tuple[int, bytes]:
                hdr = self._ws_recv_exact(sock, 2)
                b1, b2 = hdr[0], hdr[1]
                opcode = b1 & 0x0F
                masked = (b2 & 0x80) != 0
                plen = b2 & 0x7F
                if plen == 126:
                    plen = struct.unpack("!H", self._ws_recv_exact(sock, 2))[0]
                elif plen == 127:
                    plen = struct.unpack("!Q", self._ws_recv_exact(sock, 8))[0]
                if plen > int(app.tempo_real.limites["max_payload_bytes"]):
                    raise ValueError("payload websocket excede limite")
                mask = self._ws_recv_exact(sock, 4) if masked else b""
                payload = self._ws_recv_exact(sock, int(plen))
                if masked:
                    payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
                return opcode, payload

            @staticmethod
            def _bearer_token_from_headers(headers_map: dict[str, str]) -> str | None:
                auth = str(headers_map.get("authorization", ""))
                if auth.lower().startswith("bearer "):
                    return auth.split(" ", 1)[1].strip()
                return None

            def _auth_ws_usuario(
                self,
                headers_map: dict[str, str],
                query: dict[str, object],
                opcoes: dict[str, object],
            ) -> tuple[bool, dict[str, object] | None, dict[str, object] | None]:
                segredo = str(opcoes.get("jwt_segredo", "") or "")
                if not segredo:
                    return True, {"usuario": None, "id_usuario": None}, None
                token = (
                    self._bearer_token_from_headers(headers_map)
                    or str(query.get("token", "") or "")
                    or str(query.get("jwt", "") or "")
                )
                if not token:
                    return False, None, {"codigo": "NAO_AUTENTICADO", "mensagem": "Token JWT ausente para websocket."}
                try:
                    claims = security_runtime.jwt_verificar(token, segredo)
                except Exception as exc:  # noqa: BLE001
                    return False, None, {"codigo": "TOKEN_INVALIDO", "mensagem": "Token JWT inválido.", "detalhes": str(exc)}
                if bool(opcoes.get("jwt_validar_revogacao", True)) and security_runtime.token_esta_bloqueado(token):
                    return False, None, {"codigo": "TOKEN_REVOGADO", "mensagem": "Token JWT revogado.", "detalhes": None}
                if bool(opcoes.get("jwt_exigir_sessao_ativa", False)):
                    id_sessao = claims.get("sid") or claims.get("id_sessao")
                    if not isinstance(id_sessao, str) or not security_runtime.sessao_ativa(id_sessao):
                        return False, None, {"codigo": "SESSAO_INVALIDA", "mensagem": "Sessão inválida para websocket.", "detalhes": None}
                id_usuario = claims.get("id_usuario") or claims.get("user_id") or claims.get("sub")
                return True, {"usuario": claims, "id_usuario": str(id_usuario) if id_usuario is not None else None}, None

            def _ctx_conexao(self, c: TempoRealConexao, extras: dict[str, object] | None = None) -> dict[str, object]:
                base = {
                    "id_conexao": c.id_conexao,
                    "connection_id": c.id_conexao,
                    "canal": c.canal,
                    "channel": c.canal,
                    "id_usuario": c.id_usuario,
                    "user_id": c.id_usuario,
                    "id_requisicao": c.id_requisicao,
                    "request_id": c.id_requisicao,
                    "id_traco": c.id_traco,
                    "trace_id": c.id_traco,
                    "ip": c.ip,
                    "modo": c.modo,
                    "salas": sorted(c.salas),
                }
                if extras:
                    base.update(extras)
                return base

            def _emitir_evento_ws(self, c: TempoRealConexao, payload: dict[str, object]) -> None:
                if c.socket_conn is None:
                    c.enfileirar(payload)
                    return
                self._ws_send_frame(c.socket_conn, json.dumps(payload, ensure_ascii=False).encode("utf-8"), opcode=0x1)

            def _processar_mensagem_tempo_real(
                self,
                c: TempoRealConexao,
                msg: dict[str, object],
                invoke: Callable[[object, list[object]], object],
                rota_info: dict[str, object],
            ) -> None:
                tipo = str(msg.get("tipo") or msg.get("type") or "")
                if "socketio_evento" in msg and not tipo:
                    tipo = str(msg.get("socketio_evento") or "")
                if not app.tempo_real.validar_rate(c, msg):
                    self._emitir_evento_ws(c, {"ok": False, "erro": {"codigo": "RATE_MENSAGENS_EXCEDIDO"}})
                    return

                if tipo == "ping":
                    c.ultimo_heartbeat_em = time.time()
                    self._emitir_evento_ws(c, {"ok": True, "evento": "pong", "ts": c.ultimo_heartbeat_em})
                    return
                if tipo == "entrar_sala":
                    sala = str(msg.get("sala") or "")
                    ok, err = app.tempo_real.entrar_sala(c, sala)
                    if not ok:
                        self._emitir_evento_ws(c, {"ok": False, "erro": err})
                        return
                    app.tempo_real.emitir(c.canal, "sala_entrada", {"sala": sala, "id_conexao": c.id_conexao, "id_usuario": c.id_usuario}, sala=sala, origem=c)
                    self._emitir_evento_ws(c, {"ok": True, "evento": "entrar_sala", "sala": sala})
                    return
                if tipo == "sair_sala":
                    sala = str(msg.get("sala") or "")
                    app.tempo_real.sair_sala(c, sala)
                    self._emitir_evento_ws(c, {"ok": True, "evento": "sair_sala", "sala": sala})
                    return
                if tipo == "typing":
                    sala = str(msg.get("sala") or "")
                    app.tempo_real.emitir(c.canal, "typing", {"sala": sala, "digitando": bool(msg.get("digitando", True)), "id_usuario": c.id_usuario}, sala=sala, origem=c)
                    return
                if tipo == "read_receipt":
                    sala = str(msg.get("sala") or "")
                    app.tempo_real.emitir(c.canal, "read_receipt", {"sala": sala, "mensagem_id": msg.get("mensagem_id"), "id_usuario": c.id_usuario}, sala=sala, origem=c)
                    return
                if tipo in {"ack", "confirmar_ack"}:
                    id_mensagem = str(msg.get("id_mensagem") or msg.get("message_id") or "")
                    status_ack = str(msg.get("status") or "ack")
                    out_ack = app.tempo_real.confirmar_ack(c.canal, id_mensagem, c.id_conexao, status=status_ack)
                    self._emitir_evento_ws(c, {"ok": bool(out_ack.get("ok")), "evento": "ack_resultado", "dados": out_ack})
                    return
                if tipo in {"nack", "solicitar_reenvio"}:
                    id_mensagem = str(msg.get("id_mensagem") or msg.get("message_id") or "")
                    out_re = app.tempo_real.reenviar_pendentes(c.canal, id_mensagem=id_mensagem)
                    self._emitir_evento_ws(c, {"ok": True, "evento": "reenvio_resultado", "dados": out_re})
                    return
                if tipo == "broadcast_sala":
                    sala = str(msg.get("sala") or "")
                    evento = str(msg.get("evento") or "mensagem")
                    exigir_ack = bool(msg.get("exigir_ack", False))
                    out_pub = app.tempo_real.publicar_mensagem(c.canal, evento, msg.get("dados", {}), sala=sala, origem=c, exigir_ack=exigir_ack)
                    qtd = int(out_pub.get("destinos", 0))
                    self._emitir_evento_ws(c, {"ok": True, "evento": "broadcast_sala", "destinos": qtd, "sala": sala})
                    return
                if tipo == "broadcast_usuario":
                    alvo = str(msg.get("id_usuario") or msg.get("user_id") or "")
                    evento = str(msg.get("evento") or "mensagem")
                    exigir_ack = bool(msg.get("exigir_ack", False))
                    out_pub = app.tempo_real.publicar_mensagem(c.canal, evento, msg.get("dados", {}), id_usuario=alvo, origem=c, exigir_ack=exigir_ack)
                    qtd = int(out_pub.get("destinos", 0))
                    self._emitir_evento_ws(c, {"ok": True, "evento": "broadcast_usuario", "destinos": qtd, "id_usuario": alvo})
                    return
                if tipo == "broadcast_conexao":
                    alvo = str(msg.get("id_conexao") or msg.get("connection_id") or "")
                    evento = str(msg.get("evento") or "mensagem")
                    exigir_ack = bool(msg.get("exigir_ack", False))
                    out_pub = app.tempo_real.publicar_mensagem(c.canal, evento, msg.get("dados", {}), id_conexao=alvo, origem=c, exigir_ack=exigir_ack)
                    qtd = int(out_pub.get("destinos", 0))
                    self._emitir_evento_ws(c, {"ok": True, "evento": "broadcast_conexao", "destinos": qtd, "id_conexao": alvo})
                    return

                h = rota_info.get("handler")
                if h is None:
                    self._emitir_evento_ws(c, {"ok": False, "erro": {"codigo": "EVENTO_INVALIDO", "mensagem": "Evento de tempo real não suportado."}})
                    return
                req = self._ctx_conexao(c, {"evento": "mensagem", "mensagem": msg, "payload": msg, "tipo": tipo})
                res = invoke(h, [req])
                if isinstance(res, dict):
                    destino = str(res.get("destino") or "conexao")
                    evento = str(res.get("evento") or tipo or "mensagem")
                    dados = res.get("dados", {})
                    exigir_ack = bool(res.get("exigir_ack", False))
                    if destino == "sala":
                        app.tempo_real.publicar_mensagem(c.canal, evento, dados, sala=str(res.get("sala", "")), origem=c, exigir_ack=exigir_ack)
                    elif destino == "usuario":
                        app.tempo_real.publicar_mensagem(c.canal, evento, dados, id_usuario=str(res.get("id_usuario") or res.get("user_id") or ""), origem=c, exigir_ack=exigir_ack)
                    elif destino == "canal":
                        app.tempo_real.publicar_mensagem(c.canal, evento, dados, origem=c, exigir_ack=exigir_ack)
                    elif destino == "conexao":
                        app.tempo_real.publicar_mensagem(c.canal, evento, dados, id_conexao=str(res.get("id_conexao") or c.id_conexao), origem=c, exigir_ack=exigir_ack)
                    elif destino == "ignorar":
                        return
                    else:
                        app.tempo_real.publicar_mensagem(c.canal, evento, dados, id_conexao=c.id_conexao, origem=c, exigir_ack=exigir_ack)
                observability_runtime.registrar_runtime_metrica(
                    "tempo_real",
                    "mensagem_processada",
                    labels={"canal": c.canal, "tipo": tipo or "custom"},
                )

            def _processar_fallback_tempo_real(
                self,
                path: str,
                query: dict[str, object],
                headers_map: dict[str, str],
            ) -> bool:
                return processar_fallback_tempo_real_http(
                    self,
                    app=app,
                    path=path,
                    query=query,
                    headers_map=headers_map,
                    invocar_sync=invoke,
                    processar_mensagem=self._processar_mensagem_tempo_real,
                )

            def _handle_websocket_upgrade(
                self,
                path: str,
                query: dict[str, object],
                headers_map: dict[str, str],
            ) -> bool:
                return processar_upgrade_websocket_tempo_real(
                    self,
                    app=app,
                    path=path,
                    query=query,
                    headers_map=headers_map,
                    invocar_sync=invoke,
                    processar_mensagem=self._processar_mensagem_tempo_real,
                )

            def _apply_rate_limit(
                self,
                method: str,
                path: str,
                request_id: str | None,
                req: dict[str, object],
                *,
                incluir_local: bool = True,
                incluir_distribuido: bool = True,
            ) -> tuple[bool, tuple[int, dict[str, object]] | None]:
                ip = str(req.get("ip", "unknown"))
                if incluir_local:
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
                if incluir_distribuido and not bool(req.get("_rl_distribuido_aplicado", False)):
                    id_usuario = str(req.get("id_usuario") or req.get("user_id") or "").strip()
                    for p in app.rate_limits_distribuidos:
                        if p.method not in {"*", method}:
                            continue
                        if p.path != "*" and p.path != path:
                            continue
                        chaves = list(p.chaves or ["rota", "ip"])
                        for tipo_chave in chaves:
                            tipo = str(tipo_chave).strip().lower()
                            if tipo == "rota":
                                valor_chave = f"rota:{method}:{path}"
                            elif tipo == "ip":
                                valor_chave = f"ip:{ip}:{method}:{path}"
                            elif tipo == "usuario":
                                if not id_usuario:
                                    continue
                                valor_chave = f"usuario:{id_usuario}:{method}:{path}"
                            else:
                                valor_chave = f"{tipo}:{method}:{path}:{ip}"
                            out_rl = security_runtime.rate_limit_distribuido_permitir(
                                valor_chave,
                                int(p.max_requisicoes),
                                float(p.janela_segundos),
                                grupo=p.grupo,
                                id_instancia=p.id_instancia,
                                backend=p.backend,
                                redis_url=p.redis_url,
                                chave_prefixo=p.chave_prefixo,
                            )
                            if not bool(out_rl.get("permitido", False)):
                                return False, (
                                    429,
                                    {
                                        "ok": False,
                                        "erro": {
                                            "codigo": "RATE_LIMIT_EXCEDIDO",
                                            "mensagem": "Limite de requisições excedido.",
                                            "detalhes": {
                                                "metodo": method,
                                                "caminho": path,
                                                "chave": valor_chave,
                                                "escopo": tipo,
                                                "tentativas": int(out_rl.get("tentativas", 0)),
                                                "maximo": int(out_rl.get("maximo", int(p.max_requisicoes))),
                                                "degradado": bool(out_rl.get("degradado", False)),
                                            },
                                        },
                                    },
                                )
                    req["_rl_distribuido_aplicado"] = True
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

            @staticmethod
            def _campos_validacao_por_faltando(missing: list[str]) -> list[dict[str, object]]:
                return [
                    _erro_campo_validacao(
                        "CAMPO_OBRIGATORIO_AUSENTE",
                        campo,
                        "Campo obrigatório ausente.",
                        {},
                    )
                    for campo in missing
                ]

            @staticmethod
            def _aplicar_contrato_entrada(
                req: dict[str, object],
                options: dict[str, object],
            ) -> dict[str, list[str]]:
                contrato_entrada = dict(options.get("contrato_entrada", {}))
                permitidos = dict(contrato_entrada.get("campos_permitidos", {}))
                removidos: dict[str, list[str]] = {}
                for secao in ["corpo", "consulta", "parametros", "formulario"]:
                    campos_permitidos = permitidos.get(secao)
                    dados = req.get(secao)
                    if not isinstance(campos_permitidos, list) or not isinstance(dados, dict):
                        continue
                    keep = {str(x) for x in campos_permitidos}
                    drop = [str(k) for k in dados.keys() if str(k) not in keep]
                    if drop:
                        for k in drop:
                            dados.pop(k, None)
                        removidos[secao] = drop
                return removidos

            @staticmethod
            def _aplicar_dto_requisicao(
                req: dict[str, object],
                options: dict[str, object],
            ) -> list[dict[str, object]]:
                dto_req = options.get("dto_requisicao")
                if not isinstance(dto_req, dict) or not dto_req:
                    return []
                erros: list[dict[str, object]] = []
                for secao in ["corpo", "consulta", "parametros", "formulario"]:
                    if secao in dto_req:
                        spec = dto_req.get(secao)
                    elif secao == "corpo":
                        spec = dto_req
                    else:
                        continue
                    dados_atual = req.get(secao, {})
                    resultado = dto_validar_payload({secao: spec}, dados_atual, contexto=secao)
                    if bool(resultado.get("ok", False)):
                        req[secao] = resultado.get("dados", {})
                    else:
                        erros.extend(list(resultado.get("erros", [])))
                return erros

            @staticmethod
            def _registrar_auditoria_admin(
                req: dict[str, object],
                options: dict[str, object],
                *,
                resultado: str,
                detalhes: dict[str, object] | None = None,
            ) -> None:
                if not bool(app.auditoria_admin_ativa):
                    return
                auditoria_cfg_raw = options.get("auditoria_admin")
                if auditoria_cfg_raw is False:
                    return
                auditoria_cfg = dict(auditoria_cfg_raw or {}) if isinstance(auditoria_cfg_raw, dict) else {}
                parametros = req.get("parametros", {})
                if not isinstance(parametros, dict):
                    parametros = {}
                ator = str(req.get("id_usuario") or req.get("user_id") or "anonimo")
                acao = str(
                    auditoria_cfg.get("acao")
                    or f"{str(req.get('metodo', 'GET')).upper()} {str(req.get('caminho', ''))}"
                )
                alvo = str(
                    auditoria_cfg.get("alvo")
                    or req.get("alvo_admin")
                    or parametros.get("id", "")
                )
                security_runtime.auditoria_seguranca_registrar(
                    ator=ator,
                    acao=acao,
                    alvo=alvo,
                    resultado=str(resultado),
                    id_requisicao=str(req.get("id_requisicao") or req.get("request_id") or ""),
                    id_traco=str(req.get("id_traco") or req.get("trace_id") or ""),
                    origem=str(req.get("ip") or ""),
                    detalhes=dict(detalhes or {}),
                )

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
                if bool(options.get("jwt_validar_revogacao", True)) and security_runtime.token_esta_bloqueado(token):
                    return False, (
                        401,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "TOKEN_REVOGADO",
                                "mensagem": "Token revogado.",
                                "detalhes": None,
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
                if bool(options.get("jwt_exigir_sessao_ativa", False)):
                    id_sessao = claims.get("sid") or claims.get("id_sessao")
                    if not isinstance(id_sessao, str) or not security_runtime.sessao_ativa(id_sessao):
                        return False, (
                            401,
                            {
                                "ok": False,
                                "erro": {
                                    "codigo": "SESSAO_INVALIDA",
                                    "mensagem": "Sessão inválida ou revogada.",
                                    "detalhes": None,
                                },
                            },
                        )
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
            def _resolver_contrato_resposta(
                req: dict[str, object],
                options: dict[str, object],
            ) -> tuple[dict[str, object], str | None, str | None]:
                contrato_raw = options.get("contrato_resposta")
                contrato = dict(contrato_raw or {}) if isinstance(contrato_raw, dict) else {}
                if not contrato:
                    return {}, None, None

                versoes = dict(contrato.get("versoes", {}))
                if not versoes:
                    return contrato, None, None

                cabecalhos = req.get("cabecalhos", {})
                consulta = req.get("consulta", {})
                if not isinstance(cabecalhos, dict):
                    cabecalhos = {}
                if not isinstance(consulta, dict):
                    consulta = {}
                versao_solicitada = str(
                    cabecalhos.get("x-contrato-versao")
                    or cabecalhos.get("x-api-contract-version")
                    or consulta.get("versao_contrato")
                    or consulta.get("contract_version")
                    or contrato.get("versao_padrao")
                    or ""
                ).strip()
                if not versao_solicitada:
                    versao_solicitada = sorted(str(k) for k in versoes.keys())[0]
                if versao_solicitada in versoes:
                    return dict(versoes.get(versao_solicitada, {})), versao_solicitada, versao_solicitada

                retro = dict(contrato.get("retrocompativel", {}))
                versao_aplicada = str(retro.get(versao_solicitada, "")).strip()
                if versao_aplicada and versao_aplicada in versoes:
                    return dict(versoes.get(versao_aplicada, {})), versao_solicitada, versao_aplicada
                return {"__erro__": "VERSAO_CONTRATO_INVALIDA"}, versao_solicitada, None

            @staticmethod
            def _validate_response_contract(value: object, contrato: dict[str, object]) -> tuple[bool, str | None]:
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

                origem_req = str(headers_in.get("origin", "") or "")
                cors_ok, _ = self._resolver_cors(origem_req)
                if origem_req and not cors_ok:
                    self._send_json(
                        403,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "CORS_ORIGEM_NAO_PERMITIDA",
                                "mensagem": "Origem não permitida pelo CORS do ambiente.",
                                "detalhes": {"origem": origem_req, "ambiente": str(app.ambiente)},
                            },
                        },
                        {"X-Request-Id": str(request_id)},
                    )
                    return
                if self.command == "OPTIONS":
                    self._send_bytes(204, b"", "text/plain; charset=utf-8", {})
                    return

                parsed_url = urlparse(self.path)
                path = parsed_url.path
                self._trama_rota = path
                query = {k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(parsed_url.query).items()}
                headers_map = {k.lower(): v for k, v in self.headers.items()}

                if self.command in {"GET", "POST"} and self._processar_fallback_tempo_real(path, query, headers_map):
                    return

                if self.command == "GET" and self._handle_websocket_upgrade(path, query, headers_map):
                    return

                if app.observabilidade_ativa and path == app.observabilidade_path:
                    resumo = observability_runtime.observabilidade_resumo(app.alertas_config)
                    self._send_json(200, resumo, {})
                    return
                if app.observabilidade_ativa and path == app.alertas_path:
                    alertas = observability_runtime.alertas_avaliar(app.alertas_config)
                    self._send_json(200, {"ok": True, "alertas": alertas}, {})
                    return
                if app.observabilidade_ativa and path == app.metricas_path:
                    prom = observability_runtime.exportar_prometheus().encode("utf-8")
                    self._send_bytes(200, prom, "text/plain; version=0.0.4; charset=utf-8", {})
                    return
                if app.observabilidade_ativa and path == app.otlp_path:
                    otlp = observability_runtime.exportar_otel_json()
                    self._send_json(200, {"ok": True, "otlp": otlp}, {})
                    return

                if app.health_enabled and path in {app.health_path, app.readiness_path, app.liveness_path}:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    tipo = "health"
                    if path == app.readiness_path:
                        tipo = "readiness"
                    if path == app.liveness_path:
                        tipo = "liveness"
                    http_status, payload_saude = runtime_ref._status_saude(tipo)
                    self._send_json(http_status, payload_saude, headers)
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

                ok_rl, rl_err = self._apply_rate_limit(
                    self.command,
                    path,
                    request_id,
                    req,
                    incluir_local=True,
                    incluir_distribuido=False,
                )
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
                cache_cfg = dict(options.get("cache_resposta", {})) if isinstance(options.get("cache_resposta"), dict) else {}
                miss = self._validate_schema(req, schema)
                if miss:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(
                        422,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "VALIDACAO_FALHOU",
                                "mensagem": "Falha de validação da requisição.",
                                "detalhes": {
                                    "faltando": miss,
                                    "campos": self._campos_validacao_por_faltando(miss),
                                },
                            },
                        },
                        headers,
                    )
                    return

                removidos = self._aplicar_contrato_entrada(req, options)
                if removidos:
                    req["campos_removidos"] = removidos

                dto_erros = self._aplicar_dto_requisicao(req, options)
                req["body"] = req["corpo"]
                req["query"] = req["consulta"]
                req["params"] = req["parametros"]
                req["form"] = req["formulario"]
                if dto_erros:
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(
                        422,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "VALIDACAO_FALHOU",
                                "mensagem": "Falha de validação da requisição.",
                                "detalhes": {
                                    "campos": dto_erros,
                                },
                            },
                        },
                        headers,
                    )
                    return

                auth_ok, auth_err = self._apply_auth(req, options)
                if not auth_ok and auth_err is not None:
                    self._registrar_auditoria_admin(
                        req,
                        options,
                        resultado="negado",
                        detalhes={"codigo": dict(auth_err[1].get("erro", {})).get("codigo", "")},
                    )
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(auth_err[0], auth_err[1], headers)
                    return
                ok_rl_dist, rl_dist_err = self._apply_rate_limit(
                    self.command,
                    path,
                    request_id,
                    req,
                    incluir_local=False,
                    incluir_distribuido=True,
                )
                if not ok_rl_dist and rl_dist_err is not None:
                    self._registrar_auditoria_admin(
                        req,
                        options,
                        resultado="negado",
                        detalhes={"codigo": dict(rl_dist_err[1].get("erro", {})).get("codigo", "")},
                    )
                    headers = {"X-Request-Id": request_id} if request_id else None
                    self._send_json(rl_dist_err[0], rl_dist_err[1], headers)
                    return

                contrato_escolhido, versao_contrato_solicitada, versao_contrato_aplicada = self._resolver_contrato_resposta(req, options)
                if contrato_escolhido.get("__erro__") == "VERSAO_CONTRATO_INVALIDA":
                    headers = {"X-Request-Id": request_id} if request_id else {}
                    if versao_contrato_solicitada:
                        headers["X-Contrato-Versao-Solicitada"] = versao_contrato_solicitada
                    self._send_json(
                        400,
                        {
                            "ok": False,
                            "erro": {
                                "codigo": "CONTRATO_VERSAO_INVALIDA",
                                "mensagem": "Versão de contrato não suportada.",
                                "detalhes": {
                                    "versao_solicitada": versao_contrato_solicitada,
                                    "versoes_disponiveis": sorted(
                                        str(k)
                                        for k in dict(dict(options.get("contrato_resposta", {})).get("versoes", {})).keys()
                                    ),
                                },
                            },
                        },
                        headers,
                    )
                    return

                cache_chave: str | None = None
                cache_ns = str(cache_cfg.get("namespace", "http"))
                cache_ttl = cache_cfg.get("ttl_segundos")
                cache_instancia = cache_cfg.get("instancia")
                if self.command == "GET" and cache_cfg:
                    chave_personalizada = cache_cfg.get("chave")
                    if isinstance(chave_personalizada, str) and chave_personalizada:
                        cache_chave = chave_personalizada
                    else:
                        query_str = parsed_url.query or ""
                        cache_chave = f"{self.command}:{path}?{query_str}"
                    try:
                        cache_hit = cache_runtime.cache_distribuido_obter(
                            cache_chave,
                            None,
                            namespace=cache_ns,
                            instancia=cache_instancia,  # type: ignore[arg-type]
                        )
                    except Exception:
                        cache_hit = None
                    if isinstance(cache_hit, dict) and "body_b64" in cache_hit and "status" in cache_hit:
                        try:
                            cached_headers = dict(cache_hit.get("cabecalhos", {}))
                            if request_id:
                                cached_headers["X-Request-Id"] = request_id
                            self._send_bytes(
                                int(cache_hit.get("status", 200)),
                                base64.b64decode(str(cache_hit.get("body_b64", ""))),
                                str(cache_hit.get("content_type", "application/json; charset=utf-8")),
                                {str(k): str(v) for k, v in cached_headers.items()},
                            )
                            return
                        except Exception:
                            pass

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
                    ok_contract, contract_err = self._validate_response_contract(result, contrato_escolhido)
                    if not ok_contract:
                        headers = {"X-Request-Id": request_id} if request_id else {}
                        if versao_contrato_solicitada:
                            headers["X-Contrato-Versao-Solicitada"] = versao_contrato_solicitada
                        if versao_contrato_aplicada:
                            headers["X-Contrato-Versao-Aplicada"] = versao_contrato_aplicada
                        self._send_json(
                            500,
                            {
                                "ok": False,
                                "erro": {
                                    "codigo": "CONTRATO_INVALIDO",
                                    "mensagem": "Resposta do handler violou contrato da API.",
                                    "detalhes": {
                                        "erro": contract_err,
                                        "versao_solicitada": versao_contrato_solicitada,
                                        "versao_aplicada": versao_contrato_aplicada,
                                    },
                                },
                            },
                            headers,
                        )
                        self._registrar_auditoria_admin(
                            req,
                            options,
                            resultado="falha",
                            detalhes={"codigo": "CONTRATO_INVALIDO"},
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
                    if versao_contrato_solicitada:
                        final_headers["X-Contrato-Versao-Solicitada"] = versao_contrato_solicitada
                    if versao_contrato_aplicada:
                        final_headers["X-Contrato-Versao-Aplicada"] = versao_contrato_aplicada

                    if cache_chave is not None:
                        try:
                            payload_cache = {
                                "status": int(resp_map.get("status", status)),
                                "cabecalhos": {str(k): str(v) for k, v in final_headers.items()},
                                "content_type": ctype,
                                "body_b64": base64.b64encode(body_bytes).decode("ascii"),
                            }
                            cache_runtime.cache_distribuido_definir(
                                cache_chave,
                                payload_cache,
                                ttl_segundos=None if cache_ttl is None else float(cache_ttl),
                                namespace=cache_ns,
                                instancia=cache_instancia,  # type: ignore[arg-type]
                            )
                        except Exception:
                            pass

                    self._registrar_auditoria_admin(
                        req,
                        options,
                        resultado="sucesso" if int(resp_map.get("status", status)) < 400 else "falha",
                        detalhes={"status": int(resp_map.get("status", status))},
                    )
                    self._send_bytes(int(resp_map.get("status", status)), body_bytes, ctype, final_headers)
                except Exception as exc:  # noqa: BLE001
                    if app.error_handler is not None:
                        err_payload = invoke(app.error_handler, [req, {"mensagem": str(exc)}])
                        s, h, b, c = self._as_response(err_payload)
                        if request_id:
                            h["X-Request-Id"] = request_id
                        self._registrar_auditoria_admin(
                            req,
                            options,
                            resultado="erro",
                            detalhes={"erro": str(exc)},
                        )
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
                    self._registrar_auditoria_admin(
                        req,
                        options,
                        resultado="erro",
                        detalhes={"erro": str(exc)},
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
        self._estado_drenando = True
        self._estado_pronto = False
        self.engine_http.parar()
        self._estado_inicializado = False

    def _stop_legacy_httpserver(self) -> None:
        timeout = float(getattr(self.app, "shutdown_gracioso_segundos", 5.0) or 5.0)
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=max(timeout, 0.1))
