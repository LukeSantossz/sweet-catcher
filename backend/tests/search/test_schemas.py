import pytest
from pydantic import ValidationError

from app.profile.schemas import WorkMode
from app.search.schemas import RunFrequency, SearchCriteriaData


def test_accepts_empty_criteria() -> None:
    criteria = SearchCriteriaData()
    assert criteria.keywords == []
    assert criteria.min_salary is None
    assert criteria.run_frequency == RunFrequency.daily


def test_rejects_negative_min_salary() -> None:
    with pytest.raises(ValidationError):
        SearchCriteriaData(min_salary=-1)


def test_rejects_overlapping_seniorities() -> None:
    with pytest.raises(ValidationError):
        SearchCriteriaData(allowed_seniorities=["junior"], blocked_seniorities=["junior"])


def test_rejects_overlapping_areas() -> None:
    with pytest.raises(ValidationError):
        SearchCriteriaData(allowed_areas=["backend"], blocked_areas=["backend"])


def test_rejects_company_in_favorite_and_blocked() -> None:
    with pytest.raises(ValidationError):
        SearchCriteriaData(favorite_companies=["Acme"], blocked_companies=["Acme"])


def test_ignores_unknown_fields() -> None:
    criteria = SearchCriteriaData.model_validate({"keywords": ["python"], "unknown_field": "x"})
    assert criteria.keywords == ["python"]
    assert not hasattr(criteria, "unknown_field")


def test_parses_enums_in_payload() -> None:
    criteria = SearchCriteriaData.model_validate(
        {"work_modes": ["remote", "hybrid"], "min_salary": 5000, "run_frequency": "weekly"}
    )
    assert criteria.work_modes == [WorkMode.remote, WorkMode.hybrid]
    assert criteria.min_salary == 5000
    assert criteria.run_frequency == RunFrequency.weekly
