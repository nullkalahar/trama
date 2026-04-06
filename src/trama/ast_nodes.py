"""Nós de AST da linguagem trama."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    pass


@dataclass(frozen=True)
class Program(Node):
    declarations: list[Stmt]


@dataclass(frozen=True)
class Stmt(Node):
    pass


@dataclass(frozen=True)
class Expr(Node):
    pass


@dataclass(frozen=True)
class FunctionDecl(Stmt):
    name: str
    params: list[str]
    body: list[Stmt]
    is_async: bool = False
    param_types: dict[str, TypeRef] | None = None
    return_type: TypeRef | None = None
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class IfStmt(Stmt):
    condition: Expr
    then_branch: list[Stmt]
    else_branch: list[Stmt] | None
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class WhileStmt(Stmt):
    condition: Expr
    body: list[Stmt]
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class ForStmt(Stmt):
    iterator: str
    iterable: Expr
    body: list[Stmt]
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class ReturnStmt(Stmt):
    value: Expr | None
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class BreakStmt(Stmt):
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class ContinueStmt(Stmt):
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class AssignStmt(Stmt):
    name: str
    value: Expr
    annotation: TypeRef | None = None
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class ExprStmt(Stmt):
    expression: Expr
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class ImportStmt(Stmt):
    module: str
    alias: str
    names: list[str] | None = None
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class ExportStmt(Stmt):
    names: list[str]
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class TryStmt(Stmt):
    try_branch: list[Stmt]
    catch_name: str | None
    catch_branch: list[Stmt] | None
    finally_branch: list[Stmt] | None
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class ThrowStmt(Stmt):
    value: Expr
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class BinaryExpr(Expr):
    left: Expr
    operator: str
    right: Expr
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class UnaryExpr(Expr):
    operator: str
    operand: Expr
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class AwaitExpr(Expr):
    expression: Expr
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class CallExpr(Expr):
    callee: Expr
    arguments: list[Expr]
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class IndexExpr(Expr):
    target: Expr
    index: Expr
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class ListExpr(Expr):
    elements: list[Expr]
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class DictExpr(Expr):
    entries: list[tuple[Expr, Expr]]
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class Identifier(Expr):
    name: str
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class Literal(Expr):
    value: object
    linha: int = 0
    coluna: int = 0


@dataclass(frozen=True)
class TypeRef(Node):
    nome: str
    args: list[TypeRef]
