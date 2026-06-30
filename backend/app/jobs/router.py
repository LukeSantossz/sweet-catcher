from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.jobs.connectors import default_connectors
from app.jobs.models import Job
from app.jobs.schemas import JobData, RunSummary
from app.jobs.service import DiscoveryService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/discover", response_model=RunSummary)
async def discover(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RunSummary:
    return await DiscoveryService(session, default_connectors()).run()


@router.get("", response_model=list[JobData])
async def list_jobs(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[JobData]:
    result = await session.execute(select(Job).order_by(Job.first_seen_at.desc()))
    return [JobData.model_validate(row, from_attributes=True) for row in result.scalars()]
