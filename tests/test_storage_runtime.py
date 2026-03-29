from __future__ import annotations

from pathlib import Path

from trama import storage_runtime


def test_storage_local_put_get_list_delete(tmp_path: Path) -> None:
    st = storage_runtime.LocalStorage(tmp_path / "storage")
    out = st.put("avatars/u1.txt", "conteudo")
    assert out["ok"] is True
    assert out["size"] == 8

    got = st.get("avatars/u1.txt")
    assert got["size"] == 8
    assert got["bytes"] == b"conteudo"

    listed = st.list("avatars/")
    assert listed == ["avatars/u1.txt"]

    assert st.delete("avatars/u1.txt") is True
    assert st.delete("avatars/u1.txt") is False


def test_storage_local_block_path_traversal(tmp_path: Path) -> None:
    st = storage_runtime.LocalStorage(tmp_path / "base")
    try:
        st.put("../fora.txt", "x")
    except storage_runtime.StorageError:
        pass
    else:
        raise AssertionError("esperava StorageError para path traversal")
