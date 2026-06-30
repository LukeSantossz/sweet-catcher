from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.connectors import SourceConnector
from app.jobs.dedup import is_duplicate, is_probable_duplicate
from app.jobs.models import Job
from app.jobs.normalization import normalize
from app.jobs.schemas import JobData, RunSummary, SourceResult
from app.search.schemas import SearchCriteriaData
from app.search.service import SearchCriteriaManager


def _to_columns(job: JobData) -> dict[str, Any]:
    return {
        "source": job.source,
        "source_external_id": job.source_external_id,
        "title": job.title,
        "company": job.company,
        "url": job.url,
        "canonical_url": job.canonical_url,
        "description": job.description,
        "description_hash": job.description_hash,
        "location": job.location,
        "work_mode": job.work_mode.value if job.work_mode is not None else None,
        "contract_type": job.contract_type.value if job.contract_type is not None else None,
        "posted_at": job.posted_at,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "technologies": job.technologies,
        "languages": job.languages,
        "status": job.status.value,
        "raw": job.raw,
    }


class DiscoveryService:
    def __init__(self, session: AsyncSession, connectors: Sequence[SourceConnector]) -> None:
        self._session = session
        self._connectors = {connector.name: connector for connector in connectors}

    async def run(self) -> RunSummary:
        criteria = await self._load_criteria()
        summary = RunSummary()
        for name in criteria.active_sources:
            connector = self._connectors.get(name)
            if connector is not None:
                summary.sources.append(await self._run_connector(connector, criteria))
        return summary

    async def _load_criteria(self) -> SearchCriteriaData:
        row = await SearchCriteriaManager(self._session).get()
        if row is None:
            return SearchCriteriaData()
        return SearchCriteriaData.model_validate(row.data)

    async def _run_connector(
        self, connector: SourceConnector, criteria: SearchCriteriaData
    ) -> SourceResult:
        result = SourceResult(source=connector.name)
        # Boundary: isolate per-source failures so one bad source cannot abort the run (FR #5).
        try:
            raw_jobs = await connector.fetch(criteria)
        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            return result
        result.found = len(raw_jobs)
        seen: list[JobData] = []
        for raw in raw_jobs:
            job = normalize(raw)
            if any(is_duplicate(job, prior) or is_probable_duplicate(job, prior) for prior in seen):
                result.duplicates += 1
                continue
            seen.append(job)
            if await self._persist(job) == "created":
                result.created += 1
            else:
                result.updated += 1
        return result

    async def _persist(self, job: JobData) -> str:
        existing = await self._find_existing(job)
        if existing is not None:
            for key, value in _to_columns(job).items():
                setattr(existing, key, value)
            existing.last_seen_at = datetime.now(UTC)
            await self._session.flush()
            return "updated"
        self._session.add(Job(**_to_columns(job)))
        await self._session.flush()
        return "created"

    async def _find_existing(self, job: JobData) -> Job | None:
        conditions = [
            and_(Job.source == job.source, Job.source_external_id == job.source_external_id)
        ]
        if job.canonical_url:
            conditions.append(Job.canonical_url == job.canonical_url)
        if job.description_hash is not None:
            conditions.append(Job.description_hash == job.description_hash)
        result = await self._session.execute(select(Job).where(or_(*conditions)).limit(1))
        return result.scalar_one_or_none()
