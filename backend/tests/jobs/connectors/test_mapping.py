from app.jobs.connectors.mapping import (
    coerce_salary_amount,
    map_contract_type,
    map_work_mode,
    to_iso_date,
)
from app.jobs.schemas import ContractType
from app.profile.schemas import WorkMode


def test_map_work_mode_known_and_aliases() -> None:
    assert map_work_mode("remote") == WorkMode.remote.value
    assert map_work_mode("Hybrid") == WorkMode.hybrid.value
    assert map_work_mode("on-site") == WorkMode.onsite.value
    assert map_work_mode("on_site") == WorkMode.onsite.value


def test_map_work_mode_unknown_or_non_str_is_none() -> None:
    assert map_work_mode("teleport") is None
    assert map_work_mode(None) is None
    assert map_work_mode(123) is None


def test_map_contract_type_known_and_hyphenated() -> None:
    assert map_contract_type("full_time") == ContractType.full_time.value
    assert map_contract_type("full-time") == ContractType.full_time.value
    assert map_contract_type("Contract") == ContractType.contract.value


def test_map_contract_type_unknown_or_non_str_is_none() -> None:
    assert map_contract_type("gig") is None
    assert map_contract_type(None) is None


def test_to_iso_date_truncates_datetime_to_date() -> None:
    assert to_iso_date("2026-06-26T14:55:18") == "2026-06-26"
    assert to_iso_date("2026-06-26") == "2026-06-26"


def test_to_iso_date_converts_timezone_to_utc() -> None:
    # 00:30 at +05:00 is the previous calendar day in UTC.
    assert to_iso_date("2026-06-27T00:30:00+05:00") == "2026-06-26"


def test_to_iso_date_returns_none_for_bad_input() -> None:
    assert to_iso_date("not-a-date") is None
    assert to_iso_date("") is None
    assert to_iso_date(None) is None
    assert to_iso_date(20260626) is None


def test_coerce_salary_amount_accepts_int_and_finite_float() -> None:
    assert coerce_salary_amount(150000) == 150000
    assert coerce_salary_amount(150000.0) == 150000


def test_coerce_salary_amount_rejects_bool_negative_and_non_number() -> None:
    assert coerce_salary_amount(True) is None
    assert coerce_salary_amount(-5) is None
    assert coerce_salary_amount(float("inf")) is None
    assert coerce_salary_amount("80000") is None
    assert coerce_salary_amount(None) is None
