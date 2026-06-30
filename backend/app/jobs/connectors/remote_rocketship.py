import json
from html.parser import HTMLParser
from typing import Any

from app.jobs.connectors.http import PoliteClient
from app.jobs.connectors.mapping import (
    as_dict,
    as_dict_list,
    clean_str,
    coerce_id,
    coerce_salary_amount,
    map_contract_type,
    map_work_mode,
    str_list,
    to_iso_date,
)
from app.jobs.schemas import RawJob
from app.search.schemas import SearchCriteriaData

_BASE_URL = "https://www.remoterocketship.com/"


class _NextDataParser(HTMLParser):
    """Captures the text content of the Next.js ``<script id="__NEXT_DATA__">`` tag regardless of
    attribute order. Script content is CDATA to HTMLParser, so the embedded JSON is returned
    verbatim — a more stable extraction target than the rendered DOM."""

    def __init__(self) -> None:
        super().__init__()
        self._capturing = False
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self._capturing = True

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._capturing = False

    @property
    def payload(self) -> str:
        return "".join(self._chunks)


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
        parser = _NextDataParser()
        parser.feed(html)
        if not parser.payload:
            raise ValueError("Remote Rocketship page is missing the __NEXT_DATA__ payload")
        data = json.loads(parser.payload)
        page_props = as_dict(as_dict(as_dict(data).get("props")).get("pageProps"))
        return as_dict_list(page_props.get("initialJobOpenings"))

    def _to_raw(self, job: dict[str, Any]) -> RawJob:
        company = as_dict(job.get("company"))
        payload: dict[str, Any] = {
            "title": clean_str(job.get("roleTitle") or job.get("categorizedJobTitle")),
            "company": clean_str(company.get("name")),
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
        return RawJob(source=self.name, external_id=coerce_id(job.get("id")), payload=payload)

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
