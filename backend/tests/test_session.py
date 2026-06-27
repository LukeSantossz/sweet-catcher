import inspect

from app.config import get_settings
from app.db.session import get_session


def test_database_url_uses_psycopg_driver() -> None:
    assert get_settings().database_url.startswith("postgresql+psycopg://")


def test_get_session_is_async_generator() -> None:
    assert inspect.isasyncgenfunction(get_session)
