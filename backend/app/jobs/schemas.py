from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.profile.schemas import WorkMode


class _JobModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ContractType(StrEnum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"
    temporary = "temporary"
    freelance = "freelance"


class JobStatus(StrEnum):
    open = "open"
    closed = "closed"
    unknown = "unknown"


class RawJob(_JobModel):
    source: str
    external_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class JobData(_JobModel):
    source: str
    source_external_id: str
    title: str
    company: str
    url: str
    canonical_url: str
    description: str | None = None
    description_hash: str | None = None
    location: str | None = None
    work_mode: WorkMode | None = None
    contract_type: ContractType | None = None
    posted_at: date | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    technologies: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    status: JobStatus = JobStatus.open
    raw: dict[str, Any] = Field(default_factory=dict)


class SourceResult(BaseModel):
    source: str
    found: int = 0
    created: int = 0
    updated: int = 0
    duplicates: int = 0
    error: str | None = None


class RunSummary(BaseModel):
    sources: list[SourceResult] = Field(default_factory=list[SourceResult])

    @computed_field
    @property
    def found(self) -> int:
        return sum(result.found for result in self.sources)

    @computed_field
    @property
    def created(self) -> int:
        return sum(result.created for result in self.sources)

    @computed_field
    @property
    def updated(self) -> int:
        return sum(result.updated for result in self.sources)

    @computed_field
    @property
    def duplicates(self) -> int:
        return sum(result.duplicates for result in self.sources)
