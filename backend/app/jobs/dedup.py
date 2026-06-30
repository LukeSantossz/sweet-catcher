from app.jobs.schemas import JobData


def _normalize_text(text: str | None) -> str:
    return " ".join((text or "").split()).strip().lower()


def composite_key(job: JobData) -> str:
    """A normalized (title, company, location) key used as a probable-duplicate signal."""
    return "|".join(
        (_normalize_text(job.title), _normalize_text(job.company), _normalize_text(job.location))
    )


def is_duplicate(a: JobData, b: JobData) -> bool:
    """Exact-key duplicate: same canonical URL, same (source, external id), or same
    description hash (FR #8)."""
    if a.canonical_url and a.canonical_url == b.canonical_url:
        return True
    if a.source == b.source and a.source_external_id == b.source_external_id:
        return True
    if a.description_hash is not None and a.description_hash == b.description_hash:
        return True
    return False


def is_probable_duplicate(a: JobData, b: JobData) -> bool:
    """Probable duplicate: a matching normalized (title, company, location) without an
    exact-key match (FR #8 confidence-threshold flag)."""
    if is_duplicate(a, b):
        return False
    return composite_key(a) == composite_key(b)
