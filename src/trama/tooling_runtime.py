"""Tooling de backend maduro (v2.0.6+) e operacao SRE (v2.0.7+)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from urllib import error, request

from . import observability_runtime
from . import contrato_ir
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
    ir = gerar_ir_web_app(app, titulo=titulo, versao=versao, servidor_base=servidor_base)
    return gerar_openapi_de_ir(ir)


def gerar_ir_web_app(
    app: WebApp,
    titulo: str = "API Trama",
    versao: str = "1.0.0",
    servidor_base: str | None = None,
) -> dict[str, object]:
    return contrato_ir.gerar_ir_web_app(app, titulo=titulo, versao=versao, servidor_base=servidor_base)


def gerar_ir_contrato(
    contrato: dict[str, object],
    titulo: str = "API Trama",
    versao: str = "1.0.0",
    servidor_base: str | None = None,
) -> dict[str, object]:
    return contrato_ir.gerar_ir_de_documento(contrato, titulo=titulo, versao=versao, servidor_base=servidor_base)


def gerar_openapi_de_ir(ir: dict[str, object]) -> dict[str, object]:
    return contrato_ir.gerar_openapi_de_ir(ir)


def salvar_ir_contrato(ir: dict[str, object], caminho_saida: str) -> dict[str, object]:
    return contrato_ir.salvar_ir(ir, caminho_saida)


def salvar_openapi(spec: dict[str, object], caminho_saida: str) -> dict[str, object]:
    out = Path(caminho_saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "arquivo": str(out.resolve())}


def _metodos_ir(doc: dict[str, object]) -> list[_MetodoRota]:
    ir = contrato_ir.gerar_ir_de_documento(doc)
    methods: list[_MetodoRota] = []
    for rota in list(ir.get("rotas", [])):
        if not isinstance(rota, dict):
            continue
        methods.append(
            _MetodoRota(
                str(rota.get("metodo", "GET")).upper(),
                str(rota.get("caminho", "/")),
                str(rota.get("operation_id") or _op_id(str(rota.get("metodo", "GET")), str(rota.get("caminho", "/")))),
            )
        )
    return methods


def _sdk_python(doc: dict[str, object], nome_cliente: str = "ClienteApiTrama") -> str:
    methods = _metodos_ir(doc)
    if dict(doc).get("ir_contrato") == "trama_http_v1":
        ir = dict(doc)
    else:
        ir = contrato_ir.gerar_ir_de_documento(doc)

    helper_paths = [
        '"""SDK cliente Python gerado pela Trama a partir do IR formal de contrato."""',
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
        "    def _montar_caminho(self, caminho: str, parametros: dict | None = None) -> str:",
        "        out = str(caminho)",
        "        for chave, valor in dict(parametros or {}).items():",
        "            out = out.replace('{' + str(chave) + '}', str(valor))",
        "        return out",
        "",
        "    def _req(self, metodo: str, caminho: str, payload: dict | None = None, headers: dict | None = None, parametros: dict | None = None) -> dict:",
        "        h = {'Content-Type': 'application/json; charset=utf-8'}",
        "        if isinstance(headers, dict):",
        "            h.update(headers)",
        "        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')",
        "        req = request.Request(self.base_url + self._montar_caminho(caminho, parametros), method=metodo, data=data, headers=h)",
        "        with request.urlopen(req, timeout=self.timeout_segundos) as resp:",
        "            txt = resp.read().decode('utf-8', errors='replace')",
        "            return json.loads(txt) if txt else {}",
        "",
        "    def contrato(self) -> dict:",
        f"        return {repr(ir)}",
        "",
    ]
    lines = helper_paths
    for mt in methods:
        nome_fn = mt.op_id
        lines.extend(
            [
                f"    def {nome_fn}(self, payload: dict | None = None, headers: dict | None = None, parametros: dict | None = None) -> dict:",
                f"        return self._req('{mt.metodo}', '{mt.caminho}', payload=payload, headers=headers, parametros=parametros)",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _sdk_typescript(doc: dict[str, object], nome_cliente: str = "ClienteApiTrama") -> str:
    methods = _metodos_ir(doc)
    if dict(doc).get("ir_contrato") == "trama_http_v1":
        ir = dict(doc)
    else:
        ir = contrato_ir.gerar_ir_de_documento(doc)

    lines = [
        "// SDK cliente TypeScript gerado pela Trama a partir do IR formal de contrato.",
        "",
        f"export class {nome_cliente} {{",
        "  constructor(private baseUrl: string, private timeoutMs: number = 10000) {}",
        "",
        "  private montarCaminho(caminho: string, parametros?: Record<string, unknown>): string {",
        "    let out = String(caminho);",
        "    for (const [chave, valor] of Object.entries(parametros || {})) {",
        "      out = out.replace(`{${chave}}`, String(valor));",
        "    }",
        "    return out;",
        "  }",
        "",
        "  private async req(metodo: string, caminho: string, payload?: Record<string, unknown>, headers?: Record<string, string>, parametros?: Record<string, unknown>): Promise<any> {",
        "    const controller = new AbortController();",
        "    const t = setTimeout(() => controller.abort(), this.timeoutMs);",
        "    try {",
        "      const resp = await fetch(this.baseUrl.replace(/\\/$/, '') + this.montarCaminho(caminho, parametros), {",
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
        "  contrato(): any {",
        f"    return {json.dumps(ir, ensure_ascii=False, indent=4)};",
        "  }",
        "",
    ]
    for mt in methods:
        lines.extend(
            [
                f"  async {mt.op_id}(payload?: Record<string, unknown>, headers?: Record<string, string>, parametros?: Record<string, unknown>): Promise<any> {{",
                f"    return this.req('{mt.metodo}', '{mt.caminho}', payload, headers, parametros);",
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
    ir = contrato_ir.gerar_ir_de_documento(spec)
    return {
        "ok": True,
        "arquivo": str(out.resolve()),
        "linguagem": ("typescript" if lang in {"typescript", "ts"} else "python"),
        "ir_contrato": str(ir.get("ir_contrato", "")),
    }


def verificar_breaking_changes_contrato(antes: dict[str, object], depois: dict[str, object]) -> dict[str, object]:
    return contrato_ir.comparar_breaking_changes(antes, depois)


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
