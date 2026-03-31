"""Estruturas de bytecode da linguagem trama."""

from __future__ import annotations

from dataclasses import dataclass, field


BYTECODE_FORMATO_V1 = "bytecode_v1"
ABI_VM_V1 = "vm_abi_v1"
VERSAO_SERIALIZACAO_V1 = 1

OPCODES_V1: frozenset[str] = frozenset(
    {
        "HALT",
        "JUMP",
        "JUMP_IF_FALSE",
        "RETURN_VALUE",
        "LOAD_CONST",
        "LOAD_NAME",
        "STORE_NAME",
        "POP_TOP",
        "NEGATE",
        "BINARY_ADD",
        "BINARY_SUB",
        "BINARY_MUL",
        "BINARY_DIV",
        "COMPARE_OP",
        "BINARY_SUBSCR",
        "BUILD_LIST",
        "BUILD_MAP",
        "MAKE_FUNCTION",
        "CALL",
        "IMPORT_NAME",
        "THROW",
        "PUSH_TRY",
        "END_TRY_BLOCK",
        "END_CATCH_BLOCK",
        "BEGIN_FINALLY",
        "END_FINALLY",
        "AWAIT",
    }
)


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


def validate_program_dict(
    payload: dict[str, object],
    *,
    strict: bool = False,
    exigir_metadados: bool = False,
    validar_opcodes: bool = False,
) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Bytecode inválido: JSON raiz deve ser objeto.")

    allowed = {"entry", "functions", "metadados"}
    if strict:
        unknown = sorted(set(payload.keys()) - allowed)
        if unknown:
            raise ValueError(f"Bytecode inválido: campos desconhecidos no topo: {', '.join(unknown)}")

    if "entry" not in payload:
        raise ValueError("Bytecode inválido: campo 'entry' ausente.")
    if "functions" not in payload:
        raise ValueError("Bytecode inválido: campo 'functions' ausente.")

    metadados = payload.get("metadados")
    if exigir_metadados and metadados is None:
        raise ValueError("Bytecode inválido: campo 'metadados' é obrigatório neste modo.")
    if metadados is not None:
        _validate_metadados_dict(metadados)

    _validate_function_payload(payload["entry"], nome_campo="entry", validar_opcodes=validar_opcodes)
    functions_payload = payload["functions"]
    if not isinstance(functions_payload, dict):
        raise ValueError("Bytecode inválido: campo 'functions' deve ser objeto.")
    for key, raw_fn in functions_payload.items():
        if not isinstance(key, str):
            raise ValueError("Bytecode inválido: chave de função deve ser texto.")
        _validate_function_payload(raw_fn, nome_campo=f"functions.{key}", validar_opcodes=validar_opcodes)


def _validate_metadados_dict(metadados: object) -> None:
    if not isinstance(metadados, dict):
        raise ValueError("Bytecode inválido: campo 'metadados' deve ser objeto.")

    formato = metadados.get("formato")
    if formato is not None and str(formato) != BYTECODE_FORMATO_V1:
        raise ValueError(
            f"Bytecode inválido: formato '{formato}' não suportado; esperado '{BYTECODE_FORMATO_V1}'."
        )

    abi = metadados.get("abi_vm")
    if abi is not None and str(abi) != ABI_VM_V1:
        raise ValueError(f"Bytecode inválido: ABI '{abi}' não suportada; esperada '{ABI_VM_V1}'.")

    versao = metadados.get("versao_serializacao")
    if versao is not None and int(versao) != VERSAO_SERIALIZACAO_V1:
        raise ValueError(
            "Bytecode inválido: versao_serializacao incompatível para v1 "
            f"(esperado {VERSAO_SERIALIZACAO_V1})."
        )


def _validate_function_payload(
    payload: object,
    *,
    nome_campo: str,
    validar_opcodes: bool,
) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"Bytecode inválido: campo '{nome_campo}' deve ser objeto.")

    required = {"name", "params", "is_async", "instructions"}
    missing = sorted(required - set(payload.keys()))
    if missing:
        raise ValueError(f"Bytecode inválido: função '{nome_campo}' sem campos obrigatórios: {', '.join(missing)}")

    if not isinstance(payload["name"], str):
        raise ValueError(f"Bytecode inválido: '{nome_campo}.name' deve ser texto.")
    if not isinstance(payload["params"], list) or any(not isinstance(p, str) for p in payload["params"]):
        raise ValueError(f"Bytecode inválido: '{nome_campo}.params' deve ser lista de texto.")
    if not isinstance(payload["is_async"], bool):
        raise ValueError(f"Bytecode inválido: '{nome_campo}.is_async' deve ser booleano.")
    instructions = payload["instructions"]
    if not isinstance(instructions, list):
        raise ValueError(f"Bytecode inválido: '{nome_campo}.instructions' deve ser lista.")

    for index, instr in enumerate(instructions):
        if not isinstance(instr, dict):
            raise ValueError(f"Bytecode inválido: '{nome_campo}.instructions[{index}]' deve ser objeto.")
        if "op" not in instr:
            raise ValueError(f"Bytecode inválido: '{nome_campo}.instructions[{index}].op' ausente.")
        if "arg" not in instr:
            raise ValueError(f"Bytecode inválido: '{nome_campo}.instructions[{index}].arg' ausente.")
        op = instr["op"]
        if not isinstance(op, str) or not op.strip():
            raise ValueError(f"Bytecode inválido: '{nome_campo}.instructions[{index}].op' deve ser texto.")
        if validar_opcodes and op not in OPCODES_V1:
            raise ValueError(f"Bytecode inválido: opcode não suportado no v1: {op}.")


def function_from_dict(payload: dict[str, object]) -> FunctionCode:
    name = str(payload.get("name", ""))
    params = [str(p) for p in payload.get("params", [])]
    is_async = bool(payload.get("is_async", False))
    raw_instructions = payload.get("instructions", [])
    instructions: list[Instruction] = []
    for raw in raw_instructions if isinstance(raw_instructions, list) else []:
        if not isinstance(raw, dict):
            continue
        instructions.append(Instruction(op=str(raw.get("op", "")), arg=raw.get("arg")))
    return FunctionCode(name=name, params=params, is_async=is_async, instructions=instructions)


def program_from_dict(
    payload: dict[str, object],
    *,
    validar: bool = False,
    validar_opcodes: bool = False,
) -> BytecodeProgram:
    if validar:
        validate_program_dict(payload, strict=False, validar_opcodes=validar_opcodes)

    entry_payload = payload.get("entry")
    if not isinstance(entry_payload, dict):
        raise ValueError("Bytecode inválido: campo 'entry' ausente.")
    entry = function_from_dict(entry_payload)
    functions_payload = payload.get("functions", {})
    functions: dict[str, FunctionCode] = {}
    if isinstance(functions_payload, dict):
        for key, raw_fn in functions_payload.items():
            if isinstance(raw_fn, dict):
                functions[str(key)] = function_from_dict(raw_fn)
    return BytecodeProgram(entry=entry, functions=functions)


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
