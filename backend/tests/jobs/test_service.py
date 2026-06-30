from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.connectors import MockConnector
from app.jobs.models import Job
from app.jobs.schemas import RawJob
from app.jobs.service import DiscoveryService
from app.search.schemas import SearchCriteriaData
from app.search.service import SearchCriteriaManager


def _raw(external_id: str, **payload: Any) -> RawJob:
    payload.setdefault("title", f"Job {external_id}")
    payload.setdefault("company", "Acme")
    payload.setdefault("url", f"https://acme.example/jobs/{external_id}")
    return RawJob(source="mock", external_id=external_id, payload=payload)


async def _set_active(session: AsyncSession, *sources: str) -> None:
    await SearchCriteriaManager(session).set(SearchCriteriaData(active_sources=list(sources)))


async def _count_jobs(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(Job)) or 0


async def test_run_persists_new_jobs(db_session: AsyncSession) -> None:
    await _set_active(db_session, "mock")
    connector = MockConnector([_raw("1"), _raw("2")])
    summary = await DiscoveryService(db_session, [connector]).run()
    assert summary.created == 2
    assert await _count_jobs(db_session) == 2


async def test_rerun_is_idempotent(db_session: AsyncSession) -> None:
    await _set_active(db_session, "mock")
    connector = MockConnector([_raw("1"), _raw("2")])
    await DiscoveryService(db_session, [connector]).run()
    summary = await DiscoveryService(db_session, [connector]).run()
    assert summary.created == 0
    assert summary.updated == 2
    assert await _count_jobs(db_session) == 2


async def test_isolates_connector_errors(db_session: AsyncSession) -> None:
    await _set_active(db_session, "good", "bad")

    class GoodConnector:
        name = "good"

        async def fetch(self, criteria: SearchCriteriaData) -> list[RawJob]:
            return [_raw("1")]

    class BadConnector:
        name = "bad"

        async def fetch(self, criteria: SearchCriteriaData) -> list[RawJob]:
            raise RuntimeError("boom")

    summary = await DiscoveryService(db_session, [GoodConnector(), BadConnector()]).run()
    assert await _count_jobs(db_session) == 1
    errors = {result.source: result.error for result in summary.sources}
    assert errors["good"] is None
    assert errors["bad"] is not None


async def test_runs_only_active_sources(db_session: AsyncSession) -> None:
    await _set_active(db_session, "mock")
    mock = MockConnector([_raw("1")])

    class OtherConnector:
        name = "other"

        async def fetch(self, criteria: SearchCriteriaData) -> list[RawJob]:
            raise AssertionError("inactive connector must not be called")

    summary = await DiscoveryService(db_session, [mock, OtherConnector()]).run()
    assert summary.created == 1
    assert [result.source for result in summary.sources] == ["mock"]


async def test_isolates_malformed_payload(db_session: AsyncSession) -> None:
    await _set_active(db_session, "mock")
    good = _raw("1")
    bad = RawJob(
        source="mock",
        external_id="bad",
        payload={
            "title": "X",
            "company": "Y",
            "url": "https://z.example/bad",
            "work_mode": "on-site",
        },
    )
    summary = await DiscoveryService(db_session, [MockConnector([good, bad])]).run()
    source = summary.sources[0]
    assert source.created == 1
    assert source.skipped == 1
    assert await _count_jobs(db_session) == 1


async def test_flags_duplicate_without_dropping(db_session: AsyncSession) -> None:
    await _set_active(db_session, "mock")
    first = _raw("1", description="identical role")
    second = _raw("2", description="identical role")
    summary = await DiscoveryService(db_session, [MockConnector([first, second])]).run()
    source = summary.sources[0]
    assert source.created == 2
    assert source.duplicates == 1
    assert await _count_jobs(db_session) == 2


async def test_unknown_active_source_is_reported(db_session: AsyncSession) -> None:
    await _set_active(db_session, "mock", "ghost")
    summary = await DiscoveryService(db_session, [MockConnector([_raw("1")])]).run()
    results = {result.source: result for result in summary.sources}
    assert results["mock"].created == 1
    assert results["ghost"].error is not None


async def test_flags_duplicate_across_connectors(db_session: AsyncSession) -> None:
    await _set_active(db_session, "a", "b")
    shared = "https://x.example/jobs/shared"

    class A:
        name = "a"

        async def fetch(self, criteria: SearchCriteriaData) -> list[RawJob]:
            payload = {"title": "T", "company": "C", "url": shared}
            return [RawJob(source="a", external_id="1", payload=payload)]

    class B:
        name = "b"

        async def fetch(self, criteria: SearchCriteriaData) -> list[RawJob]:
            payload = {"title": "T", "company": "C", "url": shared}
            return [RawJob(source="b", external_id="2", payload=payload)]

    summary = await DiscoveryService(db_session, [A(), B()]).run()
    assert summary.created == 2
    assert summary.duplicates == 1
