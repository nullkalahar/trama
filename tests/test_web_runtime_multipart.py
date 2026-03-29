from __future__ import annotations

import json
from urllib import request

from trama import web_runtime


def _multipart_body(boundary: str, parts: list[tuple[str, str | bytes, str | None]]) -> bytes:
    # parts: (campo, valor, nome_arquivo)
    out = bytearray()
    for field, value, filename in parts:
        out.extend(f"--{boundary}\r\n".encode("utf-8"))
        if filename is None:
            out.extend(f'Content-Disposition: form-data; name="{field}"\r\n\r\n'.encode("utf-8"))
            raw = value if isinstance(value, bytes) else str(value).encode("utf-8")
            out.extend(raw)
            out.extend(b"\r\n")
        else:
            out.extend(
                (
                    f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
                    "Content-Type: application/octet-stream\r\n\r\n"
                ).encode("utf-8")
            )
            raw = value if isinstance(value, bytes) else str(value).encode("utf-8")
            out.extend(raw)
            out.extend(b"\r\n")
    out.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(out)


def test_web_runtime_multipart_upload() -> None:
    app = web_runtime.WebApp()

    def handler(req):
        arq = req["arquivos"]["avatar"][0]
        return {
            "status": 200,
            "json": {
                "ok": True,
                "nome": req["formulario"]["nome"],
                "arquivo": arq["nome_arquivo"],
                "bytes": arq["tamanho"],
            },
        }

    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/upload",
            handler,
            schema={"form_obrigatorio": ["nome"], "arquivos_obrigatorios": ["avatar"]},
            options={},
        )
    )

    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        boundary = "----tramaBoundary123"
        body = _multipart_body(
            boundary,
            [
                ("nome", "ana", None),
                ("avatar", b"ABCDEF", "foto.bin"),
            ],
        )
        req = request.Request(
            url=base + "/upload",
            method="POST",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with request.urlopen(req, timeout=5.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["ok"] is True
        assert payload["nome"] == "ana"
        assert payload["arquivo"] == "foto.bin"
        assert payload["bytes"] == 6
    finally:
        rt.stop()


def test_web_runtime_multipart_validacao_falta_arquivo() -> None:
    app = web_runtime.WebApp()
    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/upload",
            lambda req: {"status": 200, "json": {"ok": True}},
            schema={"arquivos_obrigatorios": ["avatar"]},
            options={},
        )
    )
    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        boundary = "----tramaBoundary456"
        body = _multipart_body(boundary, [("nome", "ana", None)])
        req = request.Request(
            url=base + "/upload",
            method="POST",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            request.urlopen(req, timeout=5.0)
        except Exception as exc:  # noqa: BLE001
            text = exc.read().decode("utf-8")  # type: ignore[attr-defined]
            payload = json.loads(text)
            assert payload["erro"]["codigo"] == "VALIDACAO_FALHOU"
            assert "arquivos.avatar" in payload["erro"]["detalhes"]["faltando"]
        else:
            raise AssertionError("esperava erro de validação 422")
    finally:
        rt.stop()
