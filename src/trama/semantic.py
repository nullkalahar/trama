"""Análise semântica mínima para a v0.1 da trama."""

from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import (
    AssignStmt,
    BinaryExpr,
    BreakStmt,
    CallExpr,
    ContinueStmt,
    Expr,
    ExprStmt,
    FunctionDecl,
    Identifier,
    IfStmt,
    Literal,
    Program,
    ReturnStmt,
    Stmt,
    UnaryExpr,
    WhileStmt,
)


class SemanticError(ValueError):
    """Erro semântico do programa trama."""


_BUILTIN_ARITY: dict[str, int | None] = {
    "exibir": None,  # variádica
}


@dataclass
class _Context:
    in_function: bool = False
    loop_depth: int = 0


def validate_semantics(program: Program) -> None:
    signatures: dict[str, int] = {}

    for decl in program.declarations:
        if isinstance(decl, FunctionDecl):
            if decl.name in signatures:
                raise SemanticError(f"Função '{decl.name}' declarada mais de uma vez.")
            signatures[decl.name] = len(decl.params)

    ctx = _Context(in_function=False, loop_depth=0)
    for decl in program.declarations:
        _validate_stmt(decl, ctx, signatures)


def _validate_stmt(stmt: Stmt, ctx: _Context, signatures: dict[str, int]) -> None:
    if isinstance(stmt, FunctionDecl):
        if ctx.in_function:
            raise SemanticError("Funções aninhadas ainda não são suportadas na v0.1.")
        child_ctx = _Context(in_function=True, loop_depth=0)
        for inner in stmt.body:
            _validate_stmt(inner, child_ctx, signatures)
        return

    if isinstance(stmt, IfStmt):
        _validate_expr(stmt.condition, signatures)
        for inner in stmt.then_branch:
            _validate_stmt(inner, _Context(ctx.in_function, ctx.loop_depth), signatures)
        if stmt.else_branch:
            for inner in stmt.else_branch:
                _validate_stmt(inner, _Context(ctx.in_function, ctx.loop_depth), signatures)
        return

    if isinstance(stmt, WhileStmt):
        _validate_expr(stmt.condition, signatures)
        child_ctx = _Context(in_function=ctx.in_function, loop_depth=ctx.loop_depth + 1)
        for inner in stmt.body:
            _validate_stmt(inner, child_ctx, signatures)
        return

    if isinstance(stmt, ReturnStmt):
        if not ctx.in_function:
            raise SemanticError("'retorne' só pode ser usado dentro de função.")
        if stmt.value is not None:
            _validate_expr(stmt.value, signatures)
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
        _validate_expr(stmt.value, signatures)
        return

    if isinstance(stmt, ExprStmt):
        _validate_expr(stmt.expression, signatures)
        return

    raise SemanticError(f"Statement sem validação semântica: {type(stmt).__name__}")


def _validate_expr(expr: Expr, signatures: dict[str, int]) -> None:
    if isinstance(expr, Literal):
        return

    if isinstance(expr, Identifier):
        return

    if isinstance(expr, UnaryExpr):
        _validate_expr(expr.operand, signatures)
        return

    if isinstance(expr, BinaryExpr):
        _validate_expr(expr.left, signatures)
        _validate_expr(expr.right, signatures)
        return

    if isinstance(expr, CallExpr):
        _validate_expr(expr.callee, signatures)
        for arg in expr.arguments:
            _validate_expr(arg, signatures)

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
