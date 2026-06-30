from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.jobs.connectors import default_connectors
from app.jobs.models import Job
from app.jobs.schemas import JobSummary, RunSummary
from app.jobs.service import DiscoveryService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/discover", response_model=RunSummary)
async def discover(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RunSummary:
    return await DiscoveryService(session, default_connectors()).run()


@router.get("", response_model=list[JobSummary])
async def list_jobs(
    limit: int = Query(default=50, ge=1, le=100),  # noqa: B008
    offset: int = Query(default=0, ge=0),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[JobSummary]:
    result = await session.execute(
        select(Job).order_by(Job.first_seen_at.desc(), Job.id.desc()).limit(limit).offset(offset)
    )
    return [JobSummary.model_validate(row, from_attributes=True) for row in result.scalars()]
