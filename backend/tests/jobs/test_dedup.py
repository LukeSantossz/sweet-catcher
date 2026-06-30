from typing import Any

from app.jobs.dedup import composite_key, is_duplicate, is_probable_duplicate
from app.jobs.normalization import normalize
from app.jobs.schemas import RawJob


def _job(external_id: str, **payload: Any) -> Any:
    return normalize(RawJob(source="mock", external_id=external_id, payload=payload))


def test_duplicate_on_canonical_url() -> None:
    a = _job("1", title="A", company="Acme", url="https://x.example/jobs/1?utm=a")
    b = _job("2", title="B", company="Beta", url="https://x.example/jobs/1")
    assert is_duplicate(a, b)


def test_duplicate_on_source_external_id() -> None:
    a = _job("7", title="A", company="Acme", url="https://x.example/a")
    b = _job("7", title="B", company="Beta", url="https://y.example/b")
    assert is_duplicate(a, b)


def test_duplicate_on_description_hash() -> None:
    a = _job("1", title="A", company="Acme", url="https://x.example/a", description="same role")
    b = _job("2", title="B", company="Beta", url="https://y.example/b", description="same role")
    assert is_duplicate(a, b)


def test_not_duplicate_when_all_keys_differ() -> None:
    a = _job("1", title="A", company="Acme", url="https://x.example/a", description="one")
    b = _job("2", title="B", company="Beta", url="https://y.example/b", description="two")
    assert not is_duplicate(a, b)


def test_probable_duplicate_on_title_company_location() -> None:
    a = _job("1", title="Backend Engineer", company="Acme", location="Remote", url="https://x.example/a")
    b = _job("2", title="backend engineer", company="acme", location="remote", url="https://y.example/b")
    assert not is_duplicate(a, b)
    assert is_probable_duplicate(a, b)
    assert composite_key(a) == composite_key(b)
