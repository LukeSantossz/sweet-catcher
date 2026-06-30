from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.search.models import SearchCriteria
from app.search.schemas import SearchCriteriaData


class SearchCriteriaManager:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> SearchCriteria | None:
        # Single-user V1: at most one search_criteria row exists, so no id filter is needed.
        result = await self._session.execute(select(SearchCriteria).limit(1))
        return result.scalar_one_or_none()

    async def set(self, data: SearchCriteriaData) -> SearchCriteria:
        payload = data.model_dump(mode="json")
        criteria = await self.get()
        if criteria is None:
            criteria = SearchCriteria(data=payload)
            self._session.add(criteria)
        else:
            criteria.data = payload
        await self._session.flush()
        await self._session.refresh(criteria)
        return criteria
