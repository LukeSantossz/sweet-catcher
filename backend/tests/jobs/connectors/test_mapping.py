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


def test_to_iso_date_strips_surrounding_whitespace() -> None:
    assert to_iso_date("  2026-06-26T14:55:18  ") == "2026-06-26"


def test_as_dict_returns_empty_for_non_mapping() -> None:
    assert as_dict({"a": 1}) == {"a": 1}
    assert as_dict(None) == {}
    assert as_dict([1, 2]) == {}


def test_as_dict_list_keeps_only_dict_items() -> None:
    assert as_dict_list([{"a": 1}, "x", 2, {"b": 2}]) == [{"a": 1}, {"b": 2}]
    assert as_dict_list(None) == []


def test_str_list_keeps_only_strings() -> None:
    assert str_list(["a", 1, None, "b"]) == ["a", "b"]
    assert str_list("not-a-list") == []


def test_clean_str_strips_and_handles_non_str() -> None:
    assert clean_str("  hi  ") == "hi"
    assert clean_str(None) == ""
    assert clean_str(123) == ""


def test_coerce_id_handles_none_and_numbers() -> None:
    assert coerce_id(555) == "555"
    assert coerce_id("abc") == "abc"
    assert coerce_id(None) == ""
