from datetime import date, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class _ProfileModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ProficiencyLevel(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class LanguageProficiency(StrEnum):
    elementary = "elementary"
    limited_working = "limited_working"
    professional_working = "professional_working"
    full_professional = "full_professional"
    native = "native"


class WorkMode(StrEnum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class LinkType(StrEnum):
    github = "github"
    linkedin = "linkedin"
    portfolio = "portfolio"
    website = "website"
    other = "other"


class Basics(_ProfileModel):
    full_name: str
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None


class Experience(_ProfileModel):
    company: str
    role: str
    employment_type: str | None = None
    location: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if self.is_current and self.end_date is not None:
            raise ValueError("end_date must be empty when is_current is true")
        if not self.is_current and self.end_date is None:
            raise ValueError("end_date is required when is_current is false")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must not be earlier than start_date")
        return self


class Project(_ProfileModel):
    name: str
    description: str | None = None
    role: str | None = None
    url: HttpUrl | None = None
    repository_url: HttpUrl | None = None
    start_date: date | None = None
    end_date: date | None = None
    highlights: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must not be earlier than start_date")
        return self


class TechnicalSkill(_ProfileModel):
    name: str
    category: str | None = None
    proficiency: ProficiencyLevel | None = None
    years_experience: float | None = None


class Education(_ProfileModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    location: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if self.is_current and self.end_date is not None:
            raise ValueError("end_date must be empty when is_current is true")
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must not be earlier than start_date")
        return self


class Certification(_ProfileModel):
    name: str
    issuer: str | None = None
    issue_date: date | None = None
    expiration_date: date | None = None
    credential_id: str | None = None
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        if (
            self.issue_date is not None
            and self.expiration_date is not None
            and self.expiration_date < self.issue_date
        ):
            raise ValueError("expiration_date must not be earlier than issue_date")
        return self


class Language(_ProfileModel):
    name: str
    proficiency: LanguageProficiency


class Link(_ProfileModel):
    url: HttpUrl
    type: LinkType | None = None
    label: str | None = None


class JobPreferences(_ProfileModel):
    desired_roles: list[str] = Field(default_factory=list)
    seniority_levels: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)
    work_modes: list[WorkMode] = Field(default_factory=list[WorkMode])
    locations: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    min_salary: int | None = None
    salary_currency: str | None = None
    accepted_languages: list[str] = Field(default_factory=list)
    employment_types: list[str] = Field(default_factory=list)
    open_to_relocation: bool | None = None
    availability: str | None = None


class MasterProfileData(_ProfileModel):
    basics: Basics
    experiences: list[Experience] = Field(default_factory=list[Experience])
    projects: list[Project] = Field(default_factory=list[Project])
    technical_skills: list[TechnicalSkill] = Field(default_factory=list[TechnicalSkill])
    interpersonal_skills: list[str] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list[Education])
    certifications: list[Certification] = Field(default_factory=list[Certification])
    languages: list[Language] = Field(default_factory=list[Language])
    links: list[Link] = Field(default_factory=list[Link])
    job_preferences: JobPreferences = Field(default_factory=JobPreferences)
    key_achievements: list[str] = Field(default_factory=list)


class ProfileVersionMeta(BaseModel):
    version_number: int
    created_at: datetime
    note: str | None = None


class ProfileVersionData(BaseModel):
    version_number: int
    created_at: datetime
    note: str | None = None
    data: MasterProfileData
