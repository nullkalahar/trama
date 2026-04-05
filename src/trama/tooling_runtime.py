"""Tooling de backend maduro (v2.0.6+) e operacao SRE (v2.0.7+)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any
from urllib import error, request

from . import observability_runtime
from .web_runtime import WebApp


@dataclass
class _MetodoRota:
    metodo: str
    caminho: str
    op_id: str


def _normalizar_path_openapi(path: str) -> str:
    chunks = [c for c in str(path).split("/") if c]
    out: list[str] = []
    for ch in chunks:
        if ch.startswith(":") and len(ch) > 1:
            out.append("{" + ch[1:] + "}")
        else:
            out.append(ch)
    return "/" + "/".join(out)


def _op_id(method: str, path: str) -> str:
    p = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    p = p.replace(":", "")
    return f"{method.lower()}_{p or 'raiz'}"


def _parametros_de_path(path: str) -> list[dict[str, object]]:
    params: list[dict[str, object]] = []
    for token in path.split("/"):
        if token.startswith("{") and token.endswith("}") and len(token) > 2:
            nome = token[1:-1]
            params.append(
                {
                    "name": nome,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            )
    return params


def _schema_para_openapi(spec: object) -> dict[str, object]:
    if isinstance(spec, str):
        tipo = str(spec).lower()
        if tipo in {"texto", "string"}:
            return {"type": "string"}
        if tipo in {"inteiro", "int"}:
            return {"type": "integer"}
        if tipo in {"numero", "float", "decimal"}:
            return {"type": "number"}
        if tipo in {"logico", "bool", "booleano"}:
            return {"type": "boolean"}
        if tipo in {"lista", "array"}:
            return {"type": "array", "items": {"type": "string"}}
        if tipo in {"objeto", "mapa", "dict"}:
            return {"type": "object"}
        return {"type": "string"}
    if not isinstance(spec, dict):
        return {"type": "object"}
    s = dict(spec)
    tipo = str(s.get("tipo", "objeto")).lower()
    if tipo in {"texto", "string"}:
        out = {"type": "string"}
        if "tamanho_min" in s:
            out["minLength"] = int(s.get("tamanho_min", 0))
        if "tamanho_max" in s:
            out["maxLength"] = int(s.get("tamanho_max", 0))
        if "enum" in s and isinstance(s["enum"], list):
            out["enum"] = list(s["enum"])
        return out
    if tipo in {"inteiro", "int"}:
        out = {"type": "integer"}
        if "minimo" in s:
            out["minimum"] = int(s.get("minimo", 0))
        if "maximo" in s:
            out["maximum"] = int(s.get("maximo", 0))
        return out
    if tipo in {"numero", "float", "decimal"}:
        out = {"type": "number"}
        if "minimo" in s:
            out["minimum"] = float(s.get("minimo", 0))
        if "maximo" in s:
            out["maximum"] = float(s.get("maximo", 0))
        return out
    if tipo in {"logico", "bool", "booleano"}:
        return {"type": "boolean"}
    if tipo in {"lista", "array"}:
        return {"type": "array", "items": _schema_para_openapi(s.get("itens", {"tipo": "texto"}))}
    if tipo in {"objeto", "mapa", "dict"}:
        campos = s.get("campos") if isinstance(s.get("campos"), dict) else s.get("propriedades")
        props = {str(k): _schema_para_openapi(v) for k, v in dict(campos or {}).items()}
        required = [
            str(k)
            for k, v in dict(campos or {}).items()
            if isinstance(v, dict) and bool(dict(v).get("obrigatorio", False))
        ]
        out: dict[str, object] = {"type": "object", "properties": props}
        if required:
            out["required"] = required
        return out
    return {"type": "object"}


def gerar_openapi_web_app(
    app: WebApp,
    titulo: str = "API Trama",
    versao: str = "1.0.0",
    servidor_base: str | None = None,
) -> dict[str, object]:
    paths: dict[str, object] = {}
    for r in app.routes:
        if str(r.kind) != "handler":
            continue
        path = _normalizar_path_openapi(str(r.path))
        method = str(r.method).lower()
        if path not in paths:
            paths[path] = {}
        data = dict(r.data or {})
        schema = dict(data.get("schema", {})) if isinstance(data.get("schema"), dict) else {}
        options = dict(data.get("options", {})) if isinstance(data.get("options"), dict) else {}
        dto_req = options.get("dto_requisicao") if isinstance(options.get("dto_requisicao"), dict) else None
        contrato_resp = options.get("contrato_resposta") if isinstance(options.get("contrato_resposta"), dict) else {}

        req_body_schema: dict[str, object] | None = None
        if dto_req and isinstance(dto_req, dict):
            if "corpo" in dto_req and isinstance(dto_req.get("corpo"), dict):
                req_body_schema = _schema_para_openapi(dto_req.get("corpo"))
            else:
                req_body_schema = _schema_para_openapi(dto_req)
        elif schema.get("corpo_obrigatorio"):
            req_body_schema = {
                "type": "object",
                "required": [str(x) for x in list(schema.get("corpo_obrigatorio", []))],
                "properties": {str(x): {"type": "string"} for x in list(schema.get("corpo_obrigatorio", []))},
            }

        responses: dict[str, object] = {
            "200": {
                "description": "Resposta de sucesso",
                "content": {"application/json": {"schema": {"type": "object"}}},
            },
            "422": {
                "description": "Falha de validação",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "ok": {"type": "boolean"},
                                "erro": {
                                    "type": "object",
                                    "properties": {
                                        "codigo": {"type": "string"},
                                        "mensagem": {"type": "string"},
                                        "detalhes": {"type": "object"},
                                    },
                                },
                            },
                        }
                    }
                },
            },
            "401": {"description": "Não autenticado"},
            "403": {"description": "Sem permissão"},
            "429": {"description": "Limite de taxa excedido"},
        }

        if contrato_resp:
            if isinstance(contrato_resp.get("versoes"), dict):
                versoes = dict(contrato_resp.get("versoes", {}))
                if versoes:
                    vpad = str(contrato_resp.get("versao_padrao") or sorted(versoes.keys())[0])
                    escolhido = dict(versoes.get(vpad, {}))
                    campos = [str(x) for x in list(escolhido.get("campos_obrigatorios", []))]
                    if campos:
                        responses["200"] = {
                            "description": "Resposta de sucesso contratada",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": campos,
                                        "properties": {c: {"type": "object"} for c in campos},
                                    }
                                }
                            },
                        }

        operation: dict[str, object] = {
            "operationId": _op_id(method, path),
            "summary": f"{method.upper()} {path}",
            "parameters": _parametros_de_path(path),
            "responses": responses,
        }

        if req_body_schema is not None and method in {"post", "put", "patch"}:
            operation["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": req_body_schema}},
            }

        cast_paths = dict(paths[path])
        cast_paths[method] = operation
        paths[path] = cast_paths

    servers = [{"url": servidor_base}] if servidor_base else []
    return {
        "openapi": "3.0.3",
        "info": {
            "title": str(titulo),
            "version": str(versao),
            "description": "Especificação OpenAPI gerada automaticamente pela Trama.",
        },
        "servers": servers,
        "paths": paths,
        "components": {
            "schemas": {
                "ErroPadrao": {
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "erro": {
                            "type": "object",
                            "properties": {
                                "codigo": {"type": "string"},
                                "mensagem": {"type": "string"},
                                "detalhes": {"type": "object"},
                            },
                        },
                    },
                }
            }
        },
    }


def salvar_openapi(spec: dict[str, object], caminho_saida: str) -> dict[str, object]:
    out = Path(caminho_saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "arquivo": str(out.resolve())}


def _sdk_python(spec: dict[str, object], nome_cliente: str = "ClienteApiTrama") -> str:
    paths = dict(spec.get("paths", {}))
    methods: list[_MetodoRota] = []
    for path, ops in paths.items():
        if not isinstance(ops, dict):
            continue
        for m in ["get", "post", "put", "patch", "delete"]:
            if m in ops and isinstance(ops[m], dict):
                op_id = str(dict(ops[m]).get("operationId") or _op_id(m, str(path)))
                methods.append(_MetodoRota(m.upper(), str(path), op_id))

    lines = [
        '"""SDK cliente Python gerado pela Trama a partir de OpenAPI."""',
        "",
        "from __future__ import annotations",
        "",
        "import json",
        "from urllib import request",
        "",
        f"class {nome_cliente}:",
        "    def __init__(self, base_url: str, timeout_segundos: float = 10.0) -> None:",
        "        self.base_url = base_url.rstrip('/')",
        "        self.timeout_segundos = float(timeout_segundos)",
        "",
        "    def _req(self, metodo: str, caminho: str, payload: dict | None = None, headers: dict | None = None) -> dict:",
        "        h = {'Content-Type': 'application/json; charset=utf-8'}",
        "        if isinstance(headers, dict):",
        "            h.update(headers)",
        "        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')",
        "        req = request.Request(self.base_url + caminho, method=metodo, data=data, headers=h)",
        "        with request.urlopen(req, timeout=self.timeout_segundos) as resp:",
        "            txt = resp.read().decode('utf-8', errors='replace')",
        "            return json.loads(txt) if txt else {}",
        "",
    ]
    for mt in methods:
        nome_fn = mt.op_id
        lines.extend(
            [
                f"    def {nome_fn}(self, payload: dict | None = None, headers: dict | None = None) -> dict:",
                f"        return self._req('{mt.metodo}', '{mt.caminho}', payload=payload, headers=headers)",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _sdk_typescript(spec: dict[str, object], nome_cliente: str = "ClienteApiTrama") -> str:
    paths = dict(spec.get("paths", {}))
    methods: list[_MetodoRota] = []
    for path, ops in paths.items():
        if not isinstance(ops, dict):
            continue
        for m in ["get", "post", "put", "patch", "delete"]:
            if m in ops and isinstance(ops[m], dict):
                op_id = str(dict(ops[m]).get("operationId") or _op_id(m, str(path)))
                methods.append(_MetodoRota(m.upper(), str(path), op_id))
    lines = [
        "// SDK cliente TypeScript gerado pela Trama a partir de OpenAPI.",
        "",
        f"export class {nome_cliente} {{",
        "  constructor(private baseUrl: string, private timeoutMs: number = 10000) {}",
        "",
        "  private async req(metodo: string, caminho: string, payload?: Record<string, unknown>, headers?: Record<string, string>): Promise<any> {",
        "    const controller = new AbortController();",
        "    const t = setTimeout(() => controller.abort(), this.timeoutMs);",
        "    try {",
        "      const resp = await fetch(this.baseUrl.replace(/\\/$/, '') + caminho, {",
        "        method: metodo,",
        "        headers: { 'Content-Type': 'application/json; charset=utf-8', ...(headers || {}) },",
        "        body: payload ? JSON.stringify(payload) : undefined,",
        "        signal: controller.signal,",
        "      });",
        "      const txt = await resp.text();",
        "      return txt ? JSON.parse(txt) : {};",
        "    } finally {",
        "      clearTimeout(t);",
        "    }",
        "  }",
        "",
    ]
    for mt in methods:
        lines.extend(
            [
                f"  async {mt.op_id}(payload?: Record<string, unknown>, headers?: Record<string, string>): Promise<any> {{",
                f"    return this.req('{mt.metodo}', '{mt.caminho}', payload, headers);",
                "  }",
                "",
            ]
        )
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def gerar_sdk_cliente(
    spec: dict[str, object],
    destino_arquivo: str,
    linguagem: str = "python",
    nome_cliente: str = "ClienteApiTrama",
) -> dict[str, object]:
    lang = str(linguagem).strip().lower()
    if lang not in {"python", "typescript", "ts"}:
        raise ValueError("linguagem de SDK inválida. Use python/typescript.")
    conteudo = _sdk_python(spec, nome_cliente=nome_cliente) if lang == "python" else _sdk_typescript(spec, nome_cliente=nome_cliente)
    out = Path(destino_arquivo)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(conteudo, encoding="utf-8")
    return {"ok": True, "arquivo": str(out.resolve()), "linguagem": ("typescript" if lang in {"typescript", "ts"} else "python")}


def dashboards_operacionais_prontos() -> dict[str, object]:
    return {
        "ok": True,
        "dashboards": [
            {
                "id": "api",
                "titulo": "API HTTP",
                "metricas": ["http.requisicoes_total", "http.erros_total", "http.latencia_ms"],
            },
            {
                "id": "db",
                "titulo": "Banco de Dados",
                "metricas": ["db.operacoes_total", "db.erros_total", "db.latencia_ms"],
            },
            {
                "id": "tempo_real",
                "titulo": "Tempo Real",
                "metricas": ["runtime.eventos_total"],
                "filtro_recomendado": {"componente": "tempo_real"},
            },
            {
                "id": "jobs",
                "titulo": "Filas e Jobs",
                "metricas": ["runtime.eventos_total"],
                "filtro_recomendado": {"componente": "jobs"},
            },
        ],
    }


def runbooks_incidentes_prontos() -> dict[str, object]:
    return {
        "ok": True,
        "runbooks": [
            {
                "codigo": "runbook_api_erro_alto",
                "quando_usar": "Taxa de erro HTTP acima do limite.",
                "passos": [
                    "Validar /saude, /pronto e /vivo.",
                    "Checar alertas e latencia p95 no /alertas e /observabilidade.",
                    "Correlacionar id_requisicao/id_traco em logs estruturados.",
                    "Acionar rollback da ultima mudanca se regressao confirmada.",
                ],
            },
            {
                "codigo": "runbook_latencia_alta",
                "quando_usar": "Latencia p95 elevada com erro baixo.",
                "passos": [
                    "Inspecionar gargalo em DB (db.latencia_ms) e runtime.http.",
                    "Verificar saturacao de fila/jobs e backlog realtime.",
                    "Aplicar mitigacao (cache, reducao de carga, escalonamento).",
                ],
            },
            {
                "codigo": "runbook_backplane_indisponivel",
                "quando_usar": "Falha de backend distribuido (cache/realtime/rate-limit).",
                "passos": [
                    "Confirmar degradacao controlada e ausencia de bypass inseguro.",
                    "Isolar incidente de dependencia externa e restaurar conectividade.",
                    "Revisar eventos de falha em runtime.eventos_total.",
                ],
            },
        ],
    }


def smoke_checks_http(
    base_url: str,
    timeout_segundos: float = 2.0,
    caminhos: list[str] | None = None,
) -> dict[str, object]:
    base = str(base_url).rstrip("/")
    rotas = list(caminhos or ["/saude", "/pronto", "/vivo", "/observabilidade", "/alertas"])
    resultados: list[dict[str, object]] = []
    inicio = time.perf_counter()
    for caminho in rotas:
        url = base + str(caminho)
        req = request.Request(url=url, method="GET")
        try:
            with request.urlopen(req, timeout=float(timeout_segundos)) as resp:
                status = int(resp.getcode() or 0)
                ok = 200 <= status < 400
                resultados.append({"caminho": caminho, "ok": ok, "status": status})
        except error.HTTPError as exc:
            resultados.append({"caminho": caminho, "ok": False, "status": int(exc.code), "erro": "http_error"})
        except Exception as exc:  # noqa: BLE001
            resultados.append({"caminho": caminho, "ok": False, "status": 0, "erro": str(exc)})
    total_ms = (time.perf_counter() - inicio) * 1000.0
    observability_runtime.registrar_runtime_metrica(
        "operacao",
        "smoke_check_executado",
        labels={"ok": str(all(bool(r.get("ok")) for r in resultados)).lower()},
    )
    return {
        "ok": all(bool(r.get("ok")) for r in resultados),
        "base_url": base,
        "duracao_ms": total_ms,
        "resultados": resultados,
    }
