from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import Settings


@dataclass(frozen=True)
class StoredObjectMetadata:
    size_bytes: int
    content_type: str | None = None
    md5_hash: str | None = None


class ObjectStore(Protocol):
    def save_bytes(self, object_key: str, content: bytes) -> str: ...

    def read_text(self, object_key: str) -> str: ...

    def supports_resumable_uploads(self) -> bool: ...

    def object_uri(self, object_key: str) -> str: ...

    def create_resumable_upload_session(
        self,
        object_key: str,
        content_type: str,
        size_bytes: int,
        origin: str | None = None,
    ) -> str: ...

    def get_metadata(self, object_key: str) -> StoredObjectMetadata: ...


class LocalObjectStore:
    """Development object store; the interface is intentionally replaceable by Cloud Storage."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, object_key: str, content: bytes) -> str:
        target = self.root / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return object_key

    def read_text(self, object_key: str) -> str:
        return (self.root / object_key).read_text(encoding="utf-8")

    def supports_resumable_uploads(self) -> bool:
        return False

    def object_uri(self, object_key: str) -> str:
        return (self.root / object_key).resolve().as_uri()

    def create_resumable_upload_session(
        self,
        object_key: str,
        content_type: str,
        size_bytes: int,
        origin: str | None = None,
    ) -> str:
        raise NotImplementedError("resumable_upload_requires_gcs")

    def get_metadata(self, object_key: str) -> StoredObjectMetadata:
        target = self.root / object_key
        stat = target.stat()
        return StoredObjectMetadata(size_bytes=stat.st_size)


class GcsObjectStore:
    """Google Cloud Storage implementation used by deployed API instances."""

    def __init__(self, bucket_name: str, project: str | None = None):
        try:
            from google.cloud import storage
        except ImportError as exc:  # pragma: no cover - deployment configuration guard
            raise RuntimeError(
                "STORAGE_BACKEND=gcs requires the google-cloud-storage dependency"
            ) from exc

        self.bucket = storage.Client(project=project).bucket(bucket_name)

    def save_bytes(self, object_key: str, content: bytes) -> str:
        self.bucket.blob(object_key).upload_from_string(content)
        return object_key

    def read_text(self, object_key: str) -> str:
        return self.bucket.blob(object_key).download_as_text(encoding="utf-8")

    def supports_resumable_uploads(self) -> bool:
        return True

    def object_uri(self, object_key: str) -> str:
        return f"gs://{self.bucket.name}/{object_key}"

    def create_resumable_upload_session(
        self,
        object_key: str,
        content_type: str,
        size_bytes: int,
        origin: str | None = None,
    ) -> str:
        blob = self.bucket.blob(object_key)
        return blob.create_resumable_upload_session(
            content_type=content_type,
            size=size_bytes,
            origin=origin,
        )

    def get_metadata(self, object_key: str) -> StoredObjectMetadata:
        blob = self.bucket.blob(object_key)
        blob.reload()
        if blob.size is None:
            raise FileNotFoundError(object_key)
        return StoredObjectMetadata(
            size_bytes=int(blob.size), content_type=blob.content_type, md5_hash=blob.md5_hash
        )


def create_object_store(settings: Settings) -> ObjectStore:
    if settings.storage_backend == "gcs":
        if not settings.gcs_bucket_name:
            raise RuntimeError("GCS_BUCKET_NAME is required when STORAGE_BACKEND=gcs")
        return GcsObjectStore(settings.gcs_bucket_name, settings.google_cloud_project)
    return LocalObjectStore(settings.storage_root)
