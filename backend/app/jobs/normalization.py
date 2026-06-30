import hashlib
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.jobs.schemas import JobData, RawJob


def canonical_url(url: str) -> str:
    """Reduce a posting URL to a stable form for deduplication: lowercase scheme and host,
    drop query and fragment (tracking parameters), and strip a trailing slash."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def description_hash(description: str | None) -> str | None:
    """Hash a description after collapsing whitespace and lowercasing, so cosmetic
    differences do not defeat duplicate detection. Returns None for an empty description."""
    if not description or not description.strip():
        return None
    normalized = " ".join(description.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize(raw: RawJob) -> JobData:
    """Map a connector's raw payload into the common JobData schema."""
    payload: dict[str, Any] = raw.payload
    url = str(payload.get("url", ""))
    description = payload.get("description")
    return JobData(
        source=raw.source,
        source_external_id=raw.external_id,
        title=str(payload.get("title", "")),
        company=str(payload.get("company", "")),
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
