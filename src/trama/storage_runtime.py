"""Runtime de armazenamento (v1.2): local e S3-compatível."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any


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


@dataclass
class LocalStorage:
    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir = self.base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, key: str) -> Path:
        if not key or key.strip() == "":
            raise StorageError("chave de armazenamento vazia.")
        target = (self.base_dir / key.lstrip("/")).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise StorageError("chave inválida: tentativa de escapar base do storage.")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def put(
        self,
        key: str,
        conteudo: object,
        content_type: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        data = _to_bytes(conteudo)
        path = self._resolve_key(key)
        path.write_bytes(data)
        return {
            "ok": True,
            "backend": "local",
            "key": key,
            "path": str(path),
            "size": len(data),
            "etag": _sha256(data),
            "content_type": content_type,
            "metadata": dict(metadata or {}),
        }

    def get(self, key: str) -> dict[str, object]:
        path = self._resolve_key(key)
        if not path.exists() or not path.is_file():
            raise StorageError(f"objeto não encontrado: {key}")
        data = path.read_bytes()
        return {
            "ok": True,
            "backend": "local",
            "key": key,
            "path": str(path),
            "size": len(data),
            "etag": _sha256(data),
            "bytes": data,
        }

    def delete(self, key: str) -> bool:
        path = self._resolve_key(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def list(self, prefix: str = "") -> list[str]:
        files: list[str] = []
        for p in self.base_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = str(p.relative_to(self.base_dir))
            if rel.startswith(prefix):
                files.append(rel)
        return sorted(files)

    def url(self, key: str) -> str:
        path = self._resolve_key(key)
        return f"file://{path}"


@dataclass
class S3CompatStorage:
    bucket: str
    endpoint_url: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    region: str | None = None
    prefixo: str = ""
    _client: object | None = field(default=None, init=False, repr=False)

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

    def put(
        self,
        key: str,
        conteudo: object,
        content_type: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        data = _to_bytes(conteudo)
        client = self._build_client()
        s3_key = self._key(key)
        kwargs: dict[str, object] = {
            "Bucket": self.bucket,
            "Key": s3_key,
            "Body": data,
            "Metadata": {str(k): str(v) for k, v in dict(metadata or {}).items()},
        }
        if content_type:
            kwargs["ContentType"] = content_type
        client.put_object(**kwargs)
        return {
            "ok": True,
            "backend": "s3",
            "bucket": self.bucket,
            "key": s3_key,
            "size": len(data),
            "etag": _sha256(data),
        }

    def get(self, key: str) -> dict[str, object]:
        client = self._build_client()
        s3_key = self._key(key)
        out = client.get_object(Bucket=self.bucket, Key=s3_key)
        data = out["Body"].read()
        return {
            "ok": True,
            "backend": "s3",
            "bucket": self.bucket,
            "key": s3_key,
            "size": len(data),
            "etag": _sha256(data),
            "bytes": data,
        }

    def delete(self, key: str) -> bool:
        client = self._build_client()
        s3_key = self._key(key)
        client.delete_object(Bucket=self.bucket, Key=s3_key)
        return True

    def list(self, prefix: str = "") -> list[str]:
        client = self._build_client()
        s3_prefix = self._key(prefix)
        out = client.list_objects_v2(Bucket=self.bucket, Prefix=s3_prefix)
        contents = list(out.get("Contents", []))
        return [str(item.get("Key", "")) for item in contents]

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
