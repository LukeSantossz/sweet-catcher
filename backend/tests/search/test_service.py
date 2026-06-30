from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.search.models import SearchCriteria
from app.search.schemas import SearchCriteriaData
from app.search.service import SearchCriteriaManager


def _data(*keywords: str) -> SearchCriteriaData:
    return SearchCriteriaData(keywords=list(keywords))


async def test_get_returns_none_when_unset(db_session: AsyncSession) -> None:
    manager = SearchCriteriaManager(db_session)
    assert await manager.get() is None


async def test_set_creates_then_updates_single_row(db_session: AsyncSession) -> None:
    manager = SearchCriteriaManager(db_session)
    await manager.set(_data("python"))
    await manager.set(_data("rust"))
    count = await db_session.scalar(select(func.count()).select_from(SearchCriteria))
    assert count == 1


async def test_get_returns_latest_after_set(db_session: AsyncSession) -> None:
    manager = SearchCriteriaManager(db_session)
    await manager.set(_data("python"))
    await manager.set(_data("rust", "go"))
    current = await manager.get()
    assert current is not None
    assert current.data["keywords"] == ["rust", "go"]
