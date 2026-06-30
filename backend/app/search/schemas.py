from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.profile.schemas import WorkMode


class _SearchModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RunFrequency(StrEnum):
    daily = "daily"
    weekly = "weekly"


class SearchCriteriaData(_SearchModel):
    keywords: list[str] = Field(default_factory=list)
    allowed_seniorities: list[str] = Field(default_factory=list)
    blocked_seniorities: list[str] = Field(default_factory=list)
    allowed_areas: list[str] = Field(default_factory=list)
    blocked_areas: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    work_modes: list[WorkMode] = Field(default_factory=list[WorkMode])
    min_salary: int | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    accepted_languages: list[str] = Field(default_factory=list)
    required_technologies: list[str] = Field(default_factory=list)
    desired_technologies: list[str] = Field(default_factory=list)
    favorite_companies: list[str] = Field(default_factory=list)
    blocked_companies: list[str] = Field(default_factory=list)
    active_sources: list[str] = Field(default_factory=list)
    run_frequency: RunFrequency = RunFrequency.daily

    @model_validator(mode="after")
    def _reject_allow_block_overlap(self) -> Self:
        conflicts = [
            ("seniorities", self.allowed_seniorities, self.blocked_seniorities),
            ("areas", self.allowed_areas, self.blocked_areas),
            ("companies", self.favorite_companies, self.blocked_companies),
        ]
        for label, included, blocked in conflicts:
            overlap = sorted(set(included) & set(blocked))
            if overlap:
                raise ValueError(f"{label} present in both include and block lists: {overlap}")
        return self


class SearchCriteriaRead(BaseModel):
    updated_at: datetime
    data: SearchCriteriaData
