"""TIME-233 — DATABASE_URL driver coercion so a managed-Postgres URL works unedited."""

from app.core.config import Settings


def _db(url: str) -> str:
    return Settings(database_url=url).database_url


def test_plain_postgresql_url_is_coerced_to_asyncpg():
    assert _db("postgresql://u:p@host:5432/db") == "postgresql+asyncpg://u:p@host:5432/db"


def test_heroku_style_postgres_url_is_coerced():
    assert _db("postgres://u:p@host/db") == "postgresql+asyncpg://u:p@host/db"


def test_explicit_asyncpg_url_is_left_untouched():
    url = "postgresql+asyncpg://u:p@host/db"
    assert _db(url) == url
