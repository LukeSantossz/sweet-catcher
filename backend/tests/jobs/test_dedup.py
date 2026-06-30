from typing import Any

from app.jobs.dedup import DuplicateIndex, composite_key
from app.jobs.normalization import normalize
from app.jobs.schemas import RawJob


def _job(external_id: str, **payload: Any) -> Any:
    return normalize(RawJob(source="mock", external_id=external_id, payload=payload))


def test_index_flags_repeated_canonical_url() -> None:
    index = DuplicateIndex()
    index.add(_job("1", title="A", company="Acme", url="https://x.example/jobs/1?utm=a"))
    later = _job("2", title="B", company="Beta", url="https://x.example/jobs/1")
    assert index.is_duplicate(later)


def test_index_flags_repeated_description_hash() -> None:
    index = DuplicateIndex()
    index.add(
        _job("1", title="A", company="Acme", url="https://x.example/a", description="same role")
    )
    later = _job("2", title="B", company="Beta", url="https://y.example/b", description="same role")
    assert index.is_duplicate(later)


def test_index_flags_probable_by_title_company_location() -> None:
    index = DuplicateIndex()
    index.add(
        _job(
            "1",
            title="Backend Engineer",
            company="Acme",
            location="Remote",
            url="https://x.example/a",
        )
    )
    later = _job(
        "2", title="backend engineer", company="acme", location="remote", url="https://y.example/b"
    )
    assert index.is_duplicate(later)


def test_index_does_not_flag_distinct_jobs() -> None:
    index = DuplicateIndex()
    index.add(_job("1", title="A", company="Acme", url="https://x.example/a", description="one"))
    later = _job("2", title="B", company="Beta", url="https://y.example/b", description="two")
    assert not index.is_duplicate(later)


def test_composite_key_normalizes_whitespace_and_case() -> None:
    a = _job("1", title="Backend Engineer", company="Acme", location="Remote", url="https://x/a")
    b = _job(
        "2", title="  backend   engineer ", company="ACME", location="remote", url="https://y/b"
    )
    assert composite_key(a) == composite_key(b)
