from __future__ import annotations

import threading
import time

from trama import cache_runtime


def test_v204_invalidez_remota_por_chave() -> None:
    a = cache_runtime.cache_distribuido_criar(grupo="g1", id_instancia="a", auto_sincronizar=False)
    b = cache_runtime.cache_distribuido_criar(grupo="g1", id_instancia="b", auto_sincronizar=False)
    cache_runtime.cache_distribuido_limpar(instancia=a)
    cache_runtime.cache_distribuido_limpar(instancia=b)

    cache_runtime.cache_distribuido_definir("k1", {"v": 1}, namespace="n1", instancia=a)
    cache_runtime.cache_distribuido_sincronizar(instancia=b)
    assert cache_runtime.cache_distribuido_obter("k1", namespace="n1", instancia=b)["v"] == 1

    cache_runtime.cache_distribuido_invalidar_chave("k1", namespace="n1", instancia=a)
    cache_runtime.cache_distribuido_sincronizar(instancia=b)
    assert cache_runtime.cache_distribuido_obter("k1", None, namespace="n1", instancia=b) is None


def test_v204_invalidez_remota_por_padrao() -> None:
    a = cache_runtime.cache_distribuido_criar(grupo="g2", id_instancia="a", auto_sincronizar=False)
    b = cache_runtime.cache_distribuido_criar(grupo="g2", id_instancia="b", auto_sincronizar=False)
    cache_runtime.cache_distribuido_limpar(instancia=a)
    cache_runtime.cache_distribuido_limpar(instancia=b)

    cache_runtime.cache_distribuido_definir("u:1", 1, namespace="n1", instancia=a)
    cache_runtime.cache_distribuido_definir("u:2", 2, namespace="n1", instancia=a)
    cache_runtime.cache_distribuido_sincronizar(instancia=b)

    assert cache_runtime.cache_distribuido_invalidar_padrao("u:*", namespace="n1", instancia=a) == 2
    cache_runtime.cache_distribuido_sincronizar(instancia=b)
    assert cache_runtime.cache_distribuido_obter("u:1", None, namespace="n1", instancia=b) is None
    assert cache_runtime.cache_distribuido_obter("u:2", None, namespace="n1", instancia=b) is None


def test_v204_ttl_multino_sem_regressao() -> None:
    a = cache_runtime.cache_distribuido_criar(grupo="g3", id_instancia="a", auto_sincronizar=True)
    b = cache_runtime.cache_distribuido_criar(grupo="g3", id_instancia="b", auto_sincronizar=True)
    cache_runtime.cache_distribuido_limpar(instancia=a)
    cache_runtime.cache_distribuido_limpar(instancia=b)

    cache_runtime.cache_distribuido_definir("sessao:1", {"id": 1}, ttl_segundos=0.05, namespace="n", instancia=a)
    assert cache_runtime.cache_distribuido_obter("sessao:1", None, namespace="n", instancia=b)["id"] == 1
    time.sleep(0.07)
    assert cache_runtime.cache_distribuido_obter("sessao:1", None, namespace="n", instancia=a) is None
    assert cache_runtime.cache_distribuido_obter("sessao:1", None, namespace="n", instancia=b) is None


def test_v204_stampede_coalescencia_lider_unico() -> None:
    inst = cache_runtime.cache_distribuido_criar(grupo="g4", id_instancia="coalesce", auto_sincronizar=True)
    cache_runtime.cache_distribuido_limpar(instancia=inst)

    lock = threading.Lock()
    calls = {"n": 0}

    def loader() -> dict[str, int]:
        with lock:
            calls["n"] += 1
        time.sleep(0.05)
        return {"valor": 99}

    out: list[object] = []

    def worker() -> None:
        v = cache_runtime.cache_distribuido_obter_ou_carregar(
            "k",
            loader,
            ttl_segundos=1.0,
            namespace="n",
            timeout_coalescencia_segundos=0.2,
            instancia=inst,
        )
        out.append(v)

    ths = [threading.Thread(target=worker) for _ in range(8)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()

    assert calls["n"] == 1
    assert len(out) == 8
    assert all(isinstance(x, dict) and x.get("valor") == 99 for x in out)

    st = cache_runtime.cache_distribuido_stats(namespace="n", instancia=inst)
    assert st["coalescencia_lider"] == 1
    assert st["coalescencia_espera"] >= 1


def test_v204_stampede_sem_lock_em_fluxo_manual() -> None:
    inst = cache_runtime.cache_distribuido_criar(grupo="g4b", id_instancia="sem_lock", auto_sincronizar=True)
    cache_runtime.cache_distribuido_limpar(instancia=inst)

    lock = threading.Lock()
    calls = {"n": 0}
    barreira = threading.Barrier(8)
    out: list[object] = []

    def loader_manual() -> dict[str, int]:
        with lock:
            calls["n"] += 1
        time.sleep(0.03)
        return {"valor": 7}

    def worker() -> None:
        barreira.wait()
        atual = cache_runtime.cache_distribuido_obter("manual", None, namespace="n", instancia=inst)
        if atual is None:
            atual = loader_manual()
            cache_runtime.cache_distribuido_definir("manual", atual, ttl_segundos=1.0, namespace="n", instancia=inst)
        out.append(atual)

    ths = [threading.Thread(target=worker) for _ in range(8)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()

    assert len(out) == 8
    assert all(isinstance(x, dict) and x.get("valor") == 7 for x in out)
    assert calls["n"] > 1


def test_v204_fallback_backend_indisponivel() -> None:
    inst = cache_runtime.cache_distribuido_criar(grupo="g5", id_instancia="fallback", auto_sincronizar=True)
    cache_runtime.cache_distribuido_limpar(instancia=inst)
    cache_runtime.cache_distribuido_configurar_backplane("g5", disponivel=False)

    try:
        valor = cache_runtime.cache_distribuido_obter_ou_carregar(
            "fx",
            lambda: {"ok": True},
            ttl_segundos=0.5,
            namespace="n",
            fallback={"ok": False},
            instancia=inst,
        )
        # mesmo com backend fora, não deve interromper fluxo
        assert valor in ({"ok": True}, {"ok": False})
        st = cache_runtime.cache_distribuido_stats(namespace="n", instancia=inst)
        assert st["falhas_backend"] >= 1
    finally:
        cache_runtime.cache_distribuido_configurar_backplane("g5", disponivel=True)


def test_v204_metricas_hit_ratio_latencia_invalidez() -> None:
    inst = cache_runtime.cache_distribuido_criar(grupo="g6", id_instancia="met", auto_sincronizar=True)
    cache_runtime.cache_distribuido_limpar(instancia=inst)

    cache_runtime.cache_distribuido_definir("a", 1, namespace="n", instancia=inst)
    assert cache_runtime.cache_distribuido_obter("a", None, namespace="n", instancia=inst) == 1
    assert cache_runtime.cache_distribuido_obter("x", None, namespace="n", instancia=inst) is None
    cache_runtime.cache_distribuido_invalidar_chave("a", namespace="n", instancia=inst)

    st = cache_runtime.cache_distribuido_stats(namespace="n", instancia=inst)
    assert st["hits"] >= 1
    assert st["misses"] >= 1
    assert 0.0 <= float(st["hit_ratio"]) <= 1.0
    assert st["invalidacoes_locais"] >= 1
    assert "obter" in st["latencias"]
