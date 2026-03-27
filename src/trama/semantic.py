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
    "http_get": None,
    "http_post": None,
    "http_obter": None,
    "http_postar": None,
    "env_obter": None,
    "env_todos": None,
    "config_carregar": None,
    "agora_iso": 0,
    "timestamp": 0,
    "web_criar_app": 0,
    "web_adicionar_rota_json": None,
    "web_adicionar_rota_echo_json": None,
    "web_usar_middleware": 2,
    "web_configurar_cors": None,
    "web_ativar_healthcheck": None,
    "web_servir_estaticos": 3,
    "web_rota": None,
    "web_rota_contrato": None,
    "web_middleware": None,
    "web_tratador_erro": 2,
    "web_rate_limit": None,
    "web_limite_taxa": None,
    "web_api_versionar": None,
    "web_api_versao": None,
    "web_rota_com_contrato": None,
    "web_saude_paths": None,
    "web_iniciar": None,
    "web_parar": 1,
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
    "migracao_aplicar": 3,
    "seed_aplicar": 3,
    "migracao_aplicar_versionada": None,
    "migracao_status": 1,
    "migracao_reverter_ultima": 1,
    "migracao_validar_compatibilidade": 3,
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
    "semente_aplicar": 3,
    "migracao_versionada_aplicar": None,
    "migracao_listar": 1,
    "migracao_desfazer_ultima": 1,
    "migracao_compatibilidade_validar": 3,
    "jwt_criar": None,
    "jwt_verificar": None,
    "senha_hash": None,
    "senha_verificar": 2,
    "rbac_criar": None,
    "rbac_atribuir": 3,
    "rbac_papeis_usuario": 2,
    "rbac_tem_papel": 3,
    "rbac_tem_permissao": 4,
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
