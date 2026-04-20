from __future__ import annotations

from pathlib import Path

from trama.vm import run_source


def test_v213_fluxo_backend_arls_amm_em_trm() -> None:
    raiz = Path(__file__).resolve().parents[1]
    script = raiz / "exemplos" / "v213" / "arls_amm_trm" / "213_85_backend_arls_amm_fluxo_completo.trm"
    resultado = run_source(script.read_text(encoding="utf-8"), source_path=str(script))
    assert isinstance(resultado, dict)

    login = dict(resultado.get("login") or {})
    refresh = dict(resultado.get("refresh") or {})
    obreiros = dict(resultado.get("obreiros") or {})
    reuniao = dict(resultado.get("reuniao") or {})
    dashboard = dict(resultado.get("dashboard") or {})
    cargos = list(resultado.get("cargos") or [])

    assert login.get("ok") is True
    assert refresh.get("ok") is True
    assert obreiros.get("ok") is True
    assert reuniao.get("ok") is True
    assert dashboard.get("ok") is True
    assert isinstance(resultado.get("reuniao_passou"), bool)
    assert "Chanceler" in cargos

    dados_reuniao = dict(reuniao.get("dados") or {})
    dados_dashboard = dict(dashboard.get("dados") or {})
    resumo_presenca = dict(dados_reuniao.get("presencas_resumo") or {})
    resumo_ativ = dict(dados_reuniao.get("atividades_resumo") or {})
    visitantes = list(dados_reuniao.get("visitantes") or [])
    presencas = list(dados_reuniao.get("presencas") or [])

    assert int(resumo_presenca.get("presente", 0)) == 1
    assert int(resumo_ativ.get("cartoes_visita", 0)) == 3
    assert int(dados_dashboard.get("obreiros_ativos", 0)) == 1
    assert len(visitantes) == 1
    assert len(presencas) == 1
    assert str(dict(presencas[0]).get("cargo_ocupado")) == "Chanceler"
