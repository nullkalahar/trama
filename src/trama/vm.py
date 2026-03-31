"""Máquina virtual de bytecode da linguagem trama."""

from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass, field
from pathlib import Path
import threading
from typing import Any

from .builtins import make_builtins
from .bytecode import BytecodeProgram, FunctionCode, program_from_dict
from .compiler import compile_source


class VMError(RuntimeError):
    """Erro em tempo de execução da VM."""


class TramaRaised(Exception):
    """Exceção de usuário levantada por lance."""

    def __init__(self, value: object) -> None:
        super().__init__(repr(value))
        self.value = value


@dataclass
class Environment:
    values: dict[str, object]
    parent: Environment | None = None

    def get(self, name: str) -> object:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise VMError(f"Nome não definido: {name}")

    def set(self, name: str, value: object) -> None:
        if name in self.values:
            self.values[name] = value
            return
        if self.parent is not None and self.parent.contains(name):
            self.parent.set(name, value)
            return
        self.values[name] = value

    def set_local(self, name: str, value: object) -> None:
        self.values[name] = value

    def contains(self, name: str) -> bool:
        if name in self.values:
            return True
        if self.parent is not None:
            return self.parent.contains(name)
        return False


@dataclass(frozen=True)
class UserFunction:
    name: str
    code: FunctionCode
    closure: Environment


@dataclass
class TramaCoroutine:
    vm: VirtualMachine
    callee: UserFunction
    args: list[object]

    async def run(self) -> object:
        return await self.vm._run_function(self.callee.code, self.args, closure=self.callee.closure)

    def __await__(self):
        return self.run().__await__()


@dataclass
class TryHandler:
    catch_ip: int | None
    finally_ip: int | None
    catch_name: str | None
    phase: str = "try"
    pending_exception: object | None = None


@dataclass
class Frame:
    code: FunctionCode
    ip: int
    env: Environment
    stack: list[object]
    handlers: list[TryHandler] = field(default_factory=list)


class VirtualMachine:
    def __init__(
        self,
        program: BytecodeProgram,
        print_fn: Any | None = None,
        source_path: str | None = None,
        module_cache: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self.program = program
        self.print_fn = print_fn
        self.source_path = Path(source_path).resolve() if source_path else None
        self.module_cache = module_cache if module_cache is not None else {}
        self._invoke_lock = threading.RLock()

        self._builtins = make_builtins(print_fn=print_fn, invoke_callable_sync=self._invoke_from_runtime_sync)
        self.globals_env = Environment(values=dict(self._builtins), parent=None)

    def execute(self, auto_call_principal: bool = True) -> object:
        return asyncio.run(self.execute_async(auto_call_principal=auto_call_principal))

    async def execute_async(self, auto_call_principal: bool = True) -> object:
        result = await self._run_entry()
        if auto_call_principal:
            principal = self.globals_env.values.get("principal")
            if isinstance(principal, UserFunction):
                called = await self._call_callable(principal, [])
                if principal.code.is_async:
                    return await self._await_value(called)
                return called
        return result

    async def _run_entry(self) -> object:
        frame = Frame(code=self.program.entry, ip=0, env=self.globals_env, stack=[])
        return await self._run_frame(frame)

    async def _run_function(self, code: FunctionCode, args: list[object], closure: Environment) -> object:
        if len(args) != len(code.params):
            raise VMError(
                f"Função '{code.name}' esperava {len(code.params)} argumentos, recebeu {len(args)}."
            )

        fn_env = Environment(values={}, parent=closure)
        for param, value in zip(code.params, args, strict=False):
            fn_env.set_local(param, value)

        frame = Frame(code=code, ip=0, env=fn_env, stack=[])
        return await self._run_frame(frame)

    async def _run_frame(self, frame: Frame) -> object:
        instructions = frame.code.instructions
        while frame.ip < len(instructions):
            try:
                instr = instructions[frame.ip]
                frame.ip += 1
                op = instr.op
                arg = instr.arg

                if op == "LOAD_CONST":
                    frame.stack.append(arg)
                elif op == "LOAD_NAME":
                    frame.stack.append(frame.env.get(str(arg)))
                elif op == "STORE_NAME":
                    value = frame.stack.pop()
                    frame.env.set(str(arg), value)
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
                elif op == "BINARY_SUBSCR":
                    index = frame.stack.pop()
                    target = frame.stack.pop()
                    try:
                        frame.stack.append(target[index])
                    except Exception as exc:
                        raise TramaRaised(str(exc)) from exc
                elif op == "BUILD_LIST":
                    count = int(arg)
                    if count < 0 or len(frame.stack) < count:
                        raise VMError("Pilha insuficiente para BUILD_LIST.")
                    if count == 0:
                        frame.stack.append([])
                    else:
                        items = frame.stack[-count:]
                        del frame.stack[-count:]
                        frame.stack.append(items)
                elif op == "BUILD_MAP":
                    count = int(arg)
                    needed = count * 2
                    if count < 0 or len(frame.stack) < needed:
                        raise VMError("Pilha insuficiente para BUILD_MAP.")
                    entries = frame.stack[-needed:]
                    del frame.stack[-needed:]
                    built: dict[object, object] = {}
                    for i in range(0, len(entries), 2):
                        built[entries[i]] = entries[i + 1]
                    frame.stack.append(built)
                elif op == "CALL":
                    argc = int(arg)
                    if len(frame.stack) < argc + 1:
                        raise VMError("Pilha insuficiente para CALL.")
                    args = frame.stack[-argc:] if argc > 0 else []
                    if argc > 0:
                        del frame.stack[-argc:]
                    callee = frame.stack.pop()
                    frame.stack.append(await self._call_callable(callee, args))
                elif op == "AWAIT":
                    value = frame.stack.pop() if frame.stack else None
                    frame.stack.append(await self._await_value(value))
                elif op == "MAKE_FUNCTION":
                    display_name, code_name, _is_async = tuple(arg)
                    fn_code = self.program.functions[str(code_name)]
                    frame.stack.append(UserFunction(name=str(display_name), code=fn_code, closure=frame.env))
                elif op == "IMPORT_NAME":
                    module_name = str(arg)
                    frame.stack.append(await self._import_module(module_name))
                elif op == "THROW":
                    value = frame.stack.pop() if frame.stack else None
                    raise TramaRaised(value)
                elif op == "PUSH_TRY":
                    if not isinstance(arg, dict):
                        raise VMError("PUSH_TRY inválido.")
                    frame.handlers.append(
                        TryHandler(
                            catch_ip=arg.get("catch_ip"),
                            finally_ip=arg.get("finally_ip"),
                            catch_name=arg.get("catch_name"),
                        )
                    )
                elif op == "END_TRY_BLOCK":
                    self._end_try_block(frame)
                elif op == "END_CATCH_BLOCK":
                    self._end_catch_block(frame)
                elif op == "BEGIN_FINALLY":
                    self._begin_finally(frame)
                elif op == "END_FINALLY":
                    self._end_finally(frame)
                elif op == "JUMP":
                    frame.ip = int(arg)
                elif op == "JUMP_IF_FALSE":
                    value = frame.stack.pop()
                    if not value:
                        frame.ip = int(arg)
                elif op == "RETURN_VALUE":
                    return frame.stack.pop() if frame.stack else None
                elif op == "HALT":
                    return None
                else:
                    raise VMError(f"Instrução desconhecida: {op}")
            except TramaRaised as exc:
                if self._handle_trama_exception(frame, exc):
                    continue
                raise VMError(f"Exceção não tratada: {exc.value!r}") from None

        return None

    async def _await_value(self, value: object) -> object:
        if isinstance(value, TramaCoroutine):
            return await value
        if inspect.isawaitable(value):
            return await value
        raise VMError("Valor não aguardável em 'aguarde'.")

    def _end_try_block(self, frame: Frame) -> None:
        if not frame.handlers:
            raise VMError("END_TRY_BLOCK sem handler ativo.")
        handler = frame.handlers[-1]
        if handler.phase != "try":
            raise VMError("END_TRY_BLOCK fora da fase try.")
        if handler.finally_ip is not None:
            handler.phase = "finally"
            frame.ip = handler.finally_ip
        else:
            frame.handlers.pop()

    def _end_catch_block(self, frame: Frame) -> None:
        if not frame.handlers:
            raise VMError("END_CATCH_BLOCK sem handler ativo.")
        handler = frame.handlers[-1]
        if handler.phase != "catch":
            raise VMError("END_CATCH_BLOCK fora da fase catch.")
        if handler.finally_ip is not None:
            handler.phase = "finally"
            frame.ip = handler.finally_ip
        else:
            frame.handlers.pop()

    def _begin_finally(self, frame: Frame) -> None:
        if not frame.handlers:
            raise VMError("BEGIN_FINALLY sem handler ativo.")
        frame.handlers[-1].phase = "finally"

    def _end_finally(self, frame: Frame) -> None:
        if not frame.handlers:
            raise VMError("END_FINALLY sem handler ativo.")
        handler = frame.handlers.pop()
        if handler.pending_exception is not None:
            raise TramaRaised(handler.pending_exception)

    def _handle_trama_exception(self, frame: Frame, exc: TramaRaised) -> bool:
        while frame.handlers:
            handler = frame.handlers[-1]

            if handler.phase == "finally":
                frame.handlers.pop()
                continue

            if handler.phase == "try":
                if handler.catch_ip is not None:
                    handler.phase = "catch"
                    if handler.catch_name:
                        frame.env.set_local(handler.catch_name, exc.value)
                    frame.ip = handler.catch_ip
                    return True
                if handler.finally_ip is not None:
                    handler.phase = "finally"
                    handler.pending_exception = exc.value
                    frame.ip = handler.finally_ip
                    return True
                frame.handlers.pop()
                continue

            if handler.phase == "catch":
                if handler.finally_ip is not None:
                    handler.phase = "finally"
                    handler.pending_exception = exc.value
                    frame.ip = handler.finally_ip
                    return True
                frame.handlers.pop()
                continue

            frame.handlers.pop()

        return False

    async def _call_callable(self, callee: object, args: list[object]) -> object:
        if isinstance(callee, UserFunction):
            if callee.code.is_async:
                return TramaCoroutine(vm=self, callee=callee, args=args)
            return await self._run_function(callee.code, args, closure=callee.closure)

        if callable(callee):
            try:
                result = callee(*args)
                return result
            except TramaRaised:
                raise
            except Exception as exc:
                raise TramaRaised(str(exc)) from exc

        raise VMError(f"Valor não chamável: {callee!r}")

    async def _invoke_from_runtime(self, callee: object, args: list[object]) -> object:
        result = await self._call_callable(callee, args)
        if isinstance(result, TramaCoroutine) or inspect.isawaitable(result):
            return await self._await_value(result)
        return result

    def _invoke_from_runtime_sync(self, callee: object, args: list[object]) -> object:
        with self._invoke_lock:
            return asyncio.run(self._invoke_from_runtime(callee, args))

    async def _import_module(self, module_ref: str) -> dict[str, object]:
        path = self._resolve_module_path(module_ref)
        key = str(path)
        if key in self.module_cache:
            return self.module_cache[key]

        code = path.read_text(encoding="utf-8")
        program = compile_source(code)
        module_vm = VirtualMachine(
            program=program,
            print_fn=self.print_fn,
            source_path=str(path),
            module_cache=self.module_cache,
        )
        await module_vm.execute_async(auto_call_principal=False)

        exports = {
            name: value
            for name, value in module_vm.globals_env.values.items()
            if name not in module_vm._builtins
        }
        self.module_cache[key] = exports
        return exports

    def _resolve_module_path(self, module_ref: str) -> Path:
        base_dir = self.source_path.parent if self.source_path else Path.cwd()
        module_path = Path(module_ref)

        candidates: list[Path] = []
        if module_path.suffix == ".trm":
            candidates.append(module_path)
            if not module_path.is_absolute():
                candidates.append(base_dir / module_path)
        elif "/" in module_ref or "\\" in module_ref:
            candidates.append(base_dir / module_path)
            candidates.append(base_dir / f"{module_ref}.trm")
        else:
            candidates.append(base_dir / f"{module_ref}.trm")
            candidates.append(base_dir / module_ref / "mod.trm")

        for candidate in candidates:
            path = candidate.resolve() if candidate.is_absolute() else candidate.resolve()
            if path.exists() and path.is_file():
                return path

        raise VMError(f"Módulo não encontrado: {module_ref}")

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


def run_source(codigo: str, print_fn: Any | None = None, source_path: str | None = None) -> object:
    program = compile_source(codigo)
    vm = VirtualMachine(program=program, print_fn=print_fn, source_path=source_path)
    return vm.execute()


def run_bytecode_dict(
    payload: dict[str, object],
    print_fn: Any | None = None,
    source_path: str | None = None,
) -> object:
    program = program_from_dict(payload, validar=True, validar_opcodes=False)
    vm = VirtualMachine(program=program, print_fn=print_fn, source_path=source_path)
    return vm.execute()


def run_bytecode_file(caminho: str, print_fn: Any | None = None) -> object:
    path = Path(caminho)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise VMError("Arquivo de bytecode inválido: JSON raiz deve ser objeto.")
    return run_bytecode_dict(payload, print_fn=print_fn, source_path=str(path))
