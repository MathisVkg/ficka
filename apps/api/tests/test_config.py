import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.fixture(autouse=True)
def clean_database_environment(monkeypatch):
    for key in (
        "DATABASE_URL",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    ):
        monkeypatch.delenv(key, raising=False)


def test_discrete_credentials_preserve_special_characters():
    settings = Settings(
        _env_file=None,
        postgres_user="business",
        postgres_db="ficka",
        postgres_password="p@ss:/word?#%",
    )
    url = settings.connection_url
    assert url.host == "127.0.0.1"
    assert url.port == 5432
    assert url.password == "p@ss:/word?#%"
    assert "p@ss" not in repr(settings)
    assert "p@ss" not in str(url)


def test_explicit_external_url_takes_precedence():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://external:encoded%40secret@remote:5433/db",
        postgres_host="ignored",
    )
    assert settings.connection_url.host == "remote"
    assert settings.connection_url.port == 5433
    assert settings.connection_url.password == "encoded@secret"


def test_container_environment(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_USER", "ficka")
    monkeypatch.setenv("POSTGRES_DB", "ficka")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-only")
    assert Settings(_env_file=None).connection_url.host == "db"


@pytest.mark.parametrize(
    "values", [{}, {"database_url": "sqlite:///test.db"}, {"postgres_port": 0}]
)
def test_invalid_or_missing_config_fails_early(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
