from app.jobs.schemas import JobData


def _normalize_text(text: str | None) -> str:
    return " ".join((text or "").split()).strip().lower()


def composite_key(job: JobData) -> str:
    """A normalized (title, company, location) key — the probable-duplicate signal (FR #8)."""
    return "|".join(
        (_normalize_text(job.title), _normalize_text(job.company), _normalize_text(job.location))
    )


class DuplicateIndex:
    """Accumulates the duplicate signals seen during a discovery run so cross-posting
    duplicates can be flagged without being dropped (FR #8). Exact identity dedup on
    (source, external id) is handled separately by persistence, not here.

    A job counts as a duplicate of an earlier one when it shares a canonical URL, a
    description hash, or a normalized (title, company, location) key.
    """

    def __init__(self) -> None:
        self._canonical_urls: set[str] = set()
        self._description_hashes: set[str] = set()
        self._composites: set[str] = set()

    def is_duplicate(self, job: JobData) -> bool:
        if job.canonical_url and job.canonical_url in self._canonical_urls:
            return True
        if job.description_hash is not None and job.description_hash in self._description_hashes:
            return True
        return composite_key(job) in self._composites

    def add(self, job: JobData) -> None:
        if job.canonical_url:
            self._canonical_urls.add(job.canonical_url)
        if job.description_hash is not None:
            self._description_hashes.add(job.description_hash)
        self._composites.add(composite_key(job))
