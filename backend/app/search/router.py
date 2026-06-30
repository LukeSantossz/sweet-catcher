from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.search.models import SearchCriteria
from app.search.schemas import SearchCriteriaData, SearchCriteriaRead
from app.search.service import SearchCriteriaManager

router = APIRouter(prefix="/search-criteria", tags=["search-criteria"])


def get_manager(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> SearchCriteriaManager:
    return SearchCriteriaManager(session)


def _to_read(criteria: SearchCriteria) -> SearchCriteriaRead:
    return SearchCriteriaRead(
        updated_at=criteria.updated_at,
        data=SearchCriteriaData.model_validate(criteria.data),
    )


@router.get("", response_model=SearchCriteriaRead)
async def get_search_criteria(
    manager: SearchCriteriaManager = Depends(get_manager),  # noqa: B008
) -> SearchCriteriaRead:
    criteria = await manager.get()
    if criteria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no search criteria yet")
    return _to_read(criteria)


@router.put("", response_model=SearchCriteriaRead)
async def put_search_criteria(
    data: SearchCriteriaData,
    response: Response,
    manager: SearchCriteriaManager = Depends(get_manager),  # noqa: B008
) -> SearchCriteriaRead:
    before = await manager.get()
    criteria = await manager.set(data)
    response.status_code = status.HTTP_201_CREATED if before is None else status.HTTP_200_OK
    return _to_read(criteria)
