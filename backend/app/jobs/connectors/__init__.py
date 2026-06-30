from typing import Protocol

from app.jobs.schemas import RawJob
from app.search.schemas import SearchCriteriaData


class SourceConnector(Protocol):
    name: str

    async def fetch(self, criteria: SearchCriteriaData) -> list[RawJob]: ...


class MockConnector:
    """Deterministic in-memory source connector for development and tests."""

    name = "mock"

    def __init__(self, jobs: list[RawJob] | None = None) -> None:
        self._jobs = list(jobs) if jobs is not None else _sample_jobs()

    async def fetch(self, criteria: SearchCriteriaData) -> list[RawJob]:
        return list(self._jobs)


def _sample_jobs() -> list[RawJob]:
    return [
        RawJob(
            source="mock",
            external_id="mock-1",
            payload={
                "title": "Junior Backend Engineer",
                "company": "Acme",
                "url": "https://acme.example/jobs/mock-1",
                "description": "Build and maintain Python APIs.",
                "location": "Remote",
                "work_mode": "remote",
                "contract_type": "full_time",
                "technologies": ["python", "fastapi", "postgresql"],
            },
        ),
        RawJob(
            source="mock",
            external_id="mock-2",
            payload={
                "title": "Data Engineer",
                "company": "Globex",
                "url": "https://globex.example/jobs/mock-2",
                "description": "Design and operate data pipelines.",
                "location": "Hybrid - Lisbon",
                "work_mode": "hybrid",
                "technologies": ["python", "airflow"],
            },
        ),
    ]


def default_connectors() -> list[SourceConnector]:
    connectors: list[SourceConnector] = [MockConnector()]
    return connectors
