import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./.data/clearcut.db")
    default_organization_id: str = os.getenv("DEFAULT_ORGANIZATION_ID", "demo-org")
    parallel_mode: str = os.getenv("PARALLEL_MODE", "fixture")
    parallel_api_key: str | None = os.getenv("PARALLEL_API_KEY") or None
    google_cloud_project: str | None = os.getenv("GOOGLE_CLOUD_PROJECT") or None
    google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    storage_root: str = os.getenv("STORAGE_ROOT", ".data/uploads")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
    web_allowed_origins: str = os.getenv("WEB_ALLOWED_ORIGINS", "http://localhost:3000")


settings = Settings()
