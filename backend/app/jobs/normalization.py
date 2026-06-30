import hashlib
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.jobs.schemas import JobData, RawJob

# Known tracking/analytics parameters that never identify a posting and are dropped so the
# same job linked with different campaign tags deduplicates to one canonical URL.
_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "gclid",
        "fbclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "ref_src",
    }
)


def canonical_url(url: str) -> str:
    """Reduce a posting URL to a stable form for deduplication: lowercase scheme and host,
    strip a trailing slash, drop the fragment, and remove only known tracking parameters while
    preserving identity-bearing query parameters (e.g. ``?id=123``)."""
    parts = urlsplit(url)
    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_PARAMS
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(kept), "")
    )


def description_hash(description: str | None) -> str | None:
    """Hash a description after collapsing whitespace and lowercasing, so cosmetic
    differences do not defeat duplicate detection. Returns None for an empty description."""
    if not description or not description.strip():
        return None
    normalized = " ".join(description.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing or invalid required field: {key}")
    return value


def normalize(raw: RawJob) -> JobData:
    """Map a connector's raw payload into the common JobData schema. Required fields
    (title, company, url) must be real non-empty strings; otherwise the job is rejected so the
    caller can skip it rather than persist placeholder values."""
    payload: dict[str, Any] = raw.payload
    url = _required_str(payload, "url")
    description = payload.get("description")
    return JobData(
        source=raw.source,
        source_external_id=raw.external_id,
        title=_required_str(payload, "title"),
        company=_required_str(payload, "company"),
        url=url,
        canonical_url=canonical_url(url),
        description=description,
        description_hash=description_hash(description),
        location=payload.get("location"),
        work_mode=payload.get("work_mode"),
        contract_type=payload.get("contract_type"),
        posted_at=payload.get("posted_at"),
        salary_min=payload.get("salary_min"),
        salary_max=payload.get("salary_max"),
        salary_currency=payload.get("salary_currency"),
        technologies=payload.get("technologies", []),
        languages=payload.get("languages", []),
        raw=payload,
    )
