"""Shared helpers for mapping a source's raw JSON into the common RawJob payload vocabulary.

These centralise the JSON boundary (typing-safe coercion of `Any` values) and the enum mappings
reused by every connector, so individual connectors stay small."""

import math
from datetime import UTC, datetime
from typing import Any, cast

from app.jobs.schemas import ContractType
from app.profile.schemas import WorkMode

_CONTRACT_BY_NAME = {
    "full_time": ContractType.full_time,
    "part_time": ContractType.part_time,
    "contract": ContractType.contract,
    "internship": ContractType.internship,
    "temporary": ContractType.temporary,
    "freelance": ContractType.freelance,
}

_WORK_MODE_BY_NAME = {
    "remote": WorkMode.remote,
    "hybrid": WorkMode.hybrid,
    "onsite": WorkMode.onsite,
    "on_site": WorkMode.onsite,
    "on-site": WorkMode.onsite,
}


def as_dict(value: Any) -> dict[str, Any]:
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


def as_dict_list(value: Any) -> list[dict[str, Any]]:
    items = cast("list[Any]", value) if isinstance(value, list) else []
    return [cast("dict[str, Any]", item) for item in items if isinstance(item, dict)]


def str_list(value: Any) -> list[str]:
    items = cast("list[Any]", value) if isinstance(value, list) else []
    return [item for item in items if isinstance(item, str)]


def to_iso_date(value: Any) -> str | None:
    """Reduce an ISO-8601 date or datetime string to a plain `YYYY-MM-DD` date string. A
    timezone-aware timestamp is normalized to UTC first so the calendar date does not drift."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC)
    return parsed.date().isoformat()


def coerce_salary_amount(value: Any) -> int | None:
    """Coerce a source salary amount to a non-negative int. Accepts ints and finite floats,
    but rejects bools (a bool is an int subclass), non-numbers, and negatives so a malformed
    amount is dropped rather than crashing JobData's ``ge=0`` validation."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    amount = int(value)
    return amount if amount >= 0 else None


def map_contract_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    mapped = _CONTRACT_BY_NAME.get(value.strip().lower().replace("-", "_"))
    return mapped.value if mapped is not None else None


def map_work_mode(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    mapped = _WORK_MODE_BY_NAME.get(value.strip().lower())
    return mapped.value if mapped is not None else None
