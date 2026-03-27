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
    "json_parse": 1,
    "json_stringify": 1,
    "criar_tarefa": 1,
    "cancelar_tarefa": 1,
    "dormir": 1,
    "ler_texto_async": 1,
    "escrever_texto_async": 2,
    "com_timeout": 2,
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
