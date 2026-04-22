from __future__ import annotations

import pytest

from trama import realtime_core
from trama import realtime_fallback_http
from trama import realtime_websocket


def test_v211_factory_backplane_memoria_basico() -> None:
    bp = realtime_core.criar_backplane_tempo_real(tipo="memoria", grupo="g_teste_mod")
    seq = bp.publicar_evento("evt", {"ok": True}, "n1")
    assert int(seq) >= 1
    eventos = bp.coletar_eventos(0)
    assert len(eventos) >= 1
    assert eventos[-1].tipo == "evt"


def test_v211_factory_backplane_invalido() -> None:
    with pytest.raises(ValueError, match="backplane de tempo real invalido|backplane de tempo real inválido"):
        _ = realtime_core.criar_backplane_tempo_real(tipo="xpto", grupo="g_teste_mod")


def test_v211_fallback_http_nao_ativo_retorna_false() -> None:
    class _TempoReal:
        fallback_ativo = False
        fallback_prefixo = "/tempo-real/fallback"

    class _App:
        tempo_real = _TempoReal()

    class _Ctx:
        def _read_body(self):
            return b"", {}, {}, {}, None

        def _send_json(self, _status, _payload, _headers):
            raise AssertionError("nao deveria enviar resposta quando fallback nao esta ativo")

    ok = realtime_fallback_http.processar_fallback_tempo_real_http(
        _Ctx(),
        app=_App(),
        path="/tempo-real/fallback/status",
        query={},
        headers_map={},
        invocar_sync=lambda fn, args: fn(*args),
        processar_mensagem=lambda c, m, i, info: None,
    )
    assert ok is False


def test_v211_websocket_sem_upgrade_retorna_false() -> None:
    class _TempoReal:
        def rota_info(self, _path):
            return {"handler": None, "opcoes": {}}

    class _App:
        tempo_real = _TempoReal()

    class _Ctx:
        client_address = ("127.0.0.1", 9999)
        connection = object()

        def _send_json(self, _status, _payload, _headers):
            raise AssertionError("nao deveria enviar resposta sem upgrade websocket")

    ok = realtime_websocket.processar_upgrade_websocket_tempo_real(
        _Ctx(),
        app=_App(),
        path="/ws/x",
        query={},
        headers_map={"upgrade": "", "connection": "keep-alive"},
        invocar_sync=lambda fn, args: fn(*args),
        processar_mensagem=lambda c, m, i, info: None,
    )
    assert ok is False
