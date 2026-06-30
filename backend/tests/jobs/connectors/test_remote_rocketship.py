import json
from typing import Any

import httpx2
import pytest

from app.jobs.connectors.http import PoliteClient
from app.jobs.connectors.remote_rocketship import RemoteRocketshipConnector
from app.jobs.normalization import normalize
from app.jobs.schemas import ContractType
from app.profile.schemas import WorkMode
from app.search.schemas import SearchCriteriaData

_JOB: dict[str, Any] = {
    "id": 19445192,
    "roleTitle": "Senior QA Engineer",
    "categorizedJobTitle": "QA Engineer",
    "company": {"name": "Growe Talents", "slug": "growe-talents"},
    "url": "https://boards.greenhouse.io/growetalents/jobs/4903682101",
    "jobDescriptionSummary": "Senior QA Engineer testing backend services.",
    "location": "Worldwide",
    "locationType": "remote",
    "employmentType": "full-time",
    "created_at": "2026-06-30T11:57:16.455+00:00",
    "techStack": ["Grafana", "Kafka", "SQL"],
    "requiredLanguages": ["en"],
    "salaryRange": None,
}


def _html(jobs: list[dict[str, Any]]) -> str:
    next_data = {"props": {"pageProps": {"initialJobOpenings": jobs}}}
    script = json.dumps(next_data)
    return (
        '<html><body><script id="__NEXT_DATA__" type="application/json">'
        f"{script}</script></body></html>"
    )


def _client(html: str, *, calls: list[int] | None = None) -> PoliteClient:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if calls is not None:
            calls.append(1)
        return httpx2.Response(200, html=html)

    return PoliteClient(transport=httpx2.MockTransport(handler), min_interval=0.0)


async def test_remote_rocketship_extracts_jobs_from_next_data() -> None:
    connector = RemoteRocketshipConnector(_client(_html([_JOB])))

    raws = await connector.fetch(SearchCriteriaData())

    assert connector.name == "remote_rocketship"
    assert len(raws) == 1
    raw = raws[0]
    assert raw.source == "remote_rocketship"
    assert raw.external_id == "19445192"
    payload = raw.payload
    assert payload["title"] == "Senior QA Engineer"
    assert payload["company"] == "Growe Talents"
    assert payload["url"].endswith("/4903682101")
    assert payload["work_mode"] == WorkMode.remote.value
    assert payload["contract_type"] == ContractType.full_time.value
    assert payload["technologies"] == ["Grafana", "Kafka", "SQL"]
    assert payload["languages"] == ["en"]
    assert payload["posted_at"] == "2026-06-30"
    assert payload["source_raw"]["id"] == 19445192


async def test_remote_rocketship_maps_salary_range_when_present() -> None:
    job = {**_JOB, "salaryRange": {"min": 150000, "max": 160000, "currencyCode": "USD"}}
    connector = RemoteRocketshipConnector(_client(_html([job])))

    payload = (await connector.fetch(SearchCriteriaData()))[0].payload

    assert payload["salary_min"] == 150000
    assert payload["salary_max"] == 160000
    assert payload["salary_currency"] == "USD"


async def test_remote_rocketship_produced_rawjobs_normalize_into_valid_jobdata() -> None:
    connector = RemoteRocketshipConnector(_client(_html([_JOB])))

    job = normalize((await connector.fetch(SearchCriteriaData()))[0])

    assert job.title == "Senior QA Engineer"
    assert job.company == "Growe Talents"
    assert job.work_mode == WorkMode.remote
    assert job.contract_type == ContractType.full_time
    assert job.technologies == ["Grafana", "Kafka", "SQL"]
    assert job.posted_at is not None
    assert job.posted_at.isoformat() == "2026-06-30"


async def test_remote_rocketship_raises_when_next_data_is_missing() -> None:
    connector = RemoteRocketshipConnector(_client("<html><body>no data here</body></html>"))

    with pytest.raises(ValueError):
        await connector.fetch(SearchCriteriaData())


async def test_remote_rocketship_respects_page_cap() -> None:
    calls: list[int] = []
    connector = RemoteRocketshipConnector(_client(_html([_JOB]), calls=calls), max_pages=2)

    await connector.fetch(SearchCriteriaData())

    assert len(calls) == 2  # capped at max_pages even though every page still returns jobs
