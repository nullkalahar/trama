"""Compilador AST -> bytecode da linguagem trama."""

from __future__ import annotations

from dataclasses import dataclass, field

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
from .bytecode import BytecodeProgram, FunctionCode, Instruction
from .parser import parse
from .semantic import SemanticError, validate_semantics


class CompileError(ValueError):
    """Erro de compilação."""


@dataclass
class _LoopPatch:
    start_ip: int
    break_jumps: list[int] = field(default_factory=list)
    continue_jumps: list[int] = field(default_factory=list)


@dataclass
class _FunctionCompiler:
    name: str
    params: list[str]
    instructions: list[Instruction] = field(default_factory=list)
    loops: list[_LoopPatch] = field(default_factory=list)

    def emit(self, op: str, arg: object | None = None) -> int:
        self.instructions.append(Instruction(op=op, arg=arg))
        return len(self.instructions) - 1

    def patch(self, index: int, arg: object) -> None:
        instr = self.instructions[index]
        self.instructions[index] = Instruction(op=instr.op, arg=arg)


class Compiler:
    def __init__(self) -> None:
        self._functions: dict[str, FunctionCode] = {}

    def compile(self, program: Program) -> BytecodeProgram:
        entry_compiler = _FunctionCompiler(name="__entry__", params=[])

        for decl in program.declarations:
            if isinstance(decl, FunctionDecl):
                self._compile_function_decl(decl)
            else:
                self._compile_stmt(entry_compiler, decl)

        entry_compiler.emit("HALT")
        entry_code = FunctionCode(
            name=entry_compiler.name,
            params=entry_compiler.params,
            instructions=entry_compiler.instructions,
        )
        return BytecodeProgram(entry=entry_code, functions=self._functions)

    def _compile_function_decl(self, decl: FunctionDecl) -> None:
        fn = _FunctionCompiler(name=decl.name, params=decl.params)
        for stmt in decl.body:
            self._compile_stmt(fn, stmt)
        fn.emit("LOAD_CONST", None)
        fn.emit("RETURN_VALUE")
        self._functions[decl.name] = FunctionCode(
            name=decl.name,
            params=decl.params,
            instructions=fn.instructions,
        )

    def _compile_stmt(self, fn: _FunctionCompiler, stmt: Stmt) -> None:
        if isinstance(stmt, AssignStmt):
            self._compile_expr(fn, stmt.value)
            fn.emit("STORE_NAME", stmt.name)
            return
        if isinstance(stmt, ExprStmt):
            self._compile_expr(fn, stmt.expression)
            fn.emit("POP_TOP")
            return
        if isinstance(stmt, ReturnStmt):
            if stmt.value is None:
                fn.emit("LOAD_CONST", None)
            else:
                self._compile_expr(fn, stmt.value)
            fn.emit("RETURN_VALUE")
            return
        if isinstance(stmt, IfStmt):
            self._compile_expr(fn, stmt.condition)
            jump_if_false = fn.emit("JUMP_IF_FALSE", None)
            for inner in stmt.then_branch:
                self._compile_stmt(fn, inner)
            if stmt.else_branch is not None:
                jump_end = fn.emit("JUMP", None)
                fn.patch(jump_if_false, len(fn.instructions))
                for inner in stmt.else_branch:
                    self._compile_stmt(fn, inner)
                fn.patch(jump_end, len(fn.instructions))
            else:
                fn.patch(jump_if_false, len(fn.instructions))
            return
        if isinstance(stmt, WhileStmt):
            loop = _LoopPatch(start_ip=len(fn.instructions))
            fn.loops.append(loop)
            self._compile_expr(fn, stmt.condition)
            jump_exit = fn.emit("JUMP_IF_FALSE", None)
            for inner in stmt.body:
                self._compile_stmt(fn, inner)
            fn.emit("JUMP", loop.start_ip)
            exit_ip = len(fn.instructions)
            fn.patch(jump_exit, exit_ip)
            for idx in loop.break_jumps:
                fn.patch(idx, exit_ip)
            for idx in loop.continue_jumps:
                fn.patch(idx, loop.start_ip)
            fn.loops.pop()
            return
        if isinstance(stmt, BreakStmt):
            if not fn.loops:
                raise CompileError("'pare' usado fora de um laço.")
            idx = fn.emit("JUMP", None)
            fn.loops[-1].break_jumps.append(idx)
            return
        if isinstance(stmt, ContinueStmt):
            if not fn.loops:
                raise CompileError("'continue' usado fora de um laço.")
            idx = fn.emit("JUMP", None)
            fn.loops[-1].continue_jumps.append(idx)
            return
        raise CompileError(f"Statement não suportado: {type(stmt).__name__}")

    def _compile_expr(self, fn: _FunctionCompiler, expr: Expr) -> None:
        if isinstance(expr, Literal):
            fn.emit("LOAD_CONST", expr.value)
            return
        if isinstance(expr, Identifier):
            fn.emit("LOAD_NAME", expr.name)
            return
        if isinstance(expr, UnaryExpr):
            self._compile_expr(fn, expr.operand)
            if expr.operator == "MENOS":
                fn.emit("NEGATE")
                return
            raise CompileError(f"Operador unário não suportado: {expr.operator}")
        if isinstance(expr, BinaryExpr):
            self._compile_expr(fn, expr.left)
            self._compile_expr(fn, expr.right)
            binary_map = {
                "MAIS": "BINARY_ADD",
                "MENOS": "BINARY_SUB",
                "ASTERISCO": "BINARY_MUL",
                "BARRA": "BINARY_DIV",
            }
            if expr.operator in binary_map:
                fn.emit(binary_map[expr.operator])
                return
            compare_ops = {"IGUAL_IGUAL", "DIFERENTE", "MAIOR", "MAIOR_IGUAL", "MENOR", "MENOR_IGUAL"}
            if expr.operator in compare_ops:
                fn.emit("COMPARE_OP", expr.operator)
                return
            raise CompileError(f"Operador binário não suportado: {expr.operator}")
        if isinstance(expr, CallExpr):
            self._compile_expr(fn, expr.callee)
            for arg in expr.arguments:
                self._compile_expr(fn, arg)
            fn.emit("CALL", len(expr.arguments))
            return
        raise CompileError(f"Expressão não suportada: {type(expr).__name__}")


def compile_ast(program: Program) -> BytecodeProgram:
    return Compiler().compile(program)


def compile_source(codigo: str) -> BytecodeProgram:
    program = parse(codigo)
    try:
        validate_semantics(program)
    except SemanticError as exc:
        raise CompileError(str(exc)) from exc
    return compile_ast(program)
