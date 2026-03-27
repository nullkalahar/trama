"""Estruturas de bytecode da linguagem trama."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Instruction:
    op: str
    arg: object | None = None


@dataclass
class FunctionCode:
    name: str
    params: list[str]
    is_async: bool = False
    instructions: list[Instruction] = field(default_factory=list)


@dataclass
class BytecodeProgram:
    entry: FunctionCode
    functions: dict[str, FunctionCode]


def function_to_dict(function: FunctionCode) -> dict[str, object]:
    return {
        "name": function.name,
        "params": function.params,
        "is_async": function.is_async,
        "instructions": [{"op": i.op, "arg": i.arg} for i in function.instructions],
    }


def program_to_dict(program: BytecodeProgram) -> dict[str, object]:
    return {
        "entry": function_to_dict(program.entry),
        "functions": {name: function_to_dict(fn) for name, fn in program.functions.items()},
    }


def format_program(program: BytecodeProgram) -> str:
    lines: list[str] = []

    def emit_function(fn: FunctionCode) -> None:
        prefix = "async func" if fn.is_async else "func"
        lines.append(f"{prefix} {fn.name}({', '.join(fn.params)})")
        for ip, instr in enumerate(fn.instructions):
            if instr.arg is None:
                lines.append(f"  {ip:04d}: {instr.op}")
            else:
                lines.append(f"  {ip:04d}: {instr.op} {instr.arg!r}")
        lines.append("")

    lines.append("== ENTRY ==")
    emit_function(program.entry)
    if program.functions:
        lines.append("== FUNCTIONS ==")
        for name in sorted(program.functions):
            emit_function(program.functions[name])
    return "\n".join(lines).rstrip() + "\n"
