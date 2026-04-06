from __future__ import annotations

import os
from pathlib import Path

import pytest

from trama.ast_nodes import AssignStmt, ExportStmt, ForStmt, FunctionDecl, ImportStmt, TypeRef
from trama.compiler import CompileError, compile_source
from trama.parser import parse
from trama.vm import run_source


def _run_capture(codigo: str, source_path: str | None = None) -> tuple[object, list[str]]:
    out: list[str] = []
    result = run_source(codigo, print_fn=out.append, source_path=source_path)
    return result, out


def test_v211_parser_para_em_contratos_e_tipagem() -> None:
    codigo = (
        'importe "util/matematica.trm" como mat expondo soma, media\n'
        'exporte processar\n'
        'função processar(itens: lista[inteiro]): inteiro\n'
        '    total: inteiro = 0\n'
        '    para item em itens\n'
        '        total = total + item\n'
        '    fim\n'
        '    retorne total\n'
        'fim\n'
    )
    program = parse(codigo)

    imp = program.declarations[0]
    exp = program.declarations[1]
    fn = program.declarations[2]

    assert isinstance(imp, ImportStmt)
    assert imp.module == "util/matematica.trm"
    assert imp.alias == "mat"
    assert imp.names == ["soma", "media"]

    assert isinstance(exp, ExportStmt)
    assert exp.names == ["processar"]

    assert isinstance(fn, FunctionDecl)
    assert fn.param_types is not None
    assert fn.return_type == TypeRef(nome="inteiro", args=[])
    assert fn.param_types["itens"] == TypeRef(nome="lista", args=[TypeRef(nome="inteiro", args=[])])

    ann = fn.body[0]
    loop = fn.body[1]
    assert isinstance(ann, AssignStmt)
    assert ann.annotation == TypeRef(nome="inteiro", args=[])
    assert isinstance(loop, ForStmt)
    assert loop.iterator == "item"


def test_v211_semantica_diagnostico_estavel_com_contexto() -> None:
    codigo = (
        "função dobro(x: inteiro): inteiro\n"
        "    retorne \"texto\"\n"
        "fim\n"
    )
    with pytest.raises(CompileError) as exc:
        compile_source(codigo)

    msg = str(exc.value)
    assert "SEM0204" in msg
    assert "linha=2" in msg
    assert "coluna=5" in msg
    assert "sugestao=" in msg


def test_v211_tipagem_gradual_fases_1_e_2() -> None:
    codigo_ok = (
        "função reduzir(nums: lista[inteiro]): inteiro\n"
        "    total: inteiro = 0\n"
        "    para n em nums\n"
        "        total = total + n\n"
        "    fim\n"
        "    retorne total\n"
        "fim\n"
    )
    compile_source(codigo_ok)

    codigo_fail = (
        "função dobro(x: inteiro): inteiro\n"
        "    retorne x * 2\n"
        "fim\n"
        "função principal()\n"
        "    exibir(dobro(\"a\"))\n"
        "fim\n"
    )
    with pytest.raises(CompileError, match="SEM0203"):
        compile_source(codigo_fail)


def test_v211_vm_para_em_execucao() -> None:
    codigo = (
        "função principal()\n"
        "    dados = [1, 2, 3, 4]\n"
        "    soma = 0\n"
        "    para item em dados\n"
        "        soma = soma + item\n"
        "    fim\n"
        "    exibir(soma)\n"
        "fim\n"
    )
    _, out = _run_capture(codigo)
    assert out == ["10"]


def test_v211_vm_import_export_expondo(tmp_path: Path) -> None:
    root = tmp_path
    mod_dir = root / "mods"
    mod_dir.mkdir(parents=True, exist_ok=True)

    modulo = mod_dir / "mat.trm"
    modulo.write_text(
        (
            "exporte soma\n"
            "interno = 99\n"
            "função soma(a: inteiro, b: inteiro): inteiro\n"
            "    retorne a + b\n"
            "fim\n"
        ),
        encoding="utf-8",
    )

    app = root / "app.trm"
    app.write_text(
        (
            'importe "mods/mat.trm" como mat expondo soma\n'
            "função principal()\n"
            "    ch = mapa_chaves(mat)\n"
            "    exibir(tamanho(ch))\n"
            "    exibir(mat[\"soma\"](2, 8))\n"
            "fim\n"
        ),
        encoding="utf-8",
    )

    _, out = _run_capture(app.read_text(encoding="utf-8"), source_path=str(app))
    assert out == ["1", "10"]


def test_v211_resolucao_modulo_deterministica_com_modpath(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raiz_a = tmp_path / "a"
    raiz_b = tmp_path / "b"
    (raiz_a / "pac").mkdir(parents=True)
    (raiz_b / "pac").mkdir(parents=True)

    (raiz_a / "pac" / "mod.trm").write_text(
        "exporte valor\nvalor = \"A\"\n",
        encoding="utf-8",
    )
    (raiz_b / "pac" / "mod.trm").write_text(
        "exporte valor\nvalor = \"B\"\n",
        encoding="utf-8",
    )

    app = tmp_path / "app.trm"
    app.write_text(
        (
            'importe "pac" como m expondo valor\n'
            "função principal()\n"
            "    exibir(m[\"valor\"])\n"
            "fim\n"
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("TRAMA_MODPATH", os.pathsep.join([str(raiz_b), str(raiz_a)]))
    _, out = _run_capture(app.read_text(encoding="utf-8"), source_path=str(app))
    assert out == ["B"]


def test_v211_for_em_invalido_dispara_erro_semantico() -> None:
    codigo = (
        "função principal()\n"
        "    para i em 10\n"
        "        exibir(i)\n"
        "    fim\n"
        "fim\n"
    )
    with pytest.raises(CompileError, match="SEM0306"):
        compile_source(codigo)
