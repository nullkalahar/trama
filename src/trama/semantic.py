"""Análise semântica da linguagem trama."""

from __future__ import annotations

from dataclasses import dataclass

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
    UnaryExpr,
    WhileStmt,
)


class SemanticError(ValueError):
    """Erro semântico do programa trama."""


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


@dataclass
class _Context:
    in_function: bool = False
    in_async_function: bool = False
    loop_depth: int = 0


def validate_semantics(program: Program) -> None:
    signatures: dict[str, int] = {}
    _collect_signatures(program.declarations, signatures)

    ctx = _Context(in_function=False, in_async_function=False, loop_depth=0)
    for decl in program.declarations:
        _validate_stmt(decl, ctx, signatures)


def _collect_signatures(stmts: list[Stmt], signatures: dict[str, int]) -> None:
    for stmt in stmts:
        if isinstance(stmt, FunctionDecl):
            signatures[stmt.name] = len(stmt.params)
            _collect_signatures(stmt.body, signatures)
        elif isinstance(stmt, IfStmt):
            _collect_signatures(stmt.then_branch, signatures)
            if stmt.else_branch:
                _collect_signatures(stmt.else_branch, signatures)
        elif isinstance(stmt, WhileStmt):
            _collect_signatures(stmt.body, signatures)
        elif isinstance(stmt, TryStmt):
            _collect_signatures(stmt.try_branch, signatures)
            if stmt.catch_branch:
                _collect_signatures(stmt.catch_branch, signatures)
            if stmt.finally_branch:
                _collect_signatures(stmt.finally_branch, signatures)


def _validate_stmt(stmt: Stmt, ctx: _Context, signatures: dict[str, int]) -> None:
    if isinstance(stmt, FunctionDecl):
        child_ctx = _Context(in_function=True, in_async_function=stmt.is_async, loop_depth=0)
        for inner in stmt.body:
            _validate_stmt(inner, child_ctx, signatures)
        return

    if isinstance(stmt, ImportStmt):
        if not stmt.alias:
            raise SemanticError("Alias de 'importe' não pode ser vazio.")
        return

    if isinstance(stmt, IfStmt):
        _validate_expr(stmt.condition, signatures, ctx)
        for inner in stmt.then_branch:
            _validate_stmt(
                inner,
                _Context(ctx.in_function, ctx.in_async_function, ctx.loop_depth),
                signatures,
            )
        if stmt.else_branch:
            for inner in stmt.else_branch:
                _validate_stmt(
                    inner,
                    _Context(ctx.in_function, ctx.in_async_function, ctx.loop_depth),
                    signatures,
                )
        return

    if isinstance(stmt, WhileStmt):
        _validate_expr(stmt.condition, signatures, ctx)
        child_ctx = _Context(
            in_function=ctx.in_function,
            in_async_function=ctx.in_async_function,
            loop_depth=ctx.loop_depth + 1,
        )
        for inner in stmt.body:
            _validate_stmt(inner, child_ctx, signatures)
        return

    if isinstance(stmt, TryStmt):
        for inner in stmt.try_branch:
            _validate_stmt(
                inner,
                _Context(ctx.in_function, ctx.in_async_function, ctx.loop_depth),
                signatures,
            )
        if stmt.catch_branch is not None:
            for inner in stmt.catch_branch:
                _validate_stmt(
                    inner,
                    _Context(ctx.in_function, ctx.in_async_function, ctx.loop_depth),
                    signatures,
                )
        if stmt.finally_branch is not None:
            for inner in stmt.finally_branch:
                _validate_stmt(
                    inner,
                    _Context(ctx.in_function, ctx.in_async_function, ctx.loop_depth),
                    signatures,
                )
        return

    if isinstance(stmt, ThrowStmt):
        _validate_expr(stmt.value, signatures, ctx)
        return

    if isinstance(stmt, ReturnStmt):
        if not ctx.in_function:
            raise SemanticError("'retorne' só pode ser usado dentro de função.")
        if stmt.value is not None:
            _validate_expr(stmt.value, signatures, ctx)
        return

    if isinstance(stmt, BreakStmt):
        if ctx.loop_depth <= 0:
            raise SemanticError("'pare' só pode ser usado dentro de laço.")
        return

    if isinstance(stmt, ContinueStmt):
        if ctx.loop_depth <= 0:
            raise SemanticError("'continue' só pode ser usado dentro de laço.")
        return

    if isinstance(stmt, AssignStmt):
        _validate_expr(stmt.value, signatures, ctx)
        return

    if isinstance(stmt, ExprStmt):
        _validate_expr(stmt.expression, signatures, ctx)
        return

    raise SemanticError(f"Statement sem validação semântica: {type(stmt).__name__}")


def _validate_expr(expr: Expr, signatures: dict[str, int], ctx: _Context) -> None:
    if isinstance(expr, (Literal, Identifier)):
        return

    if isinstance(expr, UnaryExpr):
        _validate_expr(expr.operand, signatures, ctx)
        return

    if isinstance(expr, AwaitExpr):
        if not ctx.in_async_function:
            raise SemanticError("'aguarde' só pode ser usado dentro de função assíncrona.")
        _validate_expr(expr.expression, signatures, ctx)
        return

    if isinstance(expr, BinaryExpr):
        _validate_expr(expr.left, signatures, ctx)
        _validate_expr(expr.right, signatures, ctx)
        return

    if isinstance(expr, ListExpr):
        for element in expr.elements:
            _validate_expr(element, signatures, ctx)
        return

    if isinstance(expr, DictExpr):
        for key, value in expr.entries:
            _validate_expr(key, signatures, ctx)
            _validate_expr(value, signatures, ctx)
        return

    if isinstance(expr, IndexExpr):
        _validate_expr(expr.target, signatures, ctx)
        _validate_expr(expr.index, signatures, ctx)
        return

    if isinstance(expr, CallExpr):
        _validate_expr(expr.callee, signatures, ctx)
        for arg in expr.arguments:
            _validate_expr(arg, signatures, ctx)

        if isinstance(expr.callee, Identifier):
            name = expr.callee.name
            if name in signatures:
                expected = signatures[name]
                got = len(expr.arguments)
                if expected != got:
                    raise SemanticError(
                        f"Função '{name}' esperava {expected} argumentos, recebeu {got}."
                    )
            elif name in _BUILTIN_ARITY:
                expected_builtin = _BUILTIN_ARITY[name]
                if expected_builtin is not None and len(expr.arguments) != expected_builtin:
                    raise SemanticError(
                        f"Builtin '{name}' esperava {expected_builtin} argumentos, "
                        f"recebeu {len(expr.arguments)}."
                    )
        return

    raise SemanticError(f"Expressão sem validação semântica: {type(expr).__name__}")
