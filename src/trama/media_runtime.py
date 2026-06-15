"""Runtime de mídia com variantes, metadados e integração com storage."""

from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any

from . import storage_runtime

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover - opcional
    Image = None  # type: ignore[assignment]


class MediaError(RuntimeError):
    """Erro de pipeline de mídia."""


def _to_bytes(conteudo: object) -> bytes:
    if isinstance(conteudo, bytes):
        return conteudo
    if isinstance(conteudo, bytearray):
        return bytes(conteudo)
    if isinstance(conteudo, str):
        p = Path(conteudo)
        if p.exists() and p.is_file():
            return p.read_bytes()
        return conteudo.encode("utf-8")
    raise MediaError("conteúdo inválido; esperado bytes/bytearray ou caminho de arquivo.")


def midia_ler_arquivo(caminho: str) -> bytes:
    return Path(caminho).read_bytes()


def midia_salvar_arquivo(caminho: str, conteudo: object) -> dict[str, object]:
    data = _to_bytes(conteudo)
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"ok": True, "caminho": str(path), "bytes": len(data)}


def midia_comprimir_gzip(conteudo: object, nivel: int = 6) -> bytes:
    data = _to_bytes(conteudo)
    level = min(9, max(1, int(nivel)))
    return gzip.compress(data, compresslevel=level)


def midia_descomprimir_gzip(conteudo: object) -> bytes:
    data = _to_bytes(conteudo)
    try:
        return gzip.decompress(data)
    except Exception as exc:  # noqa: BLE001
        raise MediaError("conteúdo gzip inválido.") from exc


def midia_sha256(conteudo: object) -> str:
    data = _to_bytes(conteudo)
    return hashlib.sha256(data).hexdigest()


def _require_pillow() -> None:
    if Image is None:
        raise MediaError("Pillow não disponível. Instale dependência de mídia para processar imagens.")


def _save_image(img: Any, formato_saida: str, qualidade: int = 85) -> bytes:
    out = BytesIO()
    fmt = str(formato_saida).upper()
    if fmt == "JPG":
        fmt = "JPEG"
    params: dict[str, object] = {}
    if fmt in {"JPEG", "WEBP"}:
        params["quality"] = min(100, max(1, int(qualidade)))
        params["optimize"] = True
    img.save(out, format=fmt, **params)
    return out.getvalue()


def _detectar_formato(conteudo: bytes, fallback: str = "BIN") -> str:
    if Image is not None:
        try:
            with Image.open(BytesIO(conteudo)) as img:  # type: ignore[union-attr]
                if img.format:
                    return str(img.format).upper()
        except Exception:
            pass
    return fallback.upper()


def midia_extrair_metadados(conteudo: object) -> dict[str, object]:
    data = _to_bytes(conteudo)
    meta: dict[str, object] = {
        "sha256": midia_sha256(data),
        "tamanho": len(data),
        "formato": _detectar_formato(data, fallback="BIN"),
    }
    if Image is not None:
        try:
            with Image.open(BytesIO(data)) as img:  # type: ignore[union-attr]
                meta["largura"] = int(img.width)
                meta["altura"] = int(img.height)
                meta["modo"] = str(img.mode)
                meta["formato"] = str(img.format or meta["formato"]).upper()
        except Exception:
            pass
    return {"ok": True, "meta": meta}


def midia_redimensionar_imagem(
    conteudo: object,
    largura: int,
    altura: int,
    manter_aspecto: bool = True,
    formato_saida: str | None = None,
    qualidade: int = 85,
) -> dict[str, object]:
    _require_pillow()
    data = _to_bytes(conteudo)
    with Image.open(BytesIO(data)) as img:  # type: ignore[union-attr]
        if manter_aspecto:
            clone = img.copy()
            clone.thumbnail((int(largura), int(altura)))
            out_img = clone
        else:
            out_img = img.resize((int(largura), int(altura)))
        fmt = str(formato_saida or img.format or "PNG")
        out = _save_image(out_img, fmt, qualidade=qualidade)
        return {
            "ok": True,
            "bytes": out,
            "largura": int(out_img.width),
            "altura": int(out_img.height),
            "formato": fmt.upper(),
            "tamanho": len(out),
        }


def midia_converter_imagem(conteudo: object, formato_saida: str, qualidade: int = 85) -> dict[str, object]:
    _require_pillow()
    data = _to_bytes(conteudo)
    with Image.open(BytesIO(data)) as img:  # type: ignore[union-attr]
        fmt = str(formato_saida).upper()
        if fmt in {"JPG", "JPEG"} and img.mode not in {"RGB", "L"}:
            out_img = img.convert("RGB")
        else:
            out_img = img.copy()
        out = _save_image(out_img, fmt, qualidade=qualidade)
        return {
            "ok": True,
            "bytes": out,
            "largura": int(out_img.width),
            "altura": int(out_img.height),
            "formato": fmt,
            "tamanho": len(out),
        }


def midia_pipeline(
    conteudo: object,
    opcoes: dict[str, object] | None = None,
) -> dict[str, object]:
    opts = dict(opcoes or {})
    atual = _to_bytes(conteudo)
    meta: dict[str, object] = {"etapas": []}

    red = opts.get("redimensionar")
    if isinstance(red, dict):
        out_red = midia_redimensionar_imagem(
            atual,
            largura=int(red.get("largura", 0)),
            altura=int(red.get("altura", 0)),
            manter_aspecto=bool(red.get("manter_aspecto", True)),
            formato_saida=str(red.get("formato_saida")) if red.get("formato_saida") else None,
            qualidade=int(red.get("qualidade", 85)),
        )
        atual = bytes(out_red["bytes"])
        meta["etapas"].append("redimensionar")
        meta["largura"] = out_red["largura"]
        meta["altura"] = out_red["altura"]
        meta["formato"] = out_red["formato"]

    if "converter_formato" in opts:
        out_conv = midia_converter_imagem(atual, str(opts["converter_formato"]), qualidade=int(opts.get("qualidade", 85)))
        atual = bytes(out_conv["bytes"])
        meta["etapas"].append("converter")
        meta["formato"] = out_conv["formato"]

    if bool(opts.get("comprimir_gzip", False)):
        atual = midia_comprimir_gzip(atual, nivel=int(opts.get("nivel_gzip", 6)))
        meta["etapas"].append("gzip")

    meta.update(midia_extrair_metadados(atual)["meta"])
    return {"ok": True, "bytes": atual, "meta": meta}


def midia_pipeline_storage(
    storage: object,
    chave_origem: str,
    prefixo_destino: str,
    opcoes: dict[str, object] | None = None,
) -> dict[str, object]:
    if not isinstance(storage, (storage_runtime.LocalStorage, storage_runtime.S3CompatStorage)):
        raise MediaError("storage inválido para pipeline de mídia.")
    origem = storage.get(chave_origem)
    bruto = bytes(origem["bytes"])
    opts = dict(opcoes or {})
    meta_origem = midia_extrair_metadados(bruto)["meta"]
    variantes_conf = list(opts.get("variantes", []))
    variantes: list[dict[str, object]] = []

    if not variantes_conf:
        variantes_conf = [{"nome": "original", "acao": "copiar"}]

    for variante in variantes_conf:
        if not isinstance(variante, dict):
            continue
        nome = str(variante.get("nome", "variante"))
        chave_saida = str(variante.get("chave") or f"{prefixo_destino.rstrip('/')}/{nome}")
        acao = str(variante.get("acao", "pipeline"))
        content_type = str(variante.get("content_type") or origem.get("content_type") or "application/octet-stream")
        if acao == "copiar":
            saida = bruto
            meta_saida = dict(meta_origem)
        else:
            proc = midia_pipeline(bruto, opcoes=dict(variante.get("opcoes", {})))
            saida = bytes(proc["bytes"])
            meta_saida = dict(proc["meta"])
            if "formato" in meta_saida:
                fmt = str(meta_saida["formato"]).lower()
                if fmt in {"jpeg", "jpg"}:
                    content_type = "image/jpeg"
                elif fmt == "png":
                    content_type = "image/png"
                elif fmt == "webp":
                    content_type = "image/webp"
        salvo = storage.put(
            chave_saida,
            saida,
            content_type=content_type,
            metadata={
                "pipeline_midia": True,
                "origem": chave_origem,
                "variante": nome,
                **dict(variante.get("metadata", {})),
            },
        )
        variantes.append(
            {
                "nome": nome,
                "chave": salvo["key"],
                "content_type": salvo["content_type"],
                "tamanho": salvo["size"],
                "etag": salvo["etag"],
                "meta": meta_saida,
            }
        )

    manifesto = {
        "ok": True,
        "origem": {
            "chave": chave_origem,
            "content_type": origem.get("content_type"),
            "meta": meta_origem,
        },
        "variantes": variantes,
        "total_variantes": len(variantes),
    }
    manifesto_key = str(opts.get("manifesto") or f"{prefixo_destino.rstrip('/')}/manifesto.json")
    storage.put(manifesto_key, manifesto, content_type="application/json", metadata={"pipeline_midia": True, "tipo": "manifesto"})
    manifesto["manifesto"] = manifesto_key
    return manifesto
