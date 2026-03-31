from __future__ import annotations

import json
import pytest

from trama.bytecode import (
    BYTECODE_FORMATO_V1,
    ABI_VM_V1,
    VERSAO_SERIALIZACAO_V1,
    BytecodeProgram,
    program_from_dict,
    program_to_dict,
    validate_program_dict,
)
from trama.compiler import compile_source
from trama.vm import VMError, run_bytecode_dict


def _assert_function_shape(fn: dict[str, object]) -> None:
    assert isinstance(fn.get("name"), str)
    assert isinstance(fn.get("params"), list)
    assert isinstance(fn.get("is_async"), bool)
    assert isinstance(fn.get("instructions"), list)
    for instr in fn["instructions"]:  # type: ignore[index]
        assert isinstance(instr, dict)
        assert "op" in instr
        assert "arg" in instr


def test_bytecode_v1_envelope_shape() -> None:
    program = compile_source("função principal()\n    retorne 1\nfim\n")
    payload = program_to_dict(program)

    assert set(payload.keys()) == {"entry", "functions"}
    assert isinstance(payload["entry"], dict)
    assert isinstance(payload["functions"], dict)

    _assert_function_shape(payload["entry"])  # type: ignore[arg-type]
    for fn in payload["functions"].values():  # type: ignore[union-attr]
        _assert_function_shape(fn)  # type: ignore[arg-type]


def test_bytecode_v1_roundtrip_stability() -> None:
    codigo = (
        "função soma(a, b)\n"
        "    retorne a + b\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    xs = [1, 2]\n"
        "    cfg = {\"k\": 10}\n"
        "    se xs[0] < cfg[\"k\"]\n"
        "        retorne aguarde soma(20, 22)\n"
        "    senão\n"
        "        retorne 0\n"
        "    fim\n"
        "fim\n"
    )
    compiled = compile_source(codigo)
    payload = program_to_dict(compiled)
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    reloaded = program_from_dict(normalized)

    assert isinstance(reloaded, BytecodeProgram)
    assert program_to_dict(reloaded) == normalized


def test_bytecode_v1_valida_com_metadados() -> None:
    payload = program_to_dict(compile_source("função principal()\n    retorne 7\nfim\n"))
    payload["metadados"] = {
        "formato": BYTECODE_FORMATO_V1,
        "abi_vm": ABI_VM_V1,
        "versao_serializacao": VERSAO_SERIALIZACAO_V1,
    }
    validate_program_dict(payload, strict=True, exigir_metadados=True, validar_opcodes=True)


def test_bytecode_v1_rejeita_metadados_com_versao_invalida() -> None:
    payload = program_to_dict(compile_source("função principal()\n    retorne 7\nfim\n"))
    payload["metadados"] = {
        "formato": "bytecode_v2",
        "abi_vm": ABI_VM_V1,
        "versao_serializacao": VERSAO_SERIALIZACAO_V1,
    }
    with pytest.raises(ValueError, match="formato"):
        validate_program_dict(payload, strict=True, exigir_metadados=True)


def test_bytecode_v1_rejeita_opcode_invalido_na_conformidade() -> None:
    payload = program_to_dict(compile_source("função principal()\n    retorne 7\nfim\n"))
    payload["entry"]["instructions"][0]["op"] = "OP_INVALIDA"  # type: ignore[index]
    with pytest.raises(ValueError, match="opcode"):
        validate_program_dict(payload, validar_opcodes=True)


def test_bytecode_v1_rejeita_estrutura_malformada() -> None:
    payload = {
        "entry": {
            "name": "__entry__",
            "params": [],
            "is_async": False,
            "instructions": [{"op": "HALT"}],  # sem arg
        },
        "functions": {},
    }
    with pytest.raises(ValueError, match="arg"):
        validate_program_dict(payload)


def test_vm_rejeita_bytecode_malformado_antes_da_execucao() -> None:
    payload = {"entry": {"name": "__entry__"}, "functions": {}}
    with pytest.raises(ValueError, match="campos obrigatórios"):
        run_bytecode_dict(payload)


def test_vm_rejeita_opcode_desconhecido_em_tempo_de_execucao() -> None:
    payload = {
        "entry": {
            "name": "__entry__",
            "params": [],
            "is_async": False,
            "instructions": [{"op": "INEXISTENTE", "arg": None}],
        },
        "functions": {},
    }
    with pytest.raises(VMError, match="Instrução desconhecida"):
        run_bytecode_dict(payload)
