"""Application settings, read from environment variables (or a local `.env` file)."""

import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/ficka.db"
    temp_dir: Path = Field(default_factory=lambda: Path(tempfile.gettempdir()) / "ficka")
    document_ttl_hours: int = Field(default=24, gt=0)
    log_level: str = "INFO"
    # Timezone used for "today" (overdue, periods). Belgium by default.
    timezone: str = "Europe/Brussels"
    # Serve /api/docs and /api/openapi.json (unauthenticated). Development only.
    api_docs: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
