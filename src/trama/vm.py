"""Máquina virtual de bytecode da linguagem trama."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .builtins import make_builtins
from .bytecode import BytecodeProgram, FunctionCode
from .compiler import compile_source


class VMError(RuntimeError):
    """Erro em tempo de execução da VM."""


@dataclass(frozen=True)
class UserFunction:
    name: str
    code: FunctionCode


@dataclass
class Frame:
    code: FunctionCode
    ip: int
    locals: dict[str, object]
    stack: list[object]


class VirtualMachine:
    def __init__(self, program: BytecodeProgram, print_fn: Any | None = None) -> None:
        self.program = program
        self.globals: dict[str, object] = {}
        self.globals.update(make_builtins(print_fn=print_fn))
        for name, fn_code in self.program.functions.items():
            self.globals[name] = UserFunction(name=name, code=fn_code)

    def execute(self) -> object:
        result = self._run_function(self.program.entry, args=[])
        principal = self.globals.get("principal")
        if isinstance(principal, UserFunction):
            return self._call_callable(principal, [])
        return result

    def _run_function(self, code: FunctionCode, args: list[object]) -> object:
        if len(args) != len(code.params):
            raise VMError(
                f"Função '{code.name}' esperava {len(code.params)} argumentos, recebeu {len(args)}."
            )
        frame = Frame(
            code=code,
            ip=0,
            locals=dict(zip(code.params, args, strict=False)),
            stack=[],
        )
        return self._run_frame(frame)

    def _run_frame(self, frame: Frame) -> object:
        instructions = frame.code.instructions
        while frame.ip < len(instructions):
            instr = instructions[frame.ip]
            frame.ip += 1
            op = instr.op
            arg = instr.arg

            if op == "LOAD_CONST":
                frame.stack.append(arg)
            elif op == "LOAD_NAME":
                frame.stack.append(self._resolve_name(frame, str(arg)))
            elif op == "STORE_NAME":
                value = frame.stack.pop()
                frame.locals[str(arg)] = value
            elif op == "POP_TOP":
                if not frame.stack:
                    raise VMError("Pilha vazia em POP_TOP.")
                frame.stack.pop()
            elif op == "NEGATE":
                frame.stack.append(-frame.stack.pop())
            elif op == "BINARY_ADD":
                b = frame.stack.pop()
                a = frame.stack.pop()
                frame.stack.append(a + b)
            elif op == "BINARY_SUB":
                b = frame.stack.pop()
                a = frame.stack.pop()
                frame.stack.append(a - b)
            elif op == "BINARY_MUL":
                b = frame.stack.pop()
                a = frame.stack.pop()
                frame.stack.append(a * b)
            elif op == "BINARY_DIV":
                b = frame.stack.pop()
                a = frame.stack.pop()
                frame.stack.append(a / b)
            elif op == "COMPARE_OP":
                b = frame.stack.pop()
                a = frame.stack.pop()
                frame.stack.append(self._compare(str(arg), a, b))
            elif op == "JUMP":
                frame.ip = int(arg)
            elif op == "JUMP_IF_FALSE":
                value = frame.stack.pop()
                if not value:
                    frame.ip = int(arg)
            elif op == "CALL":
                argc = int(arg)
                if len(frame.stack) < argc + 1:
                    raise VMError("Pilha insuficiente para CALL.")
                if argc > 0:
                    args = frame.stack[-argc:]
                    del frame.stack[-argc:]
                else:
                    args = []
                callee = frame.stack.pop()
                frame.stack.append(self._call_callable(callee, args))
            elif op == "RETURN_VALUE":
                return frame.stack.pop() if frame.stack else None
            elif op == "HALT":
                return None
            else:
                raise VMError(f"Instrução desconhecida: {op}")
        return None

    def _resolve_name(self, frame: Frame, name: str) -> object:
        if name in frame.locals:
            return frame.locals[name]
        if name in self.globals:
            return self.globals[name]
        raise VMError(f"Nome não definido: {name}")

    def _call_callable(self, callee: object, args: list[object]) -> object:
        if isinstance(callee, UserFunction):
            return self._run_function(callee.code, args)
        if callable(callee):
            return callee(*args)
        raise VMError(f"Valor não chamável: {callee!r}")

    @staticmethod
    def _compare(op: str, a: object, b: object) -> bool:
        if op == "IGUAL_IGUAL":
            return a == b
        if op == "DIFERENTE":
            return a != b
        if op == "MAIOR":
            return a > b
        if op == "MAIOR_IGUAL":
            return a >= b
        if op == "MENOR":
            return a < b
        if op == "MENOR_IGUAL":
            return a <= b
        raise VMError(f"Operador de comparação desconhecido: {op}")


def run_source(codigo: str, print_fn: Any | None = None) -> object:
    program = compile_source(codigo)
    vm = VirtualMachine(program=program, print_fn=print_fn)
    return vm.execute()
