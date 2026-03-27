from __future__ import annotations

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


def test_closure_funciona() -> None:
    codigo = (
        "função principal()\n"
        "    base = 10\n"
        "    função soma_local(x)\n"
        "        retorne x + base\n"
        "    fim\n"
        "    exibir(soma_local(5))\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["15"]


def test_tente_pegue_finalmente() -> None:
    codigo = (
        "função principal()\n"
        "    tente\n"
        "        lance \"erro\"\n"
        "    pegue e\n"
        "        exibir(e)\n"
        "    finalmente\n"
        "        exibir(\"fim\")\n"
        "    fim\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["erro", "fim"]


def test_tente_finalmente_repropaga() -> None:
    codigo = (
        "função principal()\n"
        "    tente\n"
        "        lance \"x\"\n"
        "    finalmente\n"
        "        exibir(\"sempre\")\n"
        "    fim\n"
        "fim\n"
    )
    with pytest.raises(VMError, match="Exceção não tratada"):
        run_source(codigo)


def test_colecoes_e_json() -> None:
    codigo = (
        "função principal()\n"
        "    dados = {\"nome\": \"ana\", \"nums\": [1, 2, 3]}\n"
        "    txt = json_stringify(dados)\n"
        "    obj = json_parse(txt)\n"
        "    exibir(obj[\"nome\"])\n"
        "    exibir(obj[\"nums\"][1])\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["ana", "2"]


def test_importe_modulo(tmp_path) -> None:
    mod = tmp_path / "mathx.trm"
    mod.write_text(
        "função dobro(x)\n"
        "    retorne x * 2\n"
        "fim\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.trm"
    main.write_text(
        "importe mathx como m\n"
        "função principal()\n"
        "    exibir(m[\"dobro\"](21))\n"
        "fim\n",
        encoding="utf-8",
    )

    out: list[str] = []
    result = run_source(main.read_text(encoding="utf-8"), print_fn=out.append, source_path=str(main))
    assert result is None
    assert out == ["42"]


def test_erro_break_fora_de_laco() -> None:
    with pytest.raises(CompileError, match="dentro de laço"):
        compile_source("pare\n")


def test_erro_nome_nao_definido() -> None:
    with pytest.raises(VMError, match="Nome não definido"):
        run_source("função principal()\nexibir(x)\nfim\n")


def test_assincrona_e_aguarde_basico() -> None:
    codigo = (
        "assíncrona função dobro_async(x)\n"
        "    retorne x * 2\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    valor = aguarde dobro_async(21)\n"
        "    exibir(valor)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["42"]


def test_tarefas_timeout_cancelamento() -> None:
    codigo = (
        "assíncrona função demorado()\n"
        "    aguarde dormir(0.05)\n"
        "    retorne 99\n"
        "fim\n"
        "assíncrona função principal()\n"
        "    t1 = criar_tarefa(demorado())\n"
        "    t2 = criar_tarefa(demorado())\n"
        "    cancelar_tarefa(t2)\n"
        "    tente\n"
        "        valor = aguarde com_timeout(t1, 1.0)\n"
        "        exibir(valor)\n"
        "    pegue erro\n"
        "        exibir(\"falhou\")\n"
        "    fim\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["99"]


def test_io_nao_bloqueante(tmp_path) -> None:
    arquivo = tmp_path / "async_io.txt"
    codigo = (
        "assíncrona função principal()\n"
        f"    aguarde escrever_texto_async(\"{arquivo}\", \"ola async\")\n"
        f"    conteudo = aguarde ler_texto_async(\"{arquivo}\")\n"
        "    exibir(conteudo)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["ola async"]
