"""Runtime de armazenamento com pipeline de upload e politicas formais."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import mimetypes
from pathlib import Path
import tempfile
import time
from urllib.parse import quote
import uuid


class StorageError(RuntimeError):
    """Erro de armazenamento."""


def _to_bytes(conteudo: object) -> bytes:
    if isinstance(conteudo, bytes):
        return conteudo
    if isinstance(conteudo, bytearray):
        return bytes(conteudo)
    if isinstance(conteudo, str):
        return conteudo.encode("utf-8")
    if isinstance(conteudo, (dict, list)):
        return json.dumps(conteudo, ensure_ascii=False).encode("utf-8")
    return str(conteudo).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _agora_ts() -> int:
    return int(time.time())


def _mime_por_chave(chave: str) -> str:
    guessed = mimetypes.guess_type(chave)[0]
    return guessed or "application/octet-stream"


def _normalizar_politicas(politicas: dict[str, object] | None = None) -> dict[str, object]:
    src = dict(politicas or {})
    return {
        "visibilidade": str(src.get("visibilidade", "privado") or "privado"),
        "retencao_ate": src.get("retencao_ate"),
        "lifecycle_dias": (int(src["lifecycle_dias"]) if "lifecycle_dias" in src and src["lifecycle_dias"] is not None else None),
        "expira_url_assinada_em": (
            int(src["expira_url_assinada_em"]) if "expira_url_assinada_em" in src and src["expira_url_assinada_em"] is not None else 3600
        ),
        "promocao_obrigatoria": bool(src.get("promocao_obrigatoria", False)),
    }


def _normalizar_validacao(validacao: dict[str, object] | None, chave_final: str, content_type: str | None = None) -> dict[str, object]:
    src = dict(validacao or {})
    mime_permitidos = src.get("mime_permitidos")
    if isinstance(mime_permitidos, str):
        mime_permitidos = [mime_permitidos]
    return {
        "mime_permitidos": [str(x) for x in list(mime_permitidos or [])],
        "tamanho_maximo": (int(src["tamanho_maximo"]) if "tamanho_maximo" in src and src["tamanho_maximo"] is not None else None),
        "hash_sha256": (str(src["hash_sha256"]) if src.get("hash_sha256") else None),
        "content_type": str(content_type or src.get("content_type") or _mime_por_chave(chave_final)),
    }


@dataclass
class UploadSessao:
    upload_id: str
    chave_temporaria: str
    chave_final: str
    content_type: str
    metadata: dict[str, object]
    politicas: dict[str, object]
    validacao: dict[str, object]
    tmp_path: Path
    tamanho: int = 0
    sha256: str = field(default_factory=lambda: hashlib.sha256(b"").hexdigest())
    finalizado: bool = False


class _StorageMixin:
    _uploads: dict[str, UploadSessao]
    _secret_assinatura: str
    _politicas_padrao: dict[str, object]

    def _metadata_payload(
        self,
        *,
        chave: str,
        tamanho: int,
        etag: str,
        content_type: str | None,
        metadata: dict[str, object] | None,
        politicas: dict[str, object] | None,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        out = {
            "chave": chave,
            "tamanho": int(tamanho),
            "etag": etag,
            "content_type": str(content_type or _mime_por_chave(chave)),
            "metadata": dict(metadata or {}),
            "politicas": _normalizar_politicas({**self._politicas_padrao, **dict(politicas or {})}),
            "atualizado_em": _agora_ts(),
        }
        if extra:
            out.update(extra)
        return out

    def definir_politicas(self, politicas: dict[str, object] | None = None) -> dict[str, object]:
        self._politicas_padrao = _normalizar_politicas(politicas)
        return {"ok": True, "politicas": dict(self._politicas_padrao)}

    def iniciar_upload(
        self,
        chave_final: str,
        content_type: str | None = None,
        metadata: dict[str, object] | None = None,
        validacao: dict[str, object] | None = None,
        politicas: dict[str, object] | None = None,
    ) -> dict[str, object]:
        chave_limpa = str(chave_final).lstrip("/")
        if not chave_limpa:
            raise StorageError("chave final de upload vazia.")
        upload_id = uuid.uuid4().hex
        chave_temporaria = f"_uploads/tmp/{upload_id}.part"
        tmp_path = self._criar_arquivo_temporario(upload_id)
        sessao = UploadSessao(
            upload_id=upload_id,
            chave_temporaria=chave_temporaria,
            chave_final=chave_limpa,
            content_type=str(content_type or _mime_por_chave(chave_limpa)),
            metadata=dict(metadata or {}),
            politicas=_normalizar_politicas({**self._politicas_padrao, **dict(politicas or {})}),
            validacao=_normalizar_validacao(validacao, chave_limpa, content_type=content_type),
            tmp_path=tmp_path,
        )
        self._uploads[upload_id] = sessao
        return {
            "ok": True,
            "upload_id": upload_id,
            "chave_temporaria": chave_temporaria,
            "chave_final": chave_limpa,
            "content_type": sessao.content_type,
            "validacao": dict(sessao.validacao),
            "politicas": dict(sessao.politicas),
        }

    def escrever_upload(self, upload_id: str, conteudo: object) -> dict[str, object]:
        sessao = self._obter_upload(upload_id)
        if sessao.finalizado:
            raise StorageError("upload já finalizado.")
        data = _to_bytes(conteudo)
        with sessao.tmp_path.open("ab") as fp:
            fp.write(data)
        sessao.tamanho += len(data)
        sessao.sha256 = self._sha256_arquivo(sessao.tmp_path)
        limite = sessao.validacao.get("tamanho_maximo")
        if isinstance(limite, int) and sessao.tamanho > limite:
            raise StorageError("upload excede tamanho máximo permitido.")
        return {"ok": True, "upload_id": upload_id, "bytes_escritos": len(data), "tamanho_total": sessao.tamanho}

    def abortar_upload(self, upload_id: str) -> dict[str, object]:
        sessao = self._obter_upload(upload_id)
        try:
            if sessao.tmp_path.exists():
                sessao.tmp_path.unlink()
        finally:
            self._uploads.pop(upload_id, None)
        return {"ok": True, "upload_id": upload_id, "abortado": True}

    def finalizar_upload(
        self,
        upload_id: str,
        *,
        chave_final: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, object] | None = None,
        politicas: dict[str, object] | None = None,
        validacao: dict[str, object] | None = None,
    ) -> dict[str, object]:
        sessao = self._obter_upload(upload_id)
        if sessao.finalizado:
            raise StorageError("upload já finalizado.")
        final_key = str(chave_final or sessao.chave_final).lstrip("/")
        final_content_type = str(content_type or sessao.content_type)
        final_metadata = dict(sessao.metadata)
        final_metadata.update(dict(metadata or {}))
        final_politicas = _normalizar_politicas({**sessao.politicas, **dict(politicas or {})})
        final_validacao = _normalizar_validacao({**sessao.validacao, **dict(validacao or {})}, final_key, content_type=final_content_type)

        self._validar_upload(sessao, final_validacao, final_content_type)
        resultado = self.promover_upload_temporario(
            sessao.tmp_path,
            sessao.chave_temporaria,
            final_key,
            content_type=final_content_type,
            metadata=final_metadata,
            politicas=final_politicas,
            hash_sha256=sessao.sha256,
            tamanho=sessao.tamanho,
        )
        sessao.finalizado = True
        self._uploads.pop(upload_id, None)
        return {**resultado, "upload_id": upload_id, "chave_temporaria": sessao.chave_temporaria}

    def processar_upload(
        self,
        chave_final: str,
        conteudo: object,
        *,
        content_type: str | None = None,
        metadata: dict[str, object] | None = None,
        politicas: dict[str, object] | None = None,
        validacao: dict[str, object] | None = None,
    ) -> dict[str, object]:
        iniciado = self.iniciar_upload(
            chave_final,
            content_type=content_type,
            metadata=metadata,
            politicas=politicas,
            validacao=validacao,
        )
        self.escrever_upload(str(iniciado["upload_id"]), conteudo)
        return self.finalizar_upload(str(iniciado["upload_id"]))

    def promover(self, chave_temporaria: str, chave_final: str, metadata: dict[str, object] | None = None) -> dict[str, object]:
        origem = self.get(chave_temporaria)
        return self.put(
            chave_final,
            origem["bytes"],
            content_type=str(origem.get("content_type") or _mime_por_chave(chave_final)),
            metadata={**dict(origem.get("metadata", {})), **dict(metadata or {})},
            politicas=dict(origem.get("politicas", {})),
        )

    def obter_metadados(self, chave: str) -> dict[str, object]:
        meta = self._ler_sidecar(chave)
        if meta is None:
            raise StorageError(f"metadados não encontrados para: {chave}")
        return meta

    def url_assinada(
        self,
        chave: str,
        expira_em: int = 3600,
        operacao: str = "baixar",
    ) -> str:
        expira = _agora_ts() + max(1, int(expira_em))
        payload = f"{operacao}:{chave}:{expira}"
        assinatura = hmac.new(self._secret_assinatura.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return (
            f"{self._url_base_assinada(chave)}?operacao={quote(operacao)}&expira_em={expira}&assinatura={assinatura}"
        )

    def _obter_upload(self, upload_id: str) -> UploadSessao:
        try:
            return self._uploads[str(upload_id)]
        except KeyError as exc:
            raise StorageError("upload não encontrado.") from exc

    def _validar_upload(self, sessao: UploadSessao, validacao: dict[str, object], content_type: str) -> None:
        mime_permitidos = [str(x) for x in list(validacao.get("mime_permitidos", []))]
        if mime_permitidos and content_type not in mime_permitidos:
            raise StorageError("MIME do upload não permitido.")
        hash_esperado = validacao.get("hash_sha256")
        if isinstance(hash_esperado, str) and hash_esperado and sessao.sha256 != hash_esperado:
            raise StorageError("hash SHA-256 do upload divergente.")
        limite = validacao.get("tamanho_maximo")
        if isinstance(limite, int) and sessao.tamanho > limite:
            raise StorageError("upload excede tamanho máximo permitido.")

    def _sha256_arquivo(self, caminho: Path) -> str:
        digest = hashlib.sha256()
        with caminho.open("rb") as fp:
            while True:
                chunk = fp.read(65536)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()


@dataclass
class LocalStorage(_StorageMixin):
    base_dir: Path
    politicas_padrao: dict[str, object] | None = None
    segredo_assinatura: str = "trama-local-storage"
    _uploads: dict[str, UploadSessao] = field(default_factory=dict, init=False, repr=False)
    _politicas_padrao: dict[str, object] = field(default_factory=dict, init=False, repr=False)
    _secret_assinatura: str = field(default="trama-local-storage", init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_dir = self.base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / ".trama_meta").mkdir(parents=True, exist_ok=True)
        (self.base_dir / ".trama_uploads").mkdir(parents=True, exist_ok=True)
        self._secret_assinatura = str(self.segredo_assinatura)
        self._politicas_padrao = _normalizar_politicas(self.politicas_padrao)

    def _resolve_key(self, key: str) -> Path:
        if not key or key.strip() == "":
            raise StorageError("chave de armazenamento vazia.")
        target = (self.base_dir / key.lstrip("/")).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise StorageError("chave inválida: tentativa de escapar base do storage.")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def _meta_path(self, key: str) -> Path:
        meta_dir = self.base_dir / ".trama_meta"
        return (meta_dir / (key.lstrip("/") + ".json")).resolve()

    def _write_sidecar(self, key: str, payload: dict[str, object]) -> None:
        meta = self._meta_path(key)
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _ler_sidecar(self, key: str) -> dict[str, object] | None:
        meta = self._meta_path(key)
        if not meta.exists():
            return None
        return dict(json.loads(meta.read_text(encoding="utf-8")))

    def _criar_arquivo_temporario(self, upload_id: str) -> Path:
        path = (self.base_dir / ".trama_uploads" / f"{upload_id}.part").resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
        return path

    def promover_upload_temporario(
        self,
        tmp_path: Path,
        chave_temporaria: str,
        chave_final: str,
        *,
        content_type: str,
        metadata: dict[str, object] | None,
        politicas: dict[str, object] | None,
        hash_sha256: str,
        tamanho: int,
    ) -> dict[str, object]:
        destino = self._resolve_key(chave_final)
        destino.write_bytes(tmp_path.read_bytes())
        if tmp_path.exists():
            tmp_path.unlink()
        payload = self._metadata_payload(
            chave=chave_final,
            tamanho=tamanho,
            etag=hash_sha256,
            content_type=content_type,
            metadata=metadata,
            politicas=politicas,
            extra={"origem_temporaria": chave_temporaria},
        )
        self._write_sidecar(chave_final, payload)
        return {
            "ok": True,
            "backend": "local",
            "key": chave_final,
            "path": str(destino),
            "size": tamanho,
            "etag": hash_sha256,
            "content_type": payload["content_type"],
            "metadata": dict(payload["metadata"]),
            "politicas": dict(payload["politicas"]),
        }

    def put(
        self,
        key: str,
        conteudo: object,
        content_type: str | None = None,
        metadata: dict[str, object] | None = None,
        politicas: dict[str, object] | None = None,
    ) -> dict[str, object]:
        data = _to_bytes(conteudo)
        path = self._resolve_key(key)
        path.write_bytes(data)
        payload = self._metadata_payload(
            chave=key,
            tamanho=len(data),
            etag=_sha256(data),
            content_type=content_type,
            metadata=metadata,
            politicas=politicas,
        )
        self._write_sidecar(key, payload)
        return {
            "ok": True,
            "backend": "local",
            "key": key,
            "path": str(path),
            "size": len(data),
            "etag": payload["etag"],
            "content_type": payload["content_type"],
            "metadata": dict(payload["metadata"]),
            "politicas": dict(payload["politicas"]),
        }

    def get(self, key: str) -> dict[str, object]:
        path = self._resolve_key(key)
        if not path.exists() or not path.is_file():
            raise StorageError(f"objeto não encontrado: {key}")
        data = path.read_bytes()
        meta = self._ler_sidecar(key) or self._metadata_payload(
            chave=key,
            tamanho=len(data),
            etag=_sha256(data),
            content_type=None,
            metadata={},
            politicas=None,
        )
        return {
            "ok": True,
            "backend": "local",
            "key": key,
            "path": str(path),
            "size": len(data),
            "etag": meta["etag"],
            "bytes": data,
            "content_type": meta["content_type"],
            "metadata": dict(meta["metadata"]),
            "politicas": dict(meta["politicas"]),
        }

    def delete(self, key: str) -> bool:
        path = self._resolve_key(key)
        apagou = False
        if path.exists():
            path.unlink()
            apagou = True
        meta = self._meta_path(key)
        if meta.exists():
            meta.unlink()
        return apagou

    def list(self, prefix: str = "") -> list[str]:
        files: list[str] = []
        for p in self.base_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(self.base_dir))
            if rel.startswith(".trama_meta/") or rel.startswith(".trama_uploads/"):
                continue
            if rel.startswith(prefix):
                files.append(rel)
        return sorted(files)

    def url(self, key: str) -> str:
        path = self._resolve_key(key)
        return f"file://{path}"

    def _url_base_assinada(self, chave: str) -> str:
        return f"file://{self._resolve_key(chave)}"


@dataclass
class S3CompatStorage(_StorageMixin):
    bucket: str
    endpoint_url: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    region: str | None = None
    prefixo: str = ""
    politicas_padrao: dict[str, object] | None = None
    segredo_assinatura: str = "trama-s3-storage"
    _client: object | None = field(default=None, init=False, repr=False)
    _uploads: dict[str, UploadSessao] = field(default_factory=dict, init=False, repr=False)
    _politicas_padrao: dict[str, object] = field(default_factory=dict, init=False, repr=False)
    _secret_assinatura: str = field(default="trama-s3-storage", init=False, repr=False)

    def __post_init__(self) -> None:
        self._secret_assinatura = str(self.segredo_assinatura)
        self._politicas_padrao = _normalizar_politicas(self.politicas_padrao)

    def _import_boto3(self):
        try:
            import boto3  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise StorageError("boto3 não disponível. Instale dependência para storage S3.") from exc
        return boto3

    def _build_client(self):
        if self._client is not None:
            return self._client
        boto3 = self._import_boto3()
        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url or None,
            aws_access_key_id=self.access_key or None,
            aws_secret_access_key=self.secret_key or None,
            region_name=self.region or None,
        )
        return self._client

    def _key(self, key: str) -> str:
        clean = key.lstrip("/")
        if self.prefixo.strip():
            return f"{self.prefixo.strip('/').rstrip('/')}/{clean}"
        return clean

    def _ler_sidecar(self, key: str) -> dict[str, object] | None:
        client = self._build_client()
        try:
            out = client.get_object(Bucket=self.bucket, Key=self._key(f".trama_meta/{key}.json"))
        except Exception:
            return None
        return dict(json.loads(out["Body"].read().decode("utf-8")))

    def _write_sidecar(self, key: str, payload: dict[str, object]) -> None:
        client = self._build_client()
        client.put_object(
            Bucket=self.bucket,
            Key=self._key(f".trama_meta/{key}.json"),
            Body=json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"),
            ContentType="application/json",
        )

    def _criar_arquivo_temporario(self, upload_id: str) -> Path:
        tmp_dir = Path(tempfile.gettempdir()) / "trama_storage_uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        path = (tmp_dir / f"{upload_id}.part").resolve()
        path.write_bytes(b"")
        return path

    def promover_upload_temporario(
        self,
        tmp_path: Path,
        chave_temporaria: str,
        chave_final: str,
        *,
        content_type: str,
        metadata: dict[str, object] | None,
        politicas: dict[str, object] | None,
        hash_sha256: str,
        tamanho: int,
    ) -> dict[str, object]:
        data = tmp_path.read_bytes()
        if tmp_path.exists():
            tmp_path.unlink()
        return self.put(chave_final, data, content_type=content_type, metadata=metadata, politicas=politicas)

    def put(
        self,
        key: str,
        conteudo: object,
        content_type: str | None = None,
        metadata: dict[str, object] | None = None,
        politicas: dict[str, object] | None = None,
    ) -> dict[str, object]:
        data = _to_bytes(conteudo)
        client = self._build_client()
        s3_key = self._key(key)
        payload = self._metadata_payload(
            chave=s3_key,
            tamanho=len(data),
            etag=_sha256(data),
            content_type=content_type,
            metadata=metadata,
            politicas=politicas,
        )
        kwargs: dict[str, object] = {
            "Bucket": self.bucket,
            "Key": s3_key,
            "Body": data,
            "Metadata": {str(k): str(v) for k, v in dict(payload["metadata"]).items()},
            "ContentType": str(payload["content_type"]),
        }
        if str(dict(payload["politicas"]).get("visibilidade", "privado")).lower() == "publico":
            kwargs["ACL"] = "public-read"
        client.put_object(**kwargs)
        self._write_sidecar(key, payload)
        return {
            "ok": True,
            "backend": "s3",
            "bucket": self.bucket,
            "key": s3_key,
            "size": len(data),
            "etag": payload["etag"],
            "content_type": payload["content_type"],
            "metadata": dict(payload["metadata"]),
            "politicas": dict(payload["politicas"]),
        }

    def get(self, key: str) -> dict[str, object]:
        client = self._build_client()
        s3_key = self._key(key)
        out = client.get_object(Bucket=self.bucket, Key=s3_key)
        data = out["Body"].read()
        meta = self._ler_sidecar(key) or self._metadata_payload(
            chave=s3_key,
            tamanho=len(data),
            etag=_sha256(data),
            content_type=str(out.get("ContentType") or _mime_por_chave(s3_key)),
            metadata=dict(out.get("Metadata", {})),
            politicas=None,
        )
        return {
            "ok": True,
            "backend": "s3",
            "bucket": self.bucket,
            "key": s3_key,
            "size": len(data),
            "etag": meta["etag"],
            "bytes": data,
            "content_type": meta["content_type"],
            "metadata": dict(meta["metadata"]),
            "politicas": dict(meta["politicas"]),
        }

    def delete(self, key: str) -> bool:
        client = self._build_client()
        s3_key = self._key(key)
        client.delete_object(Bucket=self.bucket, Key=s3_key)
        try:
            client.delete_object(Bucket=self.bucket, Key=self._key(f".trama_meta/{key}.json"))
        except Exception:
            pass
        return True

    def list(self, prefix: str = "") -> list[str]:
        client = self._build_client()
        s3_prefix = self._key(prefix)
        out = client.list_objects_v2(Bucket=self.bucket, Prefix=s3_prefix)
        contents = list(out.get("Contents", []))
        itens: list[str] = []
        for item in contents:
            chave = str(item.get("Key", ""))
            if "/.trama_meta/" in chave or chave.startswith(self._key(".trama_meta/")):
                continue
            itens.append(chave)
        return sorted(itens)

    def url(self, key: str, expires_in: int = 3600) -> str:
        client = self._build_client()
        s3_key = self._key(key)
        return str(
            client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=int(expires_in),
            )
        )

    def _url_base_assinada(self, chave: str) -> str:
        base = (self.endpoint_url or "s3://").rstrip("/")
        return f"{base}/{self.bucket}/{self._key(chave)}"
