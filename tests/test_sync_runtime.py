from __future__ import annotations

from trama import sync_runtime


def _reset_sync() -> None:
    sync_runtime._EVENTOS.clear()  # type: ignore[attr-defined]
    sync_runtime._CACHE_OFFLINE.clear()  # type: ignore[attr-defined]


def test_sync_incremental_cache_offline_e_conflito() -> None:
    _reset_sync()
    out1 = sync_runtime.sync_registrar_evento("posts", "p1", "criar", {"titulo": "A"})
    out2 = sync_runtime.sync_registrar_evento("posts", "p1", "atualizar", {"titulo": "B"})
    assert out1["cursor"] == 1
    assert out2["cursor"] == 2

    lote = sync_runtime.sync_consumir("posts", cursor_desde=1, limite=10)
    assert lote["ok"] is True
    assert len(lote["itens"]) == 1
    assert lote["cursor_ate"] == 2
    assert sync_runtime.sync_cursor_atual("posts") == 2

    conflito = sync_runtime.sync_resolver_conflito(
        {"id": "p1", "valor": "local", "atualizado_em": 10},
        {"id": "p1", "valor": "remoto", "atualizado_em": 20},
    )
    assert conflito["ok"] is True
    assert conflito["vencedor"]["valor"] == "remoto"

    save1 = sync_runtime.cache_offline_salvar("feed", "u1", {"itens": [1]})
    save2 = sync_runtime.cache_offline_salvar("feed", "u1", {"itens": [1, 2]})
    assert save1["versao"] == 1
    assert save2["versao"] == 2
    item = sync_runtime.cache_offline_obter("feed", "u1")
    assert item["ok"] is True
    assert item["item"]["versao"] == 2

