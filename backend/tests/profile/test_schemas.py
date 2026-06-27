import pytest
from pydantic import ValidationError

from app.profile.schemas import Certification, Education, Experience, MasterProfileData, Project


def test_requires_full_name() -> None:
    with pytest.raises(ValidationError):
        MasterProfileData.model_validate({"basics": {}})


def test_minimal_profile_is_valid() -> None:
    profile = MasterProfileData.model_validate({"basics": {"full_name": "Ada Lovelace"}})
    assert profile.basics.full_name == "Ada Lovelace"
    assert profile.experiences == []
    assert profile.key_achievements == []


def test_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        Experience.model_validate(
            {
                "company": "Acme",
                "role": "Dev",
                "start_date": "2023-01-01",
                "end_date": "2022-01-01",
            }
        )


def test_is_current_forbids_end_date() -> None:
    with pytest.raises(ValidationError):
        Experience.model_validate(
            {
                "company": "Acme",
                "role": "Dev",
                "start_date": "2023-01-01",
                "end_date": "2024-01-01",
                "is_current": True,
            }
        )


def test_not_current_requires_end_date() -> None:
    with pytest.raises(ValidationError):
        Experience.model_validate({"company": "Acme", "role": "Dev", "start_date": "2023-01-01"})


def test_ignores_unknown_fields() -> None:
    profile = MasterProfileData.model_validate({"basics": {"full_name": "Ada"}, "unexpected": "x"})
    assert not hasattr(profile, "unexpected")


def test_accepts_key_achievements() -> None:
    profile = MasterProfileData.model_validate(
        {"basics": {"full_name": "Ada"}, "key_achievements": ["Cut latency by 60%"]}
    )
    assert profile.key_achievements == ["Cut latency by 60%"]


# --- Finding 1: cross-field date validation on Project, Education, Certification ---


def test_project_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        Project.model_validate(
            {"name": "Widget", "start_date": "2023-06-01", "end_date": "2023-01-01"}
        )


def test_project_accepts_valid_dates() -> None:
    project = Project.model_validate(
        {"name": "Widget", "start_date": "2023-01-01", "end_date": "2023-06-01"}
    )
    assert project.name == "Widget"


def test_education_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        Education.model_validate(
            {
                "institution": "MIT",
                "start_date": "2022-09-01",
                "end_date": "2021-09-01",
            }
        )


def test_education_accepts_valid_dates() -> None:
    edu = Education.model_validate(
        {"institution": "MIT", "start_date": "2020-09-01", "end_date": "2024-06-01"}
    )
    assert edu.institution == "MIT"


def test_certification_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        Certification.model_validate(
            {
                "name": "AWS SAA",
                "issue_date": "2024-03-01",
                "expiration_date": "2023-03-01",
            }
        )


def test_certification_accepts_valid_dates() -> None:
    cert = Certification.model_validate(
        {"name": "AWS SAA", "issue_date": "2023-03-01", "expiration_date": "2026-03-01"}
    )
    assert cert.name == "AWS SAA"
