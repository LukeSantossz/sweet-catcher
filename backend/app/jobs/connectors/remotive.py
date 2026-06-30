from typing import Any

from app.jobs.connectors.http import PoliteClient
from app.jobs.connectors.mapping import (
    as_dict,
    as_dict_list,
    map_contract_type,
    str_list,
    to_iso_date,
)
from app.jobs.schemas import RawJob
from app.profile.schemas import WorkMode
from app.search.schemas import SearchCriteriaData

_BASE_URL = "https://remotive.com/api/remote-jobs"


class RemotiveConnector:
    """Reads the public Remotive JSON API. Every Remotive posting is remote, so work mode is
    fixed; the original job object is retained under ``source_raw`` (ADR 0007/0008)."""

    name = "remotive"

    def __init__(self, client: PoliteClient | None = None, *, limit: int = 50) -> None:
        self._client = client or PoliteClient()
        self._limit = limit

    async def fetch(self, criteria: SearchCriteriaData) -> list[RawJob]:
        # criteria is unused in V1: Remotive's default feed is fetched and source selection
        # happens via SearchCriteria.active_sources (ADR 0008).
        data = await self._client.get_json(_BASE_URL, params={"limit": self._limit})
        return [self._to_raw(job) for job in as_dict_list(as_dict(data).get("jobs"))]

    def _to_raw(self, job: dict[str, Any]) -> RawJob:
        payload: dict[str, Any] = {
            "title": str(job.get("title", "")).strip(),
            "company": str(job.get("company_name", "")).strip(),
            "url": job.get("url"),
            "description": job.get("description"),
            "location": job.get("candidate_required_location") or None,
            "work_mode": WorkMode.remote.value,
            "contract_type": map_contract_type(job.get("job_type")),
            "posted_at": to_iso_date(job.get("publication_date")),
            "technologies": str_list(job.get("tags")),
            "source_raw": job,
        }
        return RawJob(source=self.name, external_id=str(job.get("id", "")), payload=payload)
