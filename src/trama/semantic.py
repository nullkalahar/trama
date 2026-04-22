"""Análise semântica da linguagem trama."""

from __future__ import annotations

from dataclasses import dataclass, field

from .ast_nodes import (
    AssignStmt,
    AwaitExpr,
    BinaryExpr,
    BreakStmt,
    CallExpr,
    ContinueStmt,
    DictExpr,
    Expr,
    ExprStmt,
    ExportStmt,
    ForStmt,
    FunctionDecl,
    Identifier,
    IfStmt,
    ImportStmt,
    IndexExpr,
    ListExpr,
    Literal,
    Program,
    ReturnStmt,
    Stmt,
    ThrowStmt,
    TryStmt,
    TypeRef,
    UnaryExpr,
    WhileStmt,
)


class SemanticError(ValueError):
    """Erro semântico com diagnóstico estável e auditável."""

    def __init__(
        self,
        *,
        codigo: str,
        mensagem: str,
        arquivo: str | None = None,
        linha: int | None = None,
        coluna: int | None = None,
        sugestao: str | None = None,
        detalhes: dict[str, object] | None = None,
    ) -> None:
        self.codigo = codigo
        self.mensagem = mensagem
        self.arquivo = arquivo
        self.linha = linha
        self.coluna = coluna
        self.sugestao = sugestao
        self.detalhes = detalhes or {}

        partes = [f"{codigo}: {mensagem}"]
        if arquivo is not None:
            partes.append(f"arquivo={arquivo}")
        if linha is not None:
            partes.append(f"linha={linha}")
        if coluna is not None:
            partes.append(f"coluna={coluna}")
        if sugestao:
            partes.append(f"sugestao={sugestao}")
        super().__init__(" | ".join(partes))


_BUILTIN_ARITY: dict[str, int | None] = {
    "exibir": None,
    "log": 2,
    "log_info": 1,
    "log_erro": 1,
    "json_parse": 1,
    "json_parse_seguro": 1,
    "json_stringify": 1,
    "json_stringify_pretty": 1,
    "criar_tarefa": 1,
    "cancelar_tarefa": 1,
    "dormir": 1,
    "ler_texto_async": 1,
    "escrever_texto_async": 2,
    "com_timeout": 2,
    "ler_texto": 1,
    "escrever_texto": 2,
    "arquivo_existe": 1,
    "listar_diretorio": 1,
    "tamanho": 1,
    "lista_adicionar": 2,
    "mapa_obter": None,
    "mapa_definir": 3,
    "mapa_chaves": 1,
    "trama_compilar_fonte": 1,
    "trama_compilar_arquivo": 1,
    "trama_compilar_para_arquivo": 2,
    "compilar_trama_fonte": 1,
    "compilar_trama_arquivo": 1,
    "compilar_trama_para_arquivo": 2,
    "http_get": None,
    "http_post": None,
    "http_obter": None,
    "http_postar": None,
    "env_obter": None,
    "env_todos": None,
    "config_carregar": None,
    "config_carregar_ambiente": None,
    "config_validar": None,
    "segredo_obter": None,
    "segredo_ler": None,
    "segredo_mascarar": None,
    "cache_definir": None,
    "cache_obter": None,
    "cache_existe": None,
    "cache_remover": None,
    "cache_invalidar_padrao": None,
    "cache_invalida_padrao": None,
    "cache_limpar": None,
    "cache_aquecer": None,
    "cache_stats": None,
    "cache_distribuido_criar": None,
    "cache_distribuido_configurar_backplane": None,
    "cache_distribuido_sincronizar": None,
    "cache_distribuido_definir": None,
    "cache_distribuido_obter": None,
    "cache_distribuido_invalidar_chave": None,
    "cache_distribuido_invalidar_padrao": None,
    "cache_distribuido_obter_ou_carregar": None,
    "cache_distribuido_stats": None,
    "cache_distribuido_limpar": None,
    "cache_dist_criar": None,
    "cache_dist_sincronizar": None,
    "cache_dist_obter": None,
    "cache_dist_definir": None,
    "cache_dist_invalidar_chave": None,
    "cache_dist_invalidar_padrao": None,
    "cache_dist_obter_ou_carregar": None,
    "cache_dist_stats": None,
    "cache_dist_limpar": None,
    "resiliencia_executar": None,
    "circuito_status": 1,
    "circuito_resetar": None,
    "armazenamento_criar_local": 1,
    "armazenamento_criar_s3": None,
    "armazenamento_local_criar": 1,
    "armazenamento_s3_criar": None,
    "armazenamento_salvar": None,
    "armazenamento_ler": 2,
    "armazenamento_remover": 2,
    "armazenamento_listar": None,
    "armazenamento_url": None,
    "midia_ler_arquivo": 1,
    "midia_salvar_arquivo": 2,
    "midia_comprimir_gzip": None,
    "midia_descomprimir_gzip": 1,
    "midia_gzip_comprimir": None,
    "midia_gzip_descomprimir": 1,
    "midia_sha256": 1,
    "midia_redimensionar_imagem": None,
    "midia_converter_imagem": None,
    "midia_pipeline": None,
    "agora_iso": 0,
    "timestamp": 0,
    "web_criar_app": 0,
    "web_adicionar_rota_json": None,
    "web_adicionar_rota_echo_json": None,
    "web_usar_middleware": 2,
    "web_configurar_cors": None,
    "web_configurar_engine_http": None,
    "web_engine_configurar": None,
    "web_configurar_seguranca_http": None,
    "web_configurar_hardening": None,
    "web_security_configure": None,
    "web_ativar_healthcheck": None,
    "web_servir_estaticos": 3,
    "web_rota": None,
    "web_rota_contrato": None,
    "web_rota_dto": None,
    "web_middleware": None,
    "web_tratador_erro": 2,
    "web_rate_limit": None,
    "web_limite_taxa": None,
    "web_rate_limit_distribuido": None,
    "web_limite_taxa_distribuido": None,
    "web_rate_limit_dist": None,
    "web_api_versionar": None,
    "web_api_versao": None,
    "web_rota_com_contrato": None,
    "web_rota_com_dto": None,
    "web_saude_paths": None,
    "web_ativar_observabilidade": None,
    "web_observabilidade_ativar": None,
    "web_gerar_openapi": None,
    "web_exportar_openapi": None,
    "web_openapi_gerar": None,
    "web_openapi_exportar": None,
    "web_gerar_sdk": None,
    "web_sdk_gerar": None,
    "web_tempo_real_rota": None,
    "web_tempo_real_ativar_fallback": None,
    "web_tempo_real_definir_limites": None,
    "web_tempo_real_configurar_distribuicao": None,
    "web_tempo_real_sincronizar_distribuicao": None,
    "web_tempo_real_configurar_backplane": None,
    "web_tempo_real_emitir_sala": None,
    "web_tempo_real_emitir_usuario": None,
    "web_tempo_real_emitir_conexao": None,
    "web_tempo_real_status": None,
    "web_tempo_real_publicar": None,
    "web_tempo_real_confirmar_ack": None,
    "web_tempo_real_reenviar_pendentes": None,
    "web_socket_rota": None,
    "web_websocket_rota": None,
    "web_realtime_rota": None,
    "web_realtime_ativar_fallback": None,
    "web_realtime_definir_limites": None,
    "web_realtime_configurar_distribuicao": None,
    "web_realtime_sincronizar_distribuicao": None,
    "web_realtime_configurar_backplane": None,
    "web_realtime_emitir_sala": None,
    "web_realtime_emitir_usuario": None,
    "web_realtime_emitir_conexao": None,
    "web_realtime_status": None,
    "web_realtime_publicar": None,
    "web_realtime_confirmar_ack": None,
    "web_realtime_reenviar_pendentes": None,
    "web_iniciar": None,
    "web_parar": 1,
    "dto_validar": None,
    "dto_gerar_exemplos": None,
    "comunidade_criar": None,
    "comunidade_obter": 1,
    "comunidade_listar": 0,
    "canal_criar": None,
    "cargo_criar": None,
    "membro_entrar": 2,
    "membro_sair": 2,
    "membro_atribuir_cargo": 3,
    "comunidade_permissao_tem": None,
    "moderacao_acao": None,
    "moderacao_listar": 1,
    "admin_auditoria_registrar": None,
    "admin_auditoria_listar": None,
    "campanha_criar": None,
    "campanha_agendar": 2,
    "campanha_executar": 2,
    "campanha_status": 1,
    "campanha_listar": 0,
    "sync_registrar_evento": None,
    "sync_consumir": None,
    "sync_cursor_atual": 1,
    "sync_resolver_conflito": None,
    "cache_offline_salvar": None,
    "cache_offline_obter": 2,
    "cache_offline_listar": 1,
    "community_create": None,
    "community_get": 1,
    "channel_create": None,
    "role_create": None,
    "member_join": 2,
    "member_leave": 2,
    "moderation_action": None,
    "moderation_list": 1,
    "campaign_create": None,
    "campaign_schedule": 2,
    "campaign_run": 2,
    "campaign_status": 1,
    "sync_register_event": None,
    "sync_consume": None,
    "sync_conflict_resolve": None,
    "pg_conectar": 1,
    "pg_fechar": 1,
    "pg_executar": None,
    "pg_consultar": None,
    "pg_transacao_iniciar": 1,
    "pg_transacao_commit": 1,
    "pg_transacao_rollback": 1,
    "pg_tx_executar": None,
    "pg_tx_consultar": None,
    "qb_select": None,
    "qb_where_eq": 3,
    "qb_order_by": None,
    "qb_limite": 2,
    "qb_sql": 1,
    "qb_consultar": 2,
    "orm_inserir": 3,
    "orm_atualizar": 4,
    "orm_buscar_por_id": 3,
    "orm_modelo": None,
    "orm_relacao_um_para_um": None,
    "orm_relacao_um_para_muitos": None,
    "orm_relacao_muitos_para_muitos": None,
    "orm_listar": None,
    "schema_constraint_unica": None,
    "schema_constraint_fk": None,
    "schema_constraint_check": None,
    "schema_definir_tabela": None,
    "schema_definir": 1,
    "db_capacidades": 1,
    "schema_inspecionar": 1,
    "schema_diff": 2,
    "schema_preview_plano": 1,
    "schema_aplicar_diff": None,
    "migracao_aplicar": 3,
    "seed_aplicar": 3,
    "migracao_aplicar_versionada": None,
    "migracao_aplicar_versionada_v2": None,
    "migracao_status": 1,
    "migracao_reverter_ultima": 1,
    "migracao_validar_compatibilidade": 3,
    "migracao_trilha_listar": None,
    "seed_aplicar_ambiente": 4,
    "banco_conectar": 1,
    "banco_fechar": 1,
    "banco_executar": None,
    "banco_consultar": None,
    "transacao_iniciar": 1,
    "transacao_confirmar": 1,
    "transacao_cancelar": 1,
    "transacao_executar": None,
    "transacao_consultar": None,
    "consulta_selecionar": None,
    "consulta_onde_igual": 3,
    "consulta_ordenar_por": None,
    "consulta_limite": 2,
    "consulta_sql": 1,
    "consulta_executar": 2,
    "modelo_inserir": 3,
    "modelo_atualizar": 4,
    "modelo_buscar_por_id": 3,
    "modelo_listar": None,
    "semente_aplicar": 3,
    "semente_aplicar_ambiente": 4,
    "migracao_versionada_aplicar": None,
    "migracao_versionada_aplicar_v2": None,
    "migracao_listar": 1,
    "migracao_desfazer_ultima": 1,
    "migracao_compatibilidade_validar": 3,
    "migracao_trilha": None,
    "jwt_criar": None,
    "jwt_verificar": None,
    "senha_hash": None,
    "senha_verificar": 2,
    "rbac_criar": None,
    "rbac_atribuir": 3,
    "rbac_papeis_usuario": 2,
    "rbac_tem_papel": 3,
    "rbac_tem_permissao": 4,
    "auth_sessao_criar": None,
    "auth_sessao_obter": 1,
    "auth_sessao_ativa": 1,
    "auth_sessao_revogar": None,
    "auth_sessao_revogar_dispositivo": None,
    "auth_sessao_revogar_usuario": None,
    "auth_token_acesso_emitir": None,
    "auth_refresh_emitir": None,
    "auth_refresh_rotacionar": None,
    "auth_token_revogar": None,
    "auth_token_revogado": 1,
    "auth_token_limpar_denylist": 0,
    "seguranca_auditoria_registrar": None,
    "seguranca_auditoria_listar": None,
    "sessao_criar": None,
    "sessao_ativa": 1,
    "sessao_revogar": None,
    "token_revogar": None,
    "token_revogado": 1,
    "refresh_emitir": None,
    "refresh_rotacionar": None,
    "token_criar": None,
    "token_verificar": None,
    "senha_gerar_hash": None,
    "senha_validar": 2,
    "papel_criar_modelo": None,
    "papel_atribuir": 3,
    "papel_listar_usuario": 2,
    "papel_tem": 3,
    "permissao_tem": 4,
    "log_estruturado": None,
    "log_estruturado_json": None,
    "metrica_incrementar": None,
    "metrica_observar": None,
    "metricas_snapshot": 0,
    "metricas_reset": 0,
    "traco_iniciar": None,
    "traco_evento": None,
    "traco_finalizar": None,
    "tracos_snapshot": 0,
    "tracos_reset": 0,
    "observabilidade_resumo": None,
    "alertas_avaliar": None,
    "observabilidade_exportar_prometheus": 0,
    "observabilidade_exportar_otel_json": 0,
    "observabilidade_exportar_prom": 0,
    "observabilidade_exportar_otlp": 0,
    "observabilidade_dashboards_prontos": 0,
    "dashboards_operacionais_prontos": 0,
    "observabilidade_runbooks_prontos": 0,
    "runbooks_incidentes_prontos": 0,
    "operacao_smoke_checks": None,
    "metrica_inc": None,
    "traca_iniciar": None,
    "traca_evento": None,
    "traca_finalizar": None,
    "tracas_snapshot": 0,
    "tracas_reset": 0,
    "fila_criar": 1,
    "fila_enfileirar": None,
    "fila_processar": 1,
    "fila_status": 1,
    "webhook_enviar": None,
}


@dataclass(frozen=True)
class _FuncSig:
    aridade: int
    param_types: list[TypeRef | None]
    return_type: TypeRef | None


@dataclass
class _Context:
    in_function: bool = False
    in_async_function: bool = False
    loop_depth: int = 0
    in_top_level: bool = True
    current_function: str | None = None
    current_return_type: TypeRef | None = None
    variables: dict[str, TypeRef] = field(default_factory=dict)


def _ref(nome: str, args: list[TypeRef] | None = None) -> TypeRef:
    return TypeRef(nome=nome, args=args or [])


def _normalize_type(t: TypeRef | None) -> TypeRef:
    if t is None:
        return _ref("qualquer")
    return TypeRef(nome=t.nome.lower(), args=[_normalize_type(a) for a in t.args])


def _describe(t: TypeRef | None) -> str:
    tt = _normalize_type(t)
    if not tt.args:
        return tt.nome
    return f"{tt.nome}[{', '.join(_describe(a) for a in tt.args)}]"


def _is_numeric(t: TypeRef) -> bool:
    n = _normalize_type(t).nome
    return n in {"inteiro", "numero"}


def _type_compatible(actual: TypeRef | None, expected: TypeRef | None) -> bool:
    a = _normalize_type(actual)
    e = _normalize_type(expected)

    if e.nome in {"qualquer", "desconhecido"}:
        return True
    if a.nome in {"qualquer", "desconhecido"}:
        return True

    if e.nome == "uniao":
        return any(_type_compatible(a, opt) for opt in e.args)
    if a.nome == "uniao":
        return all(_type_compatible(opt, e) for opt in a.args)

    if e.nome == "numero" and a.nome == "inteiro":
        return True

    if a.nome != e.nome:
        return False

    if len(a.args) != len(e.args):
        return False

    return all(_type_compatible(aa, ee) for aa, ee in zip(a.args, e.args, strict=False))


def _err(
    codigo: str,
    mensagem: str,
    node: object | None = None,
    *,
    arquivo: str | None = None,
    sugestao: str | None = None,
    detalhes: dict[str, object] | None = None,
) -> SemanticError:
    linha = getattr(node, "linha", None) if node is not None else None
    coluna = getattr(node, "coluna", None) if node is not None else None
    if isinstance(linha, int) and linha <= 0:
        linha = None
    if isinstance(coluna, int) and coluna <= 0:
        coluna = None
    return SemanticError(
        codigo=codigo,
        mensagem=mensagem,
        arquivo=arquivo,
        linha=linha,
        coluna=coluna,
        sugestao=sugestao,
        detalhes=detalhes,
    )


def validate_semantics(program: Program, arquivo: str | None = None) -> None:
    signatures: dict[str, _FuncSig] = {}
    _collect_signatures(program.declarations, signatures)

    top_declared: set[str] = set(signatures.keys())
    seen_export_stmt = False
    exported_names: set[str] = set()

    # pré-passo de símbolos de topo para contrato de módulo
    for decl in program.declarations:
        if isinstance(decl, AssignStmt):
            top_declared.add(decl.name)
        elif isinstance(decl, ImportStmt):
            top_declared.add(decl.alias)

    ctx = _Context(in_function=False, in_async_function=False, loop_depth=0, in_top_level=True)
    for decl in program.declarations:
        _validate_stmt(decl, ctx, signatures, arquivo)
        if isinstance(decl, ExportStmt):
            seen_export_stmt = True
            for n in decl.names:
                if n in exported_names:
                    raise _err(
                        "SEM0403",
                        f"Nome exportado duplicado no contrato de módulo: '{n}'.",
                        decl,
                        arquivo=arquivo,
                        sugestao="Remova duplicatas em 'exporte'.",
                    )
                exported_names.add(n)

    if seen_export_stmt:
        missing = sorted(n for n in exported_names if n not in top_declared)
        if missing:
            raise SemanticError(
                codigo="SEM0404",
                mensagem=f"Contrato de módulo exporta nomes não declarados: {missing}.",
                arquivo=arquivo,
                sugestao="Declare os símbolos exportados antes do 'exporte'.",
                detalhes={"faltando": missing},
            )


def _collect_signatures(stmts: list[Stmt], signatures: dict[str, _FuncSig]) -> None:
    for stmt in stmts:
        if isinstance(stmt, FunctionDecl):
            param_types = [
                _normalize_type(stmt.param_types.get(p) if stmt.param_types else None)
                for p in stmt.params
            ]
            signatures[stmt.name] = _FuncSig(
                aridade=len(stmt.params),
                param_types=param_types,
                return_type=_normalize_type(stmt.return_type),
            )
            _collect_signatures(stmt.body, signatures)
        elif isinstance(stmt, IfStmt):
            _collect_signatures(stmt.then_branch, signatures)
            if stmt.else_branch:
                _collect_signatures(stmt.else_branch, signatures)
        elif isinstance(stmt, WhileStmt):
            _collect_signatures(stmt.body, signatures)
        elif isinstance(stmt, ForStmt):
            _collect_signatures(stmt.body, signatures)
        elif isinstance(stmt, TryStmt):
            _collect_signatures(stmt.try_branch, signatures)
            if stmt.catch_branch:
                _collect_signatures(stmt.catch_branch, signatures)
            if stmt.finally_branch:
                _collect_signatures(stmt.finally_branch, signatures)


def _validate_stmt(stmt: Stmt, ctx: _Context, signatures: dict[str, _FuncSig], arquivo: str | None) -> None:
    if isinstance(stmt, FunctionDecl):
        child_ctx = _Context(
            in_function=True,
            in_async_function=stmt.is_async,
            loop_depth=0,
            in_top_level=False,
            current_function=stmt.name,
            current_return_type=_normalize_type(stmt.return_type),
            variables=dict(ctx.variables),
        )
        if stmt.param_types:
            for pname, ptype in stmt.param_types.items():
                child_ctx.variables[pname] = _normalize_type(ptype)
        for inner in stmt.body:
            _validate_stmt(inner, child_ctx, signatures, arquivo)
        return

    if isinstance(stmt, ImportStmt):
        if not stmt.alias:
            raise _err(
                "SEM0401",
                "Alias de 'importe' não pode ser vazio.",
                stmt,
                arquivo=arquivo,
                sugestao="Use 'importe \"mod.trm\" como nome_modulo'.",
            )
        if stmt.names is not None:
            if len(stmt.names) == 0:
                raise _err(
                    "SEM0402",
                    "Lista de símbolos em 'expondo' não pode ser vazia.",
                    stmt,
                    arquivo=arquivo,
                    sugestao="Informe pelo menos um nome após 'expondo'.",
                )
            vistos: set[str] = set()
            for n in stmt.names:
                if n in vistos:
                    raise _err(
                        "SEM0405",
                        f"Símbolo duplicado em import explícito: '{n}'.",
                        stmt,
                        arquivo=arquivo,
                        sugestao="Remova símbolos repetidos em 'expondo'.",
                    )
                vistos.add(n)
        ctx.variables[stmt.alias] = _ref("mapa", [_ref("texto"), _ref("qualquer")])
        return

    if isinstance(stmt, ExportStmt):
        if not ctx.in_top_level:
            raise _err(
                "SEM0406",
                "'exporte' só pode ser usado no nível de módulo.",
                stmt,
                arquivo=arquivo,
                sugestao="Mova o contrato de exportação para o topo do arquivo.",
            )
        return

    if isinstance(stmt, IfStmt):
        _validate_expr(stmt.condition, signatures, ctx, arquivo)
        for inner in stmt.then_branch:
            _validate_stmt(inner, _clone_ctx(ctx), signatures, arquivo)
        if stmt.else_branch:
            for inner in stmt.else_branch:
                _validate_stmt(inner, _clone_ctx(ctx), signatures, arquivo)
        return

    if isinstance(stmt, WhileStmt):
        _validate_expr(stmt.condition, signatures, ctx, arquivo)
        child_ctx = _clone_ctx(ctx)
        child_ctx.loop_depth += 1
        child_ctx.in_top_level = False
        for inner in stmt.body:
            _validate_stmt(inner, child_ctx, signatures, arquivo)
        return

    if isinstance(stmt, ForStmt):
        iterable_t = _validate_expr(stmt.iterable, signatures, ctx, arquivo)
        elem_t = _iter_element_type(iterable_t)
        if elem_t is None:
            raise _err(
                "SEM0306",
                f"'para/em' exige iterável; recebido '{_describe(iterable_t)}'.",
                stmt,
                arquivo=arquivo,
                sugestao="Itere sobre lista, mapa ou tipo compatível.",
            )
        child_ctx = _clone_ctx(ctx)
        child_ctx.loop_depth += 1
        child_ctx.in_top_level = False
        child_ctx.variables[stmt.iterator] = elem_t
        for inner in stmt.body:
            _validate_stmt(inner, child_ctx, signatures, arquivo)
        return

    if isinstance(stmt, TryStmt):
        for inner in stmt.try_branch:
            _validate_stmt(inner, _clone_ctx(ctx), signatures, arquivo)
        if stmt.catch_branch is not None:
            catch_ctx = _clone_ctx(ctx)
            if stmt.catch_name:
                catch_ctx.variables[stmt.catch_name] = _ref("qualquer")
            for inner in stmt.catch_branch:
                _validate_stmt(inner, catch_ctx, signatures, arquivo)
        if stmt.finally_branch is not None:
            for inner in stmt.finally_branch:
                _validate_stmt(inner, _clone_ctx(ctx), signatures, arquivo)
        return

    if isinstance(stmt, ThrowStmt):
        _validate_expr(stmt.value, signatures, ctx, arquivo)
        return

    if isinstance(stmt, ReturnStmt):
        if not ctx.in_function:
            raise _err(
                "SEM0101",
                "'retorne' só pode ser usado dentro de função.",
                stmt,
                arquivo=arquivo,
                sugestao="Remova 'retorne' do topo ou envolva em função.",
            )
        if stmt.value is not None:
            ret_t = _validate_expr(stmt.value, signatures, ctx, arquivo)
            if ctx.current_return_type is not None and not _type_compatible(ret_t, ctx.current_return_type):
                raise _err(
                    "SEM0204",
                    f"Retorno incompatível em '{ctx.current_function}': esperado '{_describe(ctx.current_return_type)}', recebido '{_describe(ret_t)}'.",
                    stmt,
                    arquivo=arquivo,
                    sugestao="Ajuste o tipo retornado ou a anotação de retorno.",
                )
        return

    if isinstance(stmt, BreakStmt):
        if ctx.loop_depth <= 0:
            raise _err(
                "SEM0102",
                "'pare' só pode ser usado dentro de laço.",
                stmt,
                arquivo=arquivo,
                sugestao="Use 'pare' apenas em 'enquanto' ou 'para/em'.",
            )
        return

    if isinstance(stmt, ContinueStmt):
        if ctx.loop_depth <= 0:
            raise _err(
                "SEM0103",
                "'continue' só pode ser usado dentro de laço.",
                stmt,
                arquivo=arquivo,
                sugestao="Use 'continue' apenas em 'enquanto' ou 'para/em'.",
            )
        return

    if isinstance(stmt, AssignStmt):
        value_t = _validate_expr(stmt.value, signatures, ctx, arquivo)
        if stmt.annotation is not None:
            declared = _normalize_type(stmt.annotation)
            if not _type_compatible(value_t, declared):
                raise _err(
                    "SEM0201",
                    f"Atribuição incompatível para '{stmt.name}': esperado '{_describe(declared)}', recebido '{_describe(value_t)}'.",
                    stmt,
                    arquivo=arquivo,
                    sugestao="Corrija o valor atribuído ou ajuste a anotação.",
                )
            ctx.variables[stmt.name] = declared
        else:
            ctx.variables[stmt.name] = value_t
        return

    if isinstance(stmt, ExprStmt):
        _validate_expr(stmt.expression, signatures, ctx, arquivo)
        return

    raise _err(
        "SEM9999",
        f"Statement sem validação semântica: {type(stmt).__name__}.",
        stmt,
        arquivo=arquivo,
    )


def _iter_element_type(iterable_t: TypeRef | None) -> TypeRef | None:
    t = _normalize_type(iterable_t)
    if t.nome in {"qualquer", "desconhecido"}:
        return _ref("qualquer")
    if t.nome == "lista":
        if t.args:
            return t.args[0]
        return _ref("qualquer")
    return None


def _clone_ctx(ctx: _Context) -> _Context:
    return _Context(
        in_function=ctx.in_function,
        in_async_function=ctx.in_async_function,
        loop_depth=ctx.loop_depth,
        in_top_level=False,
        current_function=ctx.current_function,
        current_return_type=ctx.current_return_type,
        variables=dict(ctx.variables),
    )


def _validate_expr(expr: Expr, signatures: dict[str, _FuncSig], ctx: _Context, arquivo: str | None) -> TypeRef:
    if isinstance(expr, Literal):
        if expr.value is None:
            return _ref("nulo")
        if isinstance(expr.value, bool):
            return _ref("logico")
        if isinstance(expr.value, int):
            return _ref("inteiro")
        if isinstance(expr.value, float):
            return _ref("numero")
        if isinstance(expr.value, str):
            return _ref("texto")
        return _ref("qualquer")

    if isinstance(expr, Identifier):
        return ctx.variables.get(expr.name, _ref("qualquer"))

    if isinstance(expr, UnaryExpr):
        op_t = _validate_expr(expr.operand, signatures, ctx, arquivo)
        if expr.operator == "MENOS":
            if not _is_numeric(op_t):
                raise _err(
                    "SEM0301",
                    f"Operador unário '-' exige tipo numérico; recebido '{_describe(op_t)}'.",
                    expr,
                    arquivo=arquivo,
                    sugestao="Aplique '-' apenas a números.",
                )
            return op_t
        return _ref("qualquer")

    if isinstance(expr, AwaitExpr):
        if not ctx.in_async_function:
            raise _err(
                "SEM0104",
                "'aguarde' só pode ser usado dentro de função assíncrona.",
                expr,
                arquivo=arquivo,
                sugestao="Marque a função como 'assíncrona'.",
            )
        return _validate_expr(expr.expression, signatures, ctx, arquivo)

    if isinstance(expr, BinaryExpr):
        left_t = _validate_expr(expr.left, signatures, ctx, arquivo)
        right_t = _validate_expr(expr.right, signatures, ctx, arquivo)
        if expr.operator in {"MAIS", "MENOS", "ASTERISCO", "BARRA"}:
            left_n = _normalize_type(left_t)
            right_n = _normalize_type(right_t)

            # Mantém compatibilidade dinâmica em código sem anotação.
            if left_n.nome in {"qualquer", "desconhecido"} or right_n.nome in {"qualquer", "desconhecido"}:
                return _ref("qualquer")

            # Concatenação textual é permitida para '+'.
            if expr.operator == "MAIS" and left_n.nome == "texto" and right_n.nome == "texto":
                return _ref("texto")

            if not _is_numeric(left_t) or not _is_numeric(right_t):
                raise _err(
                    "SEM0302",
                    f"Operação aritmética exige números; recebido '{_describe(left_t)}' e '{_describe(right_t)}'.",
                    expr,
                    arquivo=arquivo,
                    sugestao="Converta os operandos para tipo numérico.",
                )
            if left_t.nome == "numero" or right_t.nome == "numero" or expr.operator == "BARRA":
                return _ref("numero")
            return _ref("inteiro")
        if expr.operator in {"IGUAL_IGUAL", "DIFERENTE", "MAIOR", "MAIOR_IGUAL", "MENOR", "MENOR_IGUAL"}:
            return _ref("logico")
        return _ref("qualquer")

    if isinstance(expr, ListExpr):
        if not expr.elements:
            return _ref("lista", [_ref("qualquer")])
        elem_types = [_validate_expr(e, signatures, ctx, arquivo) for e in expr.elements]
        head = elem_types[0]
        if all(_type_compatible(t, head) for t in elem_types[1:]):
            return _ref("lista", [head])
        return _ref("lista", [_ref("qualquer")])

    if isinstance(expr, DictExpr):
        if not expr.entries:
            return _ref("mapa", [_ref("qualquer"), _ref("qualquer")])
        key_types: list[TypeRef] = []
        val_types: list[TypeRef] = []
        for key, value in expr.entries:
            key_types.append(_validate_expr(key, signatures, ctx, arquivo))
            val_types.append(_validate_expr(value, signatures, ctx, arquivo))
        key_head = key_types[0]
        val_head = val_types[0]
        if not all(_type_compatible(t, key_head) for t in key_types[1:]):
            key_head = _ref("qualquer")
        if not all(_type_compatible(t, val_head) for t in val_types[1:]):
            val_head = _ref("qualquer")
        return _ref("mapa", [key_head, val_head])

    if isinstance(expr, IndexExpr):
        target_t = _validate_expr(expr.target, signatures, ctx, arquivo)
        _validate_expr(expr.index, signatures, ctx, arquivo)
        t = _normalize_type(target_t)
        if t.nome == "lista":
            return t.args[0] if t.args else _ref("qualquer")
        if t.nome == "mapa":
            return t.args[1] if len(t.args) >= 2 else _ref("qualquer")
        return _ref("qualquer")

    if isinstance(expr, CallExpr):
        callee_t = _validate_expr(expr.callee, signatures, ctx, arquivo)
        arg_types = [_validate_expr(arg, signatures, ctx, arquivo) for arg in expr.arguments]

        if isinstance(expr.callee, Identifier):
            name = expr.callee.name
            if name in signatures:
                sig = signatures[name]
                got = len(expr.arguments)
                if sig.aridade != got:
                    raise _err(
                        "SEM0105",
                        f"Função '{name}' esperava {sig.aridade} argumentos, recebeu {got}.",
                        expr,
                        arquivo=arquivo,
                        sugestao="Ajuste a quantidade de argumentos na chamada.",
                    )
                for idx, (arg_t, param_t) in enumerate(zip(arg_types, sig.param_types, strict=False), start=1):
                    if param_t is not None and not _type_compatible(arg_t, param_t):
                        raise _err(
                            "SEM0203",
                            f"Argumento {idx} incompatível em '{name}': esperado '{_describe(param_t)}', recebido '{_describe(arg_t)}'.",
                            expr,
                            arquivo=arquivo,
                            sugestao="Ajuste o tipo do argumento ou a anotação do parâmetro.",
                        )
                return _normalize_type(sig.return_type)

            if name in _BUILTIN_ARITY:
                expected_builtin = _BUILTIN_ARITY[name]
                if expected_builtin is not None and expected_builtin != len(expr.arguments):
                    raise _err(
                        "SEM0106",
                        f"Builtin '{name}' esperava {expected_builtin} argumentos, recebeu {len(expr.arguments)}.",
                        expr,
                        arquivo=arquivo,
                        sugestao="Consulte a assinatura do builtin e ajuste a chamada.",
                    )
                return _ref("qualquer")

        _ = callee_t
        return _ref("qualquer")

    raise _err(
        "SEM9998",
        f"Expressão sem validação semântica: {type(expr).__name__}.",
        expr,
        arquivo=arquivo,
    )
