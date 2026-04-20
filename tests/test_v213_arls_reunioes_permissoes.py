from __future__ import annotations

from pathlib import Path

from trama.vm import run_source


def test_v213_presenca_por_chanceler_e_cargo_oficial() -> None:
    raiz = Path(__file__).resolve().parents[1]
    base = raiz / "exemplos" / "v213" / "arls_amm_trm"
    script = base / "_tmp_teste_reuniao_permissoes.trm"
    codigo = (
        'importe "mod_estado.trm" como estado_mod\n'
        'importe "mod_reunioes.trm" como reunioes\n'
        'função principal()\n'
        '    estado = estado_mod["novo_estado"]()\n'
        '    reunioes["reuniao_criar"](estado, {"id": "r1", "data_hora": "2026-04-20T20:00:00-03:00", "grau": "mestre", "titulo": "Sessao"})\n'
        '    r1 = reunioes["presenca_definir_por_chanceler"](estado, {"cargo": "secretario"}, "r1", "obr_1", "presente", "Chanceler")\n'
        '    r2 = reunioes["presenca_definir_por_chanceler"](estado, {"cargo": "chanceler"}, "r1", "obr_1", "presente", "Cargo Inventado")\n'
        '    r3 = reunioes["presenca_definir_por_chanceler"](estado, {"cargo": "chanceler"}, "r1", "obr_1", "presente", "Chanceler")\n'
        '    rem = reunioes["reuniao_remover"](estado, "r1")\n'
        '    det = reunioes["reuniao_detalhar"](estado, "r1")\n'
        '    retorne {"negado": r1, "cargo_invalido": r2, "ok": r3, "remocao": rem, "detalhe": det}\n'
        'fim\n'
    )
    script.write_text(codigo, encoding="utf-8")
    try:
        out = run_source(codigo, source_path=str(script))
    finally:
        script.unlink(missing_ok=True)

    assert isinstance(out, dict)
    negado = dict(out.get("negado") or {})
    invalido = dict(out.get("cargo_invalido") or {})
    ok = dict(out.get("ok") or {})
    remocao = dict(out.get("remocao") or {})
    detalhe = dict(out.get("detalhe") or {})

    assert negado.get("ok") is False
    assert dict(negado.get("erro") or {}).get("codigo") == "PERMISSAO_NEGADA"

    assert invalido.get("ok") is False
    assert dict(invalido.get("erro") or {}).get("codigo") == "CARGO_INVALIDO"

    assert ok.get("ok") is True
    assert str(dict(ok.get("dados") or {}).get("cargo_ocupado")) == "Chanceler"

    assert remocao.get("ok") is True
    assert detalhe.get("ok") is True
    reuniao = dict(dict(detalhe.get("dados") or {}).get("reuniao") or {})
    assert reuniao.get("status") == "cancelada"
    assert reuniao.get("removida") is True
