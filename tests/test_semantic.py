import pytest

from trama.compiler import CompileError, compile_source
from trama.parser import ParseError


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


def test_try_sem_pegue_ou_finalmente_erro() -> None:
    with pytest.raises(ParseError, match="exige 'pegue' e/ou 'finalmente'"):
        compile_source("tente\n    exibir(1)\nfim\n")


def test_funcoes_aninhadas_agora_suportadas() -> None:
    codigo = (
        "função principal()\n"
        "    função interna()\n"
        "        retorne 1\n"
        "    fim\n"
        "    exibir(interna())\n"
        "fim\n"
    )
    compile_source(codigo)


def test_aguarde_fora_de_funcao_assincrona_da_erro() -> None:
    codigo = (
        "função principal()\n"
        "    aguarde dormir(0.01)\n"
        "fim\n"
    )
    with pytest.raises(CompileError, match="assíncrona"):
        compile_source(codigo)
