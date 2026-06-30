# SPEC: feat: job discovery core — common schema, mock connector, normalization, and deduplication

## Problem
The backend persists search criteria but has no jobs and no mechanism to collect them, so
nothing consumes the criteria to discover, normalize, deduplicate, and store job postings.

## Design Decision
Introduce the Job domain and a synchronous discovery pipeline. Jobs are stored in a
**normalized relational table** (so they can be filtered, deduplicated, and aggregated in
SQL per FR #8/#25/#26), with the original source payload retained in a `raw` JSONB column —
a deliberate departure from the read-as-whole JSONB-snapshot model used for the profile and
criteria, promoted to **ADR 0007**. A `SourceConnector` Protocol (FR #5) defines pluggable
sources whose errors are classified and isolated so one failing source cannot abort the run;
a deterministic `MockConnector` provides raw payloads for V1. Normalization maps a
connector's raw payload to a `JobData` DTO carrying only source-derived fields (FR #7);
analysis-derived fields (inferred seniority, extracted requirements — FR #9/#10) are left to
the later analysis phase. Deduplication (FR #8) keys on canonical URL, the `(source,
external_id)` pair, and a normalized description hash, with a normalized `(title, company,
location)` composite recorded as a probable-duplicate signal. A `DiscoveryService.run()`
loads the active `SearchCriteria`, invokes the connectors named in `active_sources`,
normalizes, deduplicates against existing and in-batch jobs, inserts new jobs, updates
existing ones, and returns a run summary — **synchronously**, with no worker or scheduler
yet. A FastAPI router exposes a manual run trigger and a job list.

## Alternatives Considered
- **JSONB-snapshot storage for jobs (like profile/criteria):** rejected — jobs must be
  filtered, deduplicated, and aggregated in SQL (FR #8, #25, #26); storing them as opaque
  whole-documents makes those access patterns awkward. Normalized columns plus a `raw` JSONB
  fit the workload; this is the decision recorded in ADR 0007.
- **Include the Dramatiq worker and APScheduler scheduler now:** rejected — a single
  synchronous run path proves the pipeline first; scheduled, off-request execution
  (ADR 0003) is a separate slice once normalization/dedup/persistence are correct. The run
  service is shaped to be called by the scheduler later.
- **Ship a real connector (Greenhouse/Lever/Ashby) now:** rejected — a deterministic mock
  proves normalization, dedup, and persistence without network flakiness or
  terms-of-use/compliance surface; the real connector is the next slice behind the
  now-stable `SourceConnector` interface (Open Question #9 stays open).
- **Fuzzy similarity dedup (embeddings or edit distance):** rejected for V1 — exact keys
  (canonical URL, `(source, external_id)`, description hash) plus a normalized
  `(title, company, location)` composite cover the common cases; confidence-scored fuzzy
  matching is deferred.
- **Store analysis-derived fields on the Job now:** rejected — inferred seniority and
  extracted requirements are FR #9/#10 outputs from the not-yet-built analysis/LLM phase;
  the Job carries only connector- and normalization-provided fields.

## Scope
- Includes:
  - `app/jobs/__init__.py`, `app/jobs/schemas.py`: Pydantic v2 DTOs — `JobData` (FR #7
    source-derived fields: title, company, source, source_external_id, url, canonical_url,
    description, location, work_mode, contract_type, employment dates, salary range and
    currency, technologies, languages, status, plus the `raw` payload), the `RawJob` DTO
    (source name, external id, payload), enums `ContractType` and `JobStatus`, and the
    `RunSummary` DTO (per-source counts: found, created, updated, duplicates, errors).
    `WorkMode` is reused from `app/profile/schemas.py`.
  - `app/jobs/models.py`: SQLAlchemy ORM `Job` — normalized columns for the queryable and
    dedup fields, a `raw` JSONB column, timestamps (`first_seen_at`, `last_seen_at`), a
    unique constraint on `(source, source_external_id)`, and indexes on `canonical_url` and
    `description_hash`.
  - `app/jobs/connectors/__init__.py`: the `SourceConnector` Protocol (`name: str`,
    `async def fetch(criteria: SearchCriteriaData) -> list[RawJob]`) and a `MockConnector`
    returning deterministic raw payloads.
  - `app/jobs/normalization.py`: `normalize(raw: RawJob) -> JobData`, including
    `canonical_url` derivation and `description_hash` computation.
  - `app/jobs/dedup.py`: dedup-key computation and matching (canonical URL,
    `(source, external_id)`, description hash; normalized `(title, company, location)`
    composite as the probable-duplicate signal).
  - `app/jobs/service.py`: `DiscoveryService` — `run()` loads the active `SearchCriteria`,
    invokes each connector named in `active_sources`, normalizes and deduplicates, inserts
    new jobs and updates existing ones (`last_seen_at`), isolates and records per-source
    errors, and returns a `RunSummary`.
  - `app/jobs/router.py`: router under `/jobs` — `POST /jobs/discover` (run synchronously,
    return the `RunSummary`) and `GET /jobs` (list persisted jobs); wired into `create_app()`.
  - Alembic migration `0003_create_jobs` (down-revision `0002_create_search_criteria`),
    creating the `jobs` table with the unique constraint and indexes above; registered on
    `Base.metadata` via `alembic/env.py`.
  - Tests, written first, under `tests/jobs/`: schema/normalization, dedup, service
    (dedup on re-run is idempotent; per-source error isolation; only active sources run),
    router, and migration; reusing the existing `tests/conftest.py`.
  - ADR `0007` (job storage model: normalized columns plus a raw JSONB payload), promoted at
    the Gate.
  - README note on the discovery endpoint, in the `github.md` section order.
- Does NOT include:
  - The Dramatiq worker, the APScheduler scheduler, scheduled/off-request execution
    (FR #4 scheduling), and enqueueing fit analysis. The run is synchronous and trigger-only.
  - Real source connectors; only the mock ships (Open Question #9 deferred).
  - The manual single-job add endpoint (FR #6), deferred to a later slice.
  - Fit analysis, requirement extraction, seniority inference, scoring, and any
    analysis-derived Job fields (FR #9–15).
  - Advanced filtering, pagination, market analytics, and the dashboard (FR #24–27).
  - Fuzzy/similarity-scored deduplication; pgvector or embeddings.
  - Authentication, authorization, and multi-user scoping.

## Acceptance Criteria
- normalize_maps_raw_to_jobdata: `normalize` turns a mock `RawJob` into a `JobData` with the
  expected title, company, source, url, and a populated `description_hash`.
- normalize_derives_canonical_url: a URL with tracking query parameters normalizes to a
  stable `canonical_url` (the same posting from two URLs yields the same canonical form).
- dedup_matches_on_canonical_url: two raw jobs with the same canonical URL are detected as
  duplicates.
- dedup_matches_on_source_external_id: two raw jobs with the same `(source, external_id)`
  are detected as duplicates.
- dedup_matches_on_description_hash: two raw jobs with identical descriptions are detected
  as duplicates.
- dedup_flags_probable_duplicate_on_title_company_location: jobs sharing a normalized
  `(title, company, location)` but no exact key are flagged as probable duplicates.
- service_persists_new_jobs: a discovery run over a mock source with two new postings
  inserts two `jobs` rows and reports `created == 2`.
- service_rerun_is_idempotent: running discovery twice over the same mock payloads creates no
  duplicate rows; the second run reports `created == 0` and `updated == 2`.
- service_isolates_connector_errors: when one of two active connectors raises, the other's
  jobs are still persisted and the failure is recorded in the summary's per-source errors.
- service_runs_only_active_sources: a connector whose name is absent from
  `criteria.active_sources` is not invoked.
- api_discover_returns_summary: `POST /jobs/discover` returns 200 with the run summary counts.
- api_list_jobs_returns_persisted: after a run, `GET /jobs` returns the persisted jobs.
- migration_creates_jobs_table: `alembic upgrade head` creates the `jobs` table with the
  unique `(source, source_external_id)` constraint.
- quality_gates_pass: `ruff check`, `ruff format --check`, `pyright` (strict), and `pytest`
  all pass in `backend/`.

## Reproducibility
- Verify on the `feat/phase-2-job-discovery` branch at the PR head.
- Start a local database (`docker compose up -d postgres`) and set
  `DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/sweet_catcher`.
- Commands in `backend/`: `uv sync`; `uv run alembic upgrade head`; `uv run ruff check .`;
  `uv run ruff format --check .`; `uv run pyright`; `uv run pytest`.
- Versions: Python 3.12; SQLAlchemy 2.x, Alembic, psycopg3, pytest-asyncio as pinned (no new
  runtime dependency is required for the mock path). PostgreSQL via the pinned pgvector image.
- Tests run against the auto-created, isolated `sweet_catcher_test` database with per-test
  transactional rollback, via the existing `tests/conftest.py`. The mock connector is
  deterministic; no randomness or network access is involved.

## Risks and Assumptions
- Assumption: single-user V1 and a synchronous, trigger-only run; scheduled execution
  arrives with the worker/scheduler slice (ADR 0003). A requirement for background scheduling
  before that slice would invalidate this.
- Assumption: a deterministic mock source is sufficient to prove normalization, dedup, and
  persistence; the first real connector follows behind the stable interface. An early
  requirement to ingest a live source would re-order the slices.
- Assumption: exact-key dedup plus a normalized composite signal is adequate for V1; a
  requirement for fuzzy/confidence-scored matching would invalidate the dedup design.
- Assumption: the Job holds only source-derived fields now; analysis-derived fields are added
  by the analysis phase (FR #9/#10) without reshaping this table destructively.
- Risk: the normalized Job schema will evolve as the first real connector lands; new nullable
  columns are additive, but a field rename needs a migration. Mitigated by keeping the raw
  payload so re-normalization is possible.
- Risk: `canonical_url` normalization can over- or under-strip query parameters; mitigated by
  keeping the raw URL and covering the rule with tests, and by the additional dedup keys.
- Decision record: this slice promotes ADR 0007 (job storage model), a durable, hard-to-
  reverse choice that diverges from the profile/criteria JSONB-snapshot pattern.
