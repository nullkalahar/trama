from __future__ import annotations

import time

from trama import cache_runtime


def test_cache_ttl_invalida_padrao_stats() -> None:
    cache_runtime.cache_limpar()
    cache_runtime.cache_definir("usuarios:1", {"id": 1}, ttl_segundos=0.05)
    cache_runtime.cache_definir("usuarios:2", {"id": 2}, ttl_segundos=1.0)
    assert cache_runtime.cache_existe("usuarios:1") is True
    time.sleep(0.07)
    assert cache_runtime.cache_obter("usuarios:1") is None
    removidos = cache_runtime.cache_invalidar_padrao("usuarios:*")
    assert removidos == 1
    st = cache_runtime.cache_stats()
    assert st["hits"] >= 1
    assert st["misses"] >= 1
    assert st["expirados"] >= 1


def test_cache_aquecer_varios_formatos() -> None:
    cache_runtime.cache_limpar()
    total = cache_runtime.cache_aquecer({"a": 1, "b": 2})
    total += cache_runtime.cache_aquecer([{"chave": "c", "valor": 3}, ("d", 4, 10.0)])
    assert total == 4
    assert cache_runtime.cache_obter("a") == 1
    assert cache_runtime.cache_obter("b") == 2
    assert cache_runtime.cache_obter("c") == 3
    assert cache_runtime.cache_obter("d") == 4
