import json
from typing import Any

from app.jobs.connectors.http import PoliteClient
from app.jobs.connectors.mapping import (
    as_dict,
    as_dict_list,
    coerce_salary_amount,
    map_contract_type,
    map_work_mode,
    str_list,
    to_iso_date,
)
from app.jobs.schemas import RawJob
from app.search.schemas import SearchCriteriaData

_BASE_URL = "https://www.remoterocketship.com/"
# Remote Rocketship is a Next.js Pages Router app; the full listing is embedded as JSON in the
# standard __NEXT_DATA__ script tag, a far more stable extraction target than the rendered DOM.
_NEXT_DATA_MARKER = '<script id="__NEXT_DATA__"'


class RemoteRocketshipConnector:
    """Extracts postings from Remote Rocketship's embedded Next.js __NEXT_DATA__ payload
    (props.pageProps.initialJobOpenings), retaining the original object under source_raw."""

    name = "remote_rocketship"

    def __init__(self, client: PoliteClient | None = None, *, max_pages: int = 1) -> None:
        self._client = client or PoliteClient()
        self._max_pages = max_pages

    async def fetch(self, criteria: SearchCriteriaData) -> list[RawJob]:
        # criteria is unused in V1: the listing is fetched unfiltered (recent first) and source
        # selection happens via SearchCriteria.active_sources (ADR 0008).
        raws: list[RawJob] = []
        for page in range(1, self._max_pages + 1):
            html = await self._client.get_text(
                _BASE_URL, params={"sort": "DateAdded", "page": page}
            )
            jobs = self._extract_jobs(html)
            if not jobs:
                break
            raws.extend(self._to_raw(job) for job in jobs)
        return raws

    def _extract_jobs(self, html: str) -> list[dict[str, Any]]:
        # Locate the script via plain string search (linear, no backtracking regex) and slice its
        # JSON body out to the next closing tag.
        start = html.find(_NEXT_DATA_MARKER)
        if start == -1:
            raise ValueError("Remote Rocketship page is missing the __NEXT_DATA__ payload")
        body_start = html.find(">", start)
        body_end = html.find("</script>", body_start) if body_start != -1 else -1
        if body_start == -1 or body_end == -1:
            raise ValueError("Remote Rocketship __NEXT_DATA__ script is malformed")
        data = json.loads(html[body_start + 1 : body_end])
        page_props = as_dict(as_dict(as_dict(data).get("props")).get("pageProps"))
        return as_dict_list(page_props.get("initialJobOpenings"))

    def _to_raw(self, job: dict[str, Any]) -> RawJob:
        company = as_dict(job.get("company"))
        title = job.get("roleTitle") or job.get("categorizedJobTitle") or ""
        payload: dict[str, Any] = {
            "title": str(title).strip(),
            "company": str(company.get("name", "")).strip(),
            "url": job.get("url"),
            "description": job.get("jobDescriptionSummary"),
            "location": job.get("location"),
            "work_mode": map_work_mode(job.get("locationType")),
            "contract_type": map_contract_type(job.get("employmentType")),
            "posted_at": to_iso_date(job.get("created_at")),
            "technologies": str_list(job.get("techStack")),
            "languages": str_list(job.get("requiredLanguages")),
            "source_raw": job,
        }
        self._add_salary(payload, as_dict(job.get("salaryRange")))
        return RawJob(source=self.name, external_id=str(job.get("id", "")), payload=payload)

    @staticmethod
    def _add_salary(payload: dict[str, Any], salary: dict[str, Any]) -> None:
        salary_min = coerce_salary_amount(salary.get("min"))
        salary_max = coerce_salary_amount(salary.get("max"))
        currency = salary.get("currencyCode")
        if salary_min is not None:
            payload["salary_min"] = salary_min
        if salary_max is not None:
            payload["salary_max"] = salary_max
        if isinstance(currency, str):
            payload["salary_currency"] = currency
