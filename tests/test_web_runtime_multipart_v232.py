from __future__ import annotations

import json
from urllib import request

from trama import web_runtime


def _multipart_body(boundary: str, parts: list[tuple[str, str | bytes, str | None]]) -> bytes:
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


def test_v232_multipart_grande_usa_streaming_em_tempfile() -> None:
    app = web_runtime.WebApp()

    def handler(req):
        arq = req["arquivos"]["avatar"][0]
        return {
            "status": 200,
            "json": {
                "ok": True,
                "streaming": arq["streaming"],
                "tem_temp": bool(arq["caminho_temporario"]),
                "bytes_nulos": arq["bytes"] is None,
                "tamanho": arq["tamanho"],
            },
        }

    app.routes.append(
        web_runtime.WebRoute.dynamic(
            "POST",
            "/upload-grande",
            handler,
            schema={"arquivos_obrigatorios": ["avatar"]},
            options={},
        )
    )

    rt = web_runtime.WebRuntime(app, "127.0.0.1", 0, out=lambda _: None, invoke_callable_sync=lambda fn, args: fn(*args))
    rt.start()
    try:
        base = f"http://127.0.0.1:{rt.port}"
        boundary = "----tramaBoundaryGrande"
        grande = b"A" * (1024 * 1024 + 256 * 1024)
        body = _multipart_body(boundary, [("avatar", grande, "grande.bin")])
        req = request.Request(
            url=base + "/upload-grande",
            method="POST",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with request.urlopen(req, timeout=10.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["ok"] is True
        assert payload["streaming"] is True
        assert payload["tem_temp"] is True
        assert payload["bytes_nulos"] is True
        assert payload["tamanho"] == len(grande)
    finally:
        rt.stop()
