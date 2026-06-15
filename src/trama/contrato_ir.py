"""IR formal de contrato HTTP da Trama (v2.1.27+)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .web_runtime import dto_gerar_exemplos


@dataclass(frozen=True)
class MetodoIr:
    metodo: str
    caminho: str
    operation_id: str


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


def schema_para_ir(spec: object) -> dict[str, object]:
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
        return {"type": "array", "items": schema_para_ir(s.get("itens", {"tipo": "texto"}))}
    if tipo in {"objeto", "mapa", "dict"}:
        campos = s.get("campos") if isinstance(s.get("campos"), dict) else s.get("propriedades")
        props = {str(k): schema_para_ir(v) for k, v in dict(campos or {}).items()}
        required = [
            str(k)
            for k, v in dict(campos or {}).items()
            if isinstance(v, dict) and bool(dict(v).get("obrigatorio", False))
        ]
        out: dict[str, object] = {
            "type": "object",
            "properties": props,
            "additionalProperties": bool(s.get("permitir_campos_extras", True)),
        }
        if required:
            out["required"] = required
        return out
    return {"type": "object"}


def _erros_padrao() -> list[dict[str, object]]:
    return [
        {"codigo": "NAO_AUTENTICADO", "status": 401},
        {"codigo": "SEM_PERMISSAO", "status": 403},
        {"codigo": "LIMITE_TAXA_EXCEDIDO", "status": 429},
        {"codigo": "DTO_INVALIDO", "status": 422},
        {"codigo": "VERSAO_CONTRATO_INVALIDA", "status": 400},
    ]


def _extrair_exemplos_dto(dto_requisicao: dict[str, object]) -> dict[str, object]:
    exemplos: dict[str, object] = {}
    for contexto in ["corpo", "consulta", "parametros", "formulario"]:
        if contexto in dto_requisicao:
            exemplos[contexto] = dto_gerar_exemplos(dto_requisicao, contexto=contexto)
        elif contexto == "corpo" and dto_requisicao:
            exemplos[contexto] = dto_gerar_exemplos(dto_requisicao, contexto=contexto)
    return exemplos


def gerar_ir_web_app(
    app: object,
    titulo: str = "API Trama",
    versao: str = "1.0.0",
    servidor_base: str | None = None,
) -> dict[str, object]:
    rotas: list[dict[str, object]] = []
    routes = list(getattr(app, "routes", []))
    api_versions = sorted(str(v) for v in set(getattr(app, "api_versions", set()) or set()))
    for rota in routes:
        if str(getattr(rota, "kind", "")) != "handler":
            continue
        method = str(getattr(rota, "method", "GET")).upper()
        path_raw = str(getattr(rota, "path", "/"))
        path = _normalizar_path_openapi(path_raw)
        data = dict(getattr(rota, "data", {}) or {})
        options = dict(data.get("options", {})) if isinstance(data.get("options"), dict) else {}
        dto_req = dict(options.get("dto_requisicao", {})) if isinstance(options.get("dto_requisicao"), dict) else {}
        contrato_resp = dict(options.get("contrato_resposta", {})) if isinstance(options.get("contrato_resposta"), dict) else {}
        schema = dict(data.get("schema", {})) if isinstance(data.get("schema"), dict) else {}
        versionamento = {
            "api_versions": api_versions,
            "contrato_resposta": dict(contrato_resp),
            "versao_padrao": str(contrato_resp.get("versao_padrao", "")) if contrato_resp else "",
            "retrocompativel": dict(contrato_resp.get("retrocompativel", {})) if contrato_resp else {},
        }
        dto_schemas: dict[str, object] = {}
        for contexto in ["corpo", "consulta", "parametros", "formulario"]:
            if contexto in dto_req:
                dto_schemas[contexto] = schema_para_ir(dto_req[contexto])
            elif contexto == "corpo" and dto_req:
                dto_schemas[contexto] = schema_para_ir(dto_req)
        rotas.append(
            {
                "metodo": method,
                "caminho": path,
                "caminho_original": path_raw,
                "operation_id": _op_id(method, path),
                "resumo": f"{method} {path}",
                "parametros_path": _parametros_de_path(path),
                "schema_legado": schema,
                "dto_requisicao": dto_req,
                "dto_schemas": dto_schemas,
                "contrato_resposta": contrato_resp,
                "autenticacao": {
                    "jwt_ativo": bool(str(options.get("jwt_segredo", "") or "")),
                    "jwt_exigir_sessao_ativa": bool(options.get("jwt_exigir_sessao_ativa", False)),
                    "rbac_permissoes": [str(x) for x in list(options.get("rbac_permissoes", []))],
                },
                "versionamento": versionamento,
                "erros_padrao": _erros_padrao(),
                "exemplos": _extrair_exemplos_dto(dto_req) if dto_req else {},
            }
        )
    return {
        "ir_contrato": "trama_http_v1",
        "titulo": str(titulo),
        "versao": str(versao),
        "servidores": ([{"url": str(servidor_base)}] if servidor_base else []),
        "rotas": rotas,
        "componentes": {
            "erro_padrao": {
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
        },
    }


def gerar_ir_de_documento(
    contrato: dict[str, object],
    titulo: str = "API Trama",
    versao: str = "1.0.0",
    servidor_base: str | None = None,
) -> dict[str, object]:
    doc = dict(contrato or {})
    if doc.get("ir_contrato") == "trama_http_v1":
        return doc
    if "paths" in doc:
        rotas: list[dict[str, object]] = []
        for caminho, operacoes in dict(doc.get("paths", {})).items():
            if not isinstance(operacoes, dict):
                continue
            for metodo, op in operacoes.items():
                if not isinstance(op, dict):
                    continue
                rotas.append(
                    {
                        "metodo": str(metodo).upper(),
                        "caminho": str(caminho),
                        "caminho_original": str(caminho),
                        "operation_id": str(op.get("operationId") or _op_id(str(metodo), str(caminho))),
                        "resumo": str(op.get("summary") or f"{str(metodo).upper()} {str(caminho)}"),
                        "parametros_path": list(op.get("parameters", [])),
                        "dto_requisicao": {},
                        "dto_schemas": {
                            "corpo": dict(dict(op.get("requestBody", {})).get("content", {}).get("application/json", {}).get("schema", {}))
                        }
                        if isinstance(dict(op.get("requestBody", {})).get("content", {}), dict)
                        else {},
                        "contrato_resposta": {"respostas": dict(op.get("responses", {}))},
                        "autenticacao": {},
                        "versionamento": {"api_versions": [], "contrato_resposta": {}, "versao_padrao": "", "retrocompativel": {}},
                        "erros_padrao": _erros_padrao(),
                        "exemplos": {},
                    }
                )
        return {
            "ir_contrato": "trama_http_v1",
            "titulo": str(dict(doc.get("info", {})).get("title", titulo)),
            "versao": str(dict(doc.get("info", {})).get("version", versao)),
            "servidores": list(doc.get("servers", [])) or ([{"url": str(servidor_base)}] if servidor_base else []),
            "rotas": rotas,
            "componentes": dict(doc.get("components", {})),
        }
    return {
        "ir_contrato": "trama_http_v1",
        "titulo": str(titulo),
        "versao": str(versao),
        "servidores": ([{"url": str(servidor_base)}] if servidor_base else []),
        "rotas": [],
        "componentes": {},
    }


def gerar_openapi_de_ir(ir: dict[str, object]) -> dict[str, object]:
    doc = dict(ir or {})
    if doc.get("ir_contrato") != "trama_http_v1":
        raise ValueError("IR de contrato invalido. Use 'trama_http_v1'.")
    paths: dict[str, object] = {}
    for rota in list(doc.get("rotas", [])):
        if not isinstance(rota, dict):
            continue
        path = str(rota.get("caminho", "/"))
        method = str(rota.get("metodo", "GET")).lower()
        dto_schemas = dict(rota.get("dto_schemas", {}))
        contrato_resposta = dict(rota.get("contrato_resposta", {}))
        operation: dict[str, object] = {
            "operationId": str(rota.get("operation_id") or _op_id(method, path)),
            "summary": str(rota.get("resumo") or f"{method.upper()} {path}"),
            "parameters": list(rota.get("parametros_path", [])),
            "responses": {
                "200": {
                    "description": "Resposta de sucesso",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                },
                "422": {
                    "description": "Falha de validacao",
                    "content": {"application/json": {"schema": dict(doc.get("componentes", {})).get("erro_padrao", {"type": "object"})}},
                },
                "401": {"description": "Nao autenticado"},
                "403": {"description": "Sem permissao"},
                "429": {"description": "Limite de taxa excedido"},
            },
        }
        if method in {"post", "put", "patch"} and isinstance(dto_schemas.get("corpo"), dict):
            operation["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": dict(dto_schemas.get("corpo", {}))}},
            }
        if isinstance(contrato_resposta.get("versoes"), dict):
            versoes = dict(contrato_resposta.get("versoes", {}))
            if versoes:
                vpad = str(contrato_resposta.get("versao_padrao") or sorted(versoes.keys())[0])
                escolhido = dict(versoes.get(vpad, {}))
                campos = [str(x) for x in list(escolhido.get("campos_obrigatorios", []))]
                if campos:
                    operation["responses"]["200"] = {
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
        if path not in paths:
            paths[path] = {}
        cast = dict(paths[path])
        cast[method] = operation
        paths[path] = cast
    return {
        "openapi": "3.0.3",
        "info": {
            "title": str(doc.get("titulo", "API Trama")),
            "version": str(doc.get("versao", "1.0.0")),
            "description": "Especificacao OpenAPI gerada a partir do IR formal da Trama.",
        },
        "servers": list(doc.get("servidores", [])),
        "paths": paths,
        "components": {
            "schemas": {
                "ErroPadrao": dict(dict(doc.get("componentes", {})).get("erro_padrao", {"type": "object"})),
            }
        },
    }


def salvar_ir(ir: dict[str, object], caminho_saida: str) -> dict[str, object]:
    out = Path(caminho_saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ir, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "arquivo": str(out.resolve()), "ir_contrato": str(ir.get("ir_contrato", ""))}


def _schema_required(spec: dict[str, object] | None) -> set[str]:
    if not isinstance(spec, dict):
        return set()
    return {str(x) for x in list(spec.get("required", []))}


def _schema_properties(spec: dict[str, object] | None) -> dict[str, dict[str, object]]:
    if not isinstance(spec, dict):
        return {}
    props = dict(spec.get("properties", {}))
    return {str(k): dict(v) for k, v in props.items() if isinstance(v, dict)}


def _rotas_por_chave(ir: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    out: dict[tuple[str, str], dict[str, object]] = {}
    for rota in list(dict(ir or {}).get("rotas", [])):
        if not isinstance(rota, dict):
            continue
        chave = (str(rota.get("metodo", "GET")).upper(), str(rota.get("caminho", "/")))
        out[chave] = rota
    return out


def comparar_breaking_changes(antes: dict[str, object], depois: dict[str, object]) -> dict[str, object]:
    ir_antes = gerar_ir_de_documento(antes)
    ir_depois = gerar_ir_de_documento(depois)
    rotas_antes = _rotas_por_chave(ir_antes)
    rotas_depois = _rotas_por_chave(ir_depois)
    breaking: list[dict[str, object]] = []
    avisos: list[dict[str, object]] = []

    for chave, rota_antes in rotas_antes.items():
        if chave not in rotas_depois:
            breaking.append(
                {
                    "tipo": "rota_removida",
                    "metodo": chave[0],
                    "caminho": chave[1],
                    "mensagem": "Rota removida na versão nova.",
                }
            )
            continue
        rota_depois = rotas_depois[chave]
        corpo_antes = dict(dict(rota_antes.get("dto_schemas", {})).get("corpo", {}))
        corpo_depois = dict(dict(rota_depois.get("dto_schemas", {})).get("corpo", {}))
        req_antes = _schema_required(corpo_antes)
        req_depois = _schema_required(corpo_depois)
        for campo in sorted(req_depois - req_antes):
            breaking.append(
                {
                    "tipo": "campo_requisicao_obrigatorio_adicionado",
                    "metodo": chave[0],
                    "caminho": chave[1],
                    "campo": campo,
                    "mensagem": "Novo campo obrigatório em requisição.",
                }
            )

        props_antes = _schema_properties(corpo_antes)
        props_depois = _schema_properties(corpo_depois)
        for campo in sorted(set(props_antes) & set(props_depois)):
            tipo_antes = str(props_antes[campo].get("type", "object"))
            tipo_depois = str(props_depois[campo].get("type", "object"))
            if tipo_antes != tipo_depois:
                breaking.append(
                    {
                        "tipo": "tipo_requisicao_alterado",
                        "metodo": chave[0],
                        "caminho": chave[1],
                        "campo": campo,
                        "antes": tipo_antes,
                        "depois": tipo_depois,
                        "mensagem": "Tipo de campo de requisição alterado.",
                    }
                )

        contrato_antes = dict(rota_antes.get("contrato_resposta", {}))
        contrato_depois = dict(rota_depois.get("contrato_resposta", {}))
        versoes_antes = dict(contrato_antes.get("versoes", {}))
        versoes_depois = dict(contrato_depois.get("versoes", {}))
        for versao, antigo in versoes_antes.items():
            if versao not in versoes_depois:
                breaking.append(
                    {
                        "tipo": "versao_resposta_removida",
                        "metodo": chave[0],
                        "caminho": chave[1],
                        "versao": versao,
                        "mensagem": "Versão de contrato de resposta removida.",
                    }
                )
                continue
            campos_antes = {str(x) for x in list(dict(antigo).get("campos_obrigatorios", []))}
            campos_depois = {str(x) for x in list(dict(versoes_depois[versao]).get("campos_obrigatorios", []))}
            for campo in sorted(campos_antes - campos_depois):
                breaking.append(
                    {
                        "tipo": "campo_resposta_obrigatorio_removido",
                        "metodo": chave[0],
                        "caminho": chave[1],
                        "versao": versao,
                        "campo": campo,
                        "mensagem": "Campo obrigatório de resposta removido.",
                    }
                )
            for campo in sorted(campos_depois - campos_antes):
                avisos.append(
                    {
                        "tipo": "campo_resposta_obrigatorio_adicionado",
                        "metodo": chave[0],
                        "caminho": chave[1],
                        "versao": versao,
                        "campo": campo,
                        "mensagem": "Campo obrigatório de resposta adicionado; validar consumidores.",
                    }
                )

    for chave in sorted(set(rotas_depois) - set(rotas_antes)):
        avisos.append(
            {
                "tipo": "rota_nova",
                "metodo": chave[0],
                "caminho": chave[1],
                "mensagem": "Nova rota adicionada.",
            }
        )

    return {
        "ok": not breaking,
        "breaking_changes": breaking,
        "avisos": avisos,
        "antes": {"titulo": ir_antes.get("titulo"), "versao": ir_antes.get("versao")},
        "depois": {"titulo": ir_depois.get("titulo"), "versao": ir_depois.get("versao")},
    }
