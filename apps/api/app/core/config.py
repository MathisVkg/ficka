from functools import lru_cache
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        hide_input_in_errors=True,
    )
    database_url: str | None = Field(default=None, repr=False)
    postgres_host: str = "127.0.0.1"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_user: str | None = None
    postgres_password: SecretStr | None = None
    postgres_db: str | None = None
    cors_origins: list[str] = []

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            url = make_url(value)
        except ArgumentError:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from None
        if url.drivername != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use postgresql+psycopg://")
        return value

    @model_validator(mode="after")
    def require_database_config(self) -> Self:
        if self.database_url is None and not (
            self.postgres_user
            and self.postgres_password
            and self.postgres_password.get_secret_value()
            and self.postgres_db
        ):
            raise ValueError(
                "Set POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB, or DATABASE_URL"
            )
        return self

    @property
    def connection_url(self) -> URL:
        if self.database_url is not None:
            return make_url(self.database_url)
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value() if self.postgres_password else None,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
