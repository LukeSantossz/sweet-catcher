import pytest
from pydantic import ValidationError

from app.profile.schemas import Experience, MasterProfileData


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
