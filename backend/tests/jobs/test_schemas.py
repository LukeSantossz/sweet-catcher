from typing import Any

import pytest
from pydantic import ValidationError

from app.jobs.schemas import (
    ContractType,
    JobData,
    JobStatus,
    RawJob,
    RunSummary,
    SourceResult,
)
from app.profile.schemas import WorkMode


def _job(**over: Any) -> JobData:
    base: dict[str, Any] = {
        "source": "mock",
        "source_external_id": "1",
        "title": "Backend Engineer",
        "company": "Acme",
        "url": "https://acme.example/jobs/1",
        "canonical_url": "https://acme.example/jobs/1",
    }
    base.update(over)
    return JobData(**base)


def test_jobdata_requires_canonical_url() -> None:
    with pytest.raises(ValidationError):
        JobData.model_validate(
            {
                "source": "mock",
                "source_external_id": "1",
                "title": "x",
                "company": "y",
                "url": "https://acme.example/jobs/1",
            }
        )


def test_jobdata_defaults() -> None:
    job = _job()
    assert job.status == JobStatus.open
    assert job.technologies == []
    assert job.raw == {}


def test_jobdata_parses_enums() -> None:
    job = _job(work_mode="remote", contract_type="full_time")
    assert job.work_mode == WorkMode.remote
    assert job.contract_type == ContractType.full_time


def test_jobdata_rejects_negative_salary() -> None:
    with pytest.raises(ValidationError):
        _job(salary_min=-1)


def test_rawjob_holds_payload() -> None:
    raw = RawJob(source="mock", external_id="1", payload={"title": "x"})
    assert raw.payload["title"] == "x"


def test_runsummary_aggregates_totals() -> None:
    summary = RunSummary(
        sources=[
            SourceResult(source="mock", found=3, created=2, updated=1, duplicates=0),
            SourceResult(source="other", found=1, created=0, updated=1, duplicates=0),
        ]
    )
    assert summary.found == 4
    assert summary.created == 2
    assert summary.updated == 2


def test_jobdata_rejects_transposed_salary() -> None:
    with pytest.raises(ValidationError):
        _job(salary_min=120000, salary_max=80000)
