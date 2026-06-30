from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.connectors import SourceConnector
from app.jobs.dedup import DuplicateIndex
from app.jobs.models import Job
from app.jobs.normalization import normalize
from app.jobs.schemas import JobData, RunSummary, SourceResult
from app.search.schemas import SearchCriteriaData
from app.search.service import SearchCriteriaManager

_IDENTITY_COLUMNS = ("source", "source_external_id")


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


def _mutable_columns(job: JobData) -> dict[str, Any]:
    # Identity columns (source, source_external_id) are never overwritten on update; a row
    # is only ever matched by its own identity, so updates touch the mutable fields only.
    return {key: value for key, value in _to_columns(job).items() if key not in _IDENTITY_COLUMNS}


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
        # Boundary: a source's fetch failure must not abort the run (FR #5).
        try:
            raw_jobs = await connector.fetch(criteria)
        except Exception as exc:
            result.error = f"{type(exc).__name__}: {exc}"
            return result
        result.found = len(raw_jobs)
        jobs: list[JobData] = []
        for raw in raw_jobs:
            # Per-job isolation: a malformed payload skips that job, not the whole run (FR #5).
            try:
                jobs.append(normalize(raw))
            except Exception:
                result.skipped += 1
        await self._persist_batch(jobs, result)
        return result

    async def _persist_batch(self, jobs: list[JobData], result: SourceResult) -> None:
        if not jobs:
            return
        existing = await self._load_existing(jobs)
        pending: dict[tuple[str, str], Job] = {}
        index = DuplicateIndex()
        for job in jobs:
            if index.is_duplicate(job):
                # Cross-posting duplicate: flagged, but still persisted (FR #8) — never dropped.
                result.duplicates += 1
            index.add(job)
            key = (job.source, job.source_external_id)
            row = existing.get(key) or pending.get(key)
            if row is None:
                new_row = Job(**_to_columns(job))
                self._session.add(new_row)
                pending[key] = new_row
                result.created += 1
            else:
                for column, value in _mutable_columns(job).items():
                    setattr(row, column, value)
                row.last_seen_at = datetime.now(UTC)
                if key in existing:
                    result.updated += 1
        await self._session.flush()

    async def _load_existing(self, jobs: list[JobData]) -> dict[tuple[str, str], Job]:
        keys = list({(job.source, job.source_external_id) for job in jobs})
        result = await self._session.execute(
            select(Job).where(tuple_(Job.source, Job.source_external_id).in_(keys))
        )
        return {(row.source, row.source_external_id): row for row in result.scalars()}
