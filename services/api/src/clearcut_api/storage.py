from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .config import Settings


class ObjectStore(Protocol):
    def save_bytes(self, object_key: str, content: bytes) -> str: ...

    def read_text(self, object_key: str) -> str: ...


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


def create_object_store(settings: Settings) -> ObjectStore:
    if settings.storage_backend == "gcs":
        if not settings.gcs_bucket_name:
            raise RuntimeError("GCS_BUCKET_NAME is required when STORAGE_BACKEND=gcs")
        return GcsObjectStore(settings.gcs_bucket_name, settings.google_cloud_project)
    return LocalObjectStore(settings.storage_root)
