import pytest

from trama.compiler import CompileError, compile_source
from trama.vm import VMError, run_source


def _run_capture(codigo: str) -> tuple[object, list[str]]:
    out: list[str] = []
    result = run_source(codigo, print_fn=out.append)
    return result, out


def test_execucao_principal_e_exibir() -> None:
    codigo = (
        "função principal()\n"
        "    exibir(\"Olá\")\n"
        "fim\n"
    )
    result, out = _run_capture(codigo)
    assert result is None
    assert out == ["Olá"]


def test_precedencia_aritmetica() -> None:
    codigo = (
        "função principal()\n"
        "    exibir(1 + 2 * 3)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["7"]


def test_if_senao_sem_acento() -> None:
    codigo = (
        "função principal()\n"
        "    se verdadeiro\n"
        "        exibir(\"ok\")\n"
        "    senao\n"
        "        exibir(\"falha\")\n"
        "    fim\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["ok"]


def test_while_com_continue_e_pare() -> None:
    codigo = (
        "função principal()\n"
        "    i = 0\n"
        "    enquanto i < 10\n"
        "        i = i + 1\n"
        "        se i == 3\n"
        "            continue\n"
        "        fim\n"
        "        se i == 5\n"
        "            pare\n"
        "        fim\n"
        "        exibir(i)\n"
        "    fim\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["1", "2", "4"]


def test_funcoes_com_retorno() -> None:
    codigo = (
        "função soma(a, b)\n"
        "    retorne a + b\n"
        "fim\n"
        "função principal()\n"
        "    exibir(soma(10, 20))\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["30"]


def test_erro_break_fora_de_laco() -> None:
    with pytest.raises(CompileError, match="fora de um laço"):
        compile_source("pare\n")


def test_erro_nome_nao_definido() -> None:
    with pytest.raises(VMError, match="Nome não definido"):
        run_source("função principal()\nexibir(x)\nfim\n")
