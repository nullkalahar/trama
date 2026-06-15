from __future__ import annotations

from pathlib import Path

from trama import media_runtime
from trama import storage_runtime


def test_v231_pipeline_upload_com_validacao_e_promocao(tmp_path: Path) -> None:
    st = storage_runtime.LocalStorage(tmp_path / "storage")
    st.definir_politicas({"visibilidade": "privado", "lifecycle_dias": 30})
    conteudo = b"ola storage"
    sha = storage_runtime._sha256(conteudo)

    up = st.iniciar_upload(
        "docs/ola.txt",
        content_type="text/plain",
        validacao={"mime_permitidos": ["text/plain"], "tamanho_maximo": 64, "hash_sha256": sha},
        metadata={"origem": "teste"},
        politicas={"retencao_ate": "2026-12-31T00:00:00Z"},
    )
    assert up["ok"] is True
    st.escrever_upload(str(up["upload_id"]), conteudo[:4])
    st.escrever_upload(str(up["upload_id"]), conteudo[4:])
    out = st.finalizar_upload(str(up["upload_id"]))

    assert out["ok"] is True
    assert out["key"] == "docs/ola.txt"
    got = st.get("docs/ola.txt")
    assert got["bytes"] == conteudo
    assert got["metadata"]["origem"] == "teste"
    assert got["politicas"]["visibilidade"] == "privado"
    assert got["politicas"]["retencao_ate"] == "2026-12-31T00:00:00Z"


def test_v234_politicas_e_url_assinada(tmp_path: Path) -> None:
    st = storage_runtime.LocalStorage(tmp_path / "storage", politicas_padrao={"visibilidade": "publico", "lifecycle_dias": 7})
    st.put("publicos/a.txt", "abc", content_type="text/plain")
    meta = st.obter_metadados("publicos/a.txt")
    url = st.url_assinada("publicos/a.txt", expira_em=120, operacao="baixar")

    assert meta["politicas"]["visibilidade"] == "publico"
    assert meta["politicas"]["lifecycle_dias"] == 7
    assert "assinatura=" in url
    assert "expira_em=" in url


def test_v233_pipeline_midia_integrada_ao_storage(tmp_path: Path) -> None:
    st = storage_runtime.LocalStorage(tmp_path / "storage")
    origem = b"abc" * 200
    st.put("origens/arquivo.bin", origem, content_type="application/octet-stream")

    out = media_runtime.midia_pipeline_storage(
        st,
        "origens/arquivo.bin",
        "midia/arquivo",
        opcoes={
            "variantes": [
                {"nome": "gzip", "opcoes": {"comprimir_gzip": True, "nivel_gzip": 6}, "chave": "midia/arquivo/arquivo.bin.gz"},
                {"nome": "copia", "acao": "copiar", "chave": "midia/arquivo/arquivo.bin"},
            ]
        },
    )

    assert out["ok"] is True
    assert out["total_variantes"] == 2
    assert "midia/arquivo/manifesto.json" in st.list("midia/arquivo")
    gz = st.get("midia/arquivo/arquivo.bin.gz")
    assert gz["metadata"]["variante"] == "gzip"
    assert media_runtime.midia_descomprimir_gzip(gz["bytes"]) == origem
