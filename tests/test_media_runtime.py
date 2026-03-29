from __future__ import annotations

from pathlib import Path

from trama import media_runtime


def test_media_gzip_pipeline_basico(tmp_path: Path) -> None:
    raw = b"abc" * 100
    gz = media_runtime.midia_comprimir_gzip(raw, nivel=6)
    out = media_runtime.midia_descomprimir_gzip(gz)
    assert out == raw

    saved = media_runtime.midia_salvar_arquivo(str(tmp_path / "a.bin"), raw)
    assert saved["ok"] is True
    loaded = media_runtime.midia_ler_arquivo(str(tmp_path / "a.bin"))
    assert loaded == raw

    pipe = media_runtime.midia_pipeline(raw, {"comprimir_gzip": True, "nivel_gzip": 6})
    assert pipe["ok"] is True
    assert "gzip" in pipe["meta"]["etapas"]


def test_media_imagem_sem_pillow_falha_controlada() -> None:
    if media_runtime.Image is not None:
        return
    try:
        _ = media_runtime.midia_redimensionar_imagem(b"x", 10, 10)
    except media_runtime.MediaError:
        pass
    else:
        raise AssertionError("esperava MediaError quando Pillow não está disponível")
