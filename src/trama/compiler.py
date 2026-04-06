"""Compilador AST -> bytecode da linguagem trama."""

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
    code_name: str
    params: list[str]
    display_name: str
    is_async: bool = False
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
        self._fn_counter = 0
        self._tmp_counter = 0

    def compile(self, program: Program) -> BytecodeProgram:
        entry_compiler = _FunctionCompiler(
            code_name="__entry__",
            display_name="__entry__",
            params=[],
            is_async=False,
        )

        for decl in program.declarations:
            self._compile_stmt(entry_compiler, decl)

        entry_compiler.emit("HALT")
        entry_code = FunctionCode(
            name=entry_compiler.code_name,
            params=entry_compiler.params,
            is_async=False,
            instructions=entry_compiler.instructions,
        )
        return BytecodeProgram(entry=entry_code, functions=self._functions)

    def _allocate_code_name(self, display_name: str) -> str:
        self._fn_counter += 1
        return f"{display_name}#{self._fn_counter}"

    def _allocate_tmp(self, prefix: str = "__tmp") -> str:
        self._tmp_counter += 1
        return f"{prefix}_{self._tmp_counter}"

    def _compile_function_decl(self, decl: FunctionDecl) -> str:
        code_name = self._allocate_code_name(decl.name)
        fn = _FunctionCompiler(
            code_name=code_name,
            display_name=decl.name,
            params=decl.params,
            is_async=decl.is_async,
        )
        for stmt in decl.body:
            self._compile_stmt(fn, stmt)
        fn.emit("LOAD_CONST", None)
        fn.emit("RETURN_VALUE")
        self._functions[code_name] = FunctionCode(
            name=fn.display_name,
            params=fn.params,
            is_async=fn.is_async,
            instructions=fn.instructions,
        )
        return code_name

    def _compile_stmt(self, fn: _FunctionCompiler, stmt: Stmt) -> None:
        if isinstance(stmt, FunctionDecl):
            code_name = self._compile_function_decl(stmt)
            fn.emit("MAKE_FUNCTION", (stmt.name, code_name, stmt.is_async))
            fn.emit("STORE_NAME", stmt.name)
            return

        if isinstance(stmt, AssignStmt):
            self._compile_expr(fn, stmt.value)
            fn.emit("STORE_NAME", stmt.name)
            return

        if isinstance(stmt, ImportStmt):
            fn.emit("IMPORT_NAME", stmt.module)
            if stmt.names:
                tmp_mod = self._allocate_tmp("__import_mod")
                fn.emit("STORE_NAME", tmp_mod)
                for nome in stmt.names:
                    fn.emit("LOAD_CONST", nome)
                    fn.emit("LOAD_NAME", tmp_mod)
                    fn.emit("LOAD_CONST", nome)
                    fn.emit("BINARY_SUBSCR")
                fn.emit("BUILD_MAP", len(stmt.names))
            fn.emit("STORE_NAME", stmt.alias)
            return

        if isinstance(stmt, ExportStmt):
            for nome in stmt.names:
                fn.emit("LOAD_CONST", nome)
                fn.emit("LOAD_CONST", True)
            fn.emit("BUILD_MAP", len(stmt.names))
            fn.emit("STORE_NAME", "__exportes__")
            return

        if isinstance(stmt, ThrowStmt):
            self._compile_expr(fn, stmt.value)
            fn.emit("THROW")
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

        if isinstance(stmt, ForStmt):
            iter_var = stmt.iterator
            tmp_iter = self._allocate_tmp("__for_iter")
            tmp_idx = self._allocate_tmp("__for_idx")

            self._compile_expr(fn, stmt.iterable)
            fn.emit("STORE_NAME", tmp_iter)
            fn.emit("LOAD_CONST", 0)
            fn.emit("STORE_NAME", tmp_idx)

            loop = _LoopPatch(start_ip=len(fn.instructions))
            fn.loops.append(loop)

            fn.emit("LOAD_NAME", tmp_idx)
            fn.emit("LOAD_NAME", "tamanho")
            fn.emit("LOAD_NAME", tmp_iter)
            fn.emit("CALL", 1)
            fn.emit("COMPARE_OP", "MENOR")
            jump_exit = fn.emit("JUMP_IF_FALSE", None)

            fn.emit("LOAD_NAME", tmp_iter)
            fn.emit("LOAD_NAME", tmp_idx)
            fn.emit("BINARY_SUBSCR")
            fn.emit("STORE_NAME", iter_var)

            for inner in stmt.body:
                self._compile_stmt(fn, inner)

            fn.emit("LOAD_NAME", tmp_idx)
            fn.emit("LOAD_CONST", 1)
            fn.emit("BINARY_ADD")
            fn.emit("STORE_NAME", tmp_idx)
            fn.emit("JUMP", loop.start_ip)

            exit_ip = len(fn.instructions)
            fn.patch(jump_exit, exit_ip)
            for idx in loop.break_jumps:
                fn.patch(idx, exit_ip)
            for idx in loop.continue_jumps:
                fn.patch(idx, loop.start_ip)
            fn.loops.pop()
            return

        if isinstance(stmt, TryStmt):
            try_push = fn.emit(
                "PUSH_TRY",
                {
                    "catch_ip": None,
                    "finally_ip": None,
                    "catch_name": stmt.catch_name,
                },
            )

            for inner in stmt.try_branch:
                self._compile_stmt(fn, inner)
            fn.emit("END_TRY_BLOCK")
            jump_after_try = fn.emit("JUMP", None)

            catch_ip = None
            if stmt.catch_branch is not None:
                catch_ip = len(fn.instructions)
                for inner in stmt.catch_branch:
                    self._compile_stmt(fn, inner)
                fn.emit("END_CATCH_BLOCK")
                fn.emit("JUMP", None)

            finally_ip = None
            if stmt.finally_branch is not None:
                finally_ip = len(fn.instructions)
                fn.emit("BEGIN_FINALLY")
                for inner in stmt.finally_branch:
                    self._compile_stmt(fn, inner)
                fn.emit("END_FINALLY")

            after_ip = len(fn.instructions)
            fn.patch(jump_after_try, after_ip)

            # corrige salto ao fim após catch (se existir)
            if stmt.catch_branch is not None:
                # último jump emitido logo após END_CATCH_BLOCK
                end_catch_jump = -1
                for idx in range(after_ip - 1, -1, -1):
                    instr = fn.instructions[idx]
                    if instr.op == "JUMP" and instr.arg is None:
                        end_catch_jump = idx
                        break
                if end_catch_jump >= 0:
                    fn.patch(end_catch_jump, after_ip)

            fn.patch(
                try_push,
                {
                    "catch_ip": catch_ip,
                    "finally_ip": finally_ip,
                    "catch_name": stmt.catch_name,
                },
            )
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

        if isinstance(expr, AwaitExpr):
            self._compile_expr(fn, expr.expression)
            fn.emit("AWAIT")
            return

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
            compare_ops = {
                "IGUAL_IGUAL",
                "DIFERENTE",
                "MAIOR",
                "MAIOR_IGUAL",
                "MENOR",
                "MENOR_IGUAL",
            }
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

        if isinstance(expr, IndexExpr):
            self._compile_expr(fn, expr.target)
            self._compile_expr(fn, expr.index)
            fn.emit("BINARY_SUBSCR")
            return

        if isinstance(expr, ListExpr):
            for element in expr.elements:
                self._compile_expr(fn, element)
            fn.emit("BUILD_LIST", len(expr.elements))
            return

        if isinstance(expr, DictExpr):
            for key, value in expr.entries:
                self._compile_expr(fn, key)
                self._compile_expr(fn, value)
            fn.emit("BUILD_MAP", len(expr.entries))
            return

        raise CompileError(f"Expressão não suportada: {type(expr).__name__}")


def compile_ast(program: Program) -> BytecodeProgram:
    return Compiler().compile(program)


def compile_source(codigo: str, arquivo: str | None = None) -> BytecodeProgram:
    program = parse(codigo)
    try:
        validate_semantics(program, arquivo=arquivo)
    except SemanticError as exc:
        raise CompileError(str(exc)) from exc
    return compile_ast(program)
