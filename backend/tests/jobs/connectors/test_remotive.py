from typing import Any

import httpx2

from app.jobs.connectors.http import PoliteClient
from app.jobs.connectors.remotive import RemotiveConnector
from app.jobs.normalization import normalize
from app.jobs.schemas import ContractType
from app.profile.schemas import WorkMode
from app.search.schemas import SearchCriteriaData

_SAMPLE: dict[str, Any] = {
    "0-legal-notice": "Remotive attribution notice",
    "jobs": [
        {
            "id": 2091038,
            "title": "Sales Assistant ",
            "company_name": "Endureed ",
            "url": "https://remotive.com/remote-jobs/sales/sales-assistant-2091038",
            "category": "Sales",
            "job_type": "full_time",
            "publication_date": "2026-06-26T14:55:18",
            "candidate_required_location": "USA",
            "salary": "$20k-$25k",
            "tags": ["research", "CRM"],
            "description": "<p>Do sales things</p>",
        }
    ],
}


def _client(payload: dict[str, Any], *, capture: dict[str, str] | None = None) -> PoliteClient:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if capture is not None:
            capture["url"] = str(request.url)
        return httpx2.Response(200, json=payload)

    return PoliteClient(transport=httpx2.MockTransport(handler), min_interval=0.0)


async def test_remotive_maps_api_jobs_to_rawjobs() -> None:
    capture: dict[str, str] = {}
    connector = RemotiveConnector(_client(_SAMPLE, capture=capture))

    raws = await connector.fetch(SearchCriteriaData())

    assert connector.name == "remotive"
    assert "/api/remote-jobs" in capture["url"]
    assert len(raws) == 1
    raw = raws[0]
    assert raw.source == "remotive"
    assert raw.external_id == "2091038"
    payload = raw.payload
    assert payload["title"] == "Sales Assistant"
    assert payload["company"] == "Endureed"
    assert payload["url"].endswith("sales-assistant-2091038")
    assert payload["work_mode"] == WorkMode.remote.value
    assert payload["contract_type"] == ContractType.full_time.value
    assert payload["location"] == "USA"
    assert payload["technologies"] == ["research", "CRM"]
    assert payload["posted_at"] == "2026-06-26"
    assert payload["source_raw"]["id"] == 2091038


async def test_remotive_produced_rawjobs_normalize_into_valid_jobdata() -> None:
    connector = RemotiveConnector(_client(_SAMPLE))

    job = normalize((await connector.fetch(SearchCriteriaData()))[0])

    assert job.title == "Sales Assistant"
    assert job.company == "Endureed"
    assert job.work_mode == WorkMode.remote
    assert job.contract_type == ContractType.full_time
    assert job.posted_at is not None
    assert job.posted_at.isoformat() == "2026-06-26"


async def test_remotive_returns_empty_list_when_api_has_no_jobs() -> None:
    connector = RemotiveConnector(_client({"jobs": []}))

    raws = await connector.fetch(SearchCriteriaData())

    assert raws == []
