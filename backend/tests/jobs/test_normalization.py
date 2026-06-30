from app.jobs.normalization import canonical_url, description_hash, normalize
from app.jobs.schemas import RawJob


def test_normalize_maps_raw_to_jobdata() -> None:
    raw = RawJob(
        source="mock",
        external_id="42",
        payload={
            "title": "Backend Engineer",
            "company": "Acme",
            "url": "https://acme.example/jobs/42",
            "description": "Build APIs.",
            "work_mode": "remote",
        },
    )
    job = normalize(raw)
    assert job.source == "mock"
    assert job.source_external_id == "42"
    assert job.title == "Backend Engineer"
    assert job.company == "Acme"
    assert job.canonical_url == "https://acme.example/jobs/42"
    assert job.description_hash is not None
    assert job.raw == raw.payload


def test_canonical_url_strips_tracking_params() -> None:
    assert canonical_url("https://acme.example/jobs/42?utm_source=x&ref=y") == canonical_url(
        "https://acme.example/jobs/42"
    )


def test_canonical_url_normalizes_host_and_trailing_slash() -> None:
    assert canonical_url("https://ACME.example/jobs/42/") == canonical_url(
        "https://acme.example/jobs/42"
    )


def test_description_hash_ignores_whitespace_and_case() -> None:
    assert description_hash("Build   APIs") == description_hash("build apis")


def test_description_hash_none_for_empty() -> None:
    assert description_hash(None) is None
    assert description_hash("") is None
