import os
from dataclasses import dataclass
from urllib.parse import quote, quote_plus

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str | None = os.getenv("DATABASE_URL") or None
    database_name: str = os.getenv("DATABASE_NAME", "clearcut")
    database_user: str | None = os.getenv("DATABASE_USER") or None
    database_password: str | None = os.getenv("DATABASE_PASSWORD") or None
    cloud_sql_connection_name: str | None = os.getenv("CLOUD_SQL_CONNECTION_NAME") or None
    default_organization_id: str = os.getenv("DEFAULT_ORGANIZATION_ID", "demo-org")
    parallel_mode: str = os.getenv("PARALLEL_MODE", "fixture")
    parallel_api_key: str | None = os.getenv("PARALLEL_API_KEY") or None
    agent_mode: str = os.getenv("AGENT_MODE", "fixture")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    google_cloud_project: str | None = os.getenv("GOOGLE_CLOUD_PROJECT") or None
    google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "local")
    storage_root: str = os.getenv("STORAGE_ROOT", ".data/uploads")
    gcs_bucket_name: str | None = os.getenv("GCS_BUCKET_NAME") or None
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
    web_allowed_origins: str = os.getenv("WEB_ALLOWED_ORIGINS", "http://localhost:3000")

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.cloud_sql_connection_name and self.database_user and self.database_password:
            user = quote(self.database_user, safe="")
            password = quote(self.database_password, safe="")
            database = quote(self.database_name, safe="")
            socket_path = quote_plus(f"/cloudsql/{self.cloud_sql_connection_name}")
            return f"postgresql+psycopg://{user}:{password}@/{database}?host={socket_path}"
        return "sqlite:///./.data/clearcut.db"


settings = Settings()
