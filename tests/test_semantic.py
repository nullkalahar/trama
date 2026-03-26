import pytest

from trama.compiler import CompileError, compile_source


def test_retorne_fora_de_funcao() -> None:
    with pytest.raises(CompileError, match="retorne"):
        compile_source("retorne 1\n")


def test_pare_fora_de_laco() -> None:
    with pytest.raises(CompileError, match="pare"):
        compile_source("pare\n")


def test_continue_fora_de_laco() -> None:
    with pytest.raises(CompileError, match="continue"):
        compile_source("continue\n")


def test_aridade_funcao_incorreta() -> None:
    codigo = (
        "função soma(a, b)\n"
        "    retorne a + b\n"
        "fim\n"
        "função principal()\n"
        "    exibir(soma(1))\n"
        "fim\n"
    )
    with pytest.raises(CompileError, match="esperava 2 argumentos"):
        compile_source(codigo)


def test_funcao_aninhada_nao_suportada_v0_1() -> None:
    codigo = (
        "função principal()\n"
        "    função interna()\n"
        "        retorne 1\n"
        "    fim\n"
        "    exibir(interna())\n"
        "fim\n"
    )
    with pytest.raises(CompileError, match="Funções aninhadas"):
        compile_source(codigo)
