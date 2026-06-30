# SPEC: feat: configurable global job-search criteria

## Problem
There is no persisted, user-configurable set of global search criteria, so scheduled
discovery (FR #4) has no source of truth describing what jobs to look for.

## Design Decision
Introduce a single, mutable global search-criteria configuration, stored as one validated
JSONB document in a singleton table (`search_criteria`, at most one row for the single-user
V1). A Pydantic v2 DTO (`SearchCriteriaData`) models every FR #3 field — keywords, allowed
and blocked seniorities, allowed and blocked areas, countries and cities, work modes,
minimum salary (with currency), accepted languages, required and desired technologies,
blocked and favorite companies, active sources, and run frequency — with permissive input
(`extra="ignore"`) and cross-field validation (non-negative salary; no value appearing in
both an allow-list and its matching block-list). A `SearchCriteriaManager` service exposes
`get` and `set` (upsert into the one row), and a FastAPI router under `/search-criteria`
provides `GET` (current) and `PUT` (create-or-update) access. Unlike the master profile
(FR #1), the criteria are **not versioned**: FR #3 requires only the current configuration,
so no version history, snapshots, or restore are introduced. The `WorkMode` enum already
defined in `app/profile/schemas.py` is reused rather than duplicated; a new `RunFrequency`
enum (`daily`, `weekly`) defaults to `daily`, matching FR #4's "default daily,
user-adjustable".

## Alternatives Considered
- **Reuse the master-profile versioned-snapshot model (a versions table plus restore):**
  rejected — FR #3 asks only for the current configuration; the audit/version-number
  drivers behind ADR 0006 (FR #1, #17, #30) do not apply to search criteria, so a versions
  table and restore endpoint would be unused machinery. A mutable singleton matches the
  requirement; versioning can be added later if criteria history becomes a requirement.
- **Normalized relational columns/tables per field:** rejected — most FR #3 fields are
  lists (keywords, seniorities, technologies, companies, sources), which would require many
  join tables; the configuration is read and written as a whole, and JSONB absorbs shape
  evolution without a migration, consistent with the master-profile precedent.
- **Configuration via environment variables or a static file:** rejected — the criteria
  must be editable at runtime through the API and persisted in the relational source of
  truth (NFR #7); env/file config is neither runtime-editable nor the system of record.
- **A multiple-named-criteria-sets model:** rejected — FR #3 specifies a single set of
  global criteria for the single-user V1; multiple named criteria sets are not required and
  would add selection logic with no present need.

## Scope
- Includes:
  - `app/search/__init__.py`, `app/search/schemas.py`: Pydantic v2 DTOs — `SearchCriteriaData`
    (all FR #3 fields, every field optional or an empty list), the `RunFrequency` enum, the
    read model `SearchCriteriaRead` (`updated_at` plus `data`); `extra="ignore"`;
    `min_salary` constrained to `>= 0`; cross-field validation rejecting any value present in
    both `allowed_seniorities`/`blocked_seniorities`, both `allowed_areas`/`blocked_areas`,
    or both `favorite_companies`/`blocked_companies`. `WorkMode` is imported from
    `app/profile/schemas.py` (reused, not redefined).
  - `app/search/models.py`: SQLAlchemy ORM `SearchCriteria` (UUID primary key, `created_at`,
    `updated_at`, `data` JSONB); a singleton — the service maintains at most one row.
  - `app/search/service.py`: `SearchCriteriaManager` — `get` (returns the single row or
    `None`) and `set` (insert when absent, otherwise update the existing row's `data` and
    `updated_at`).
  - `app/search/router.py`: FastAPI router under `/search-criteria` — `GET /search-criteria`
    (200 with current, 404 when unset) and `PUT /search-criteria` (201 on first creation,
    200 on update, 422 on invalid body); wired into `create_app()`.
  - Alembic migration `0002_create_search_criteria` (down-revision `0001_create_master_profile`).
  - Tests, written first: `tests/search/__init__.py`, `tests/search/test_schemas.py`,
    `tests/search/test_service.py`, `tests/search/test_router.py`,
    `tests/search/test_migration.py`, reusing the existing `tests/conftest.py` fixtures.
  - README: a short note on the search-criteria endpoint, in the `github.md` section order.
- Does NOT include:
  - Scheduled discovery itself (FR #4) and any of the discovery pipeline (FR #5–8): source
    connectors, the Dramatiq worker, the APScheduler scheduler, normalization, and
    deduplication. This slice only persists the criteria those features will later read.
  - Versioning, history, audit log, or restore of the criteria (not required by FR #3).
  - Validation that `active_sources` names correspond to real connectors (the connector
    registry does not exist yet); `active_sources` is a free list of strings for now.
  - Authentication, authorization, or per-user scoping (single-user V1).
  - Multiple or named criteria sets; per-source criteria.
  - Any frontend or dashboard surface.

## Acceptance Criteria
- schema_accepts_empty_criteria: `SearchCriteriaData` validates with all fields defaulted
  (empty lists, null salary) and `run_frequency` equal to `daily`.
- schema_rejects_negative_min_salary: `min_salary` below zero fails validation.
- schema_rejects_overlapping_seniorities: a seniority present in both `allowed_seniorities`
  and `blocked_seniorities` fails validation.
- schema_rejects_overlapping_areas: an area present in both `allowed_areas` and
  `blocked_areas` fails validation.
- schema_rejects_company_in_favorite_and_blocked: a company present in both
  `favorite_companies` and `blocked_companies` fails validation.
- schema_ignores_unknown_fields: unknown keys in the input are ignored, not rejected.
- service_get_returns_none_when_unset: `get` returns `None` before any `set`.
- service_set_creates_then_updates_single_row: a first `set` creates the row; a second `set`
  with different data updates it, and exactly one `search_criteria` row exists afterward.
- service_get_returns_latest_after_set: `get` after `set` returns the data last written.
- api_get_returns_404_when_unset: `GET /search-criteria` returns 404 before any `PUT`.
- api_put_creates_returns_201_then_update_returns_200: a first `PUT` returns 201; a
  subsequent `PUT` returns 200.
- api_get_returns_current_after_put: `GET` after a `PUT` returns the written criteria.
- api_put_invalid_body_returns_422: `PUT` with an invalid body (for example a negative
  `min_salary`) returns 422.
- migration_creates_search_criteria_table: `alembic upgrade head` on an empty database
  creates the `search_criteria` table.
- quality_gates_pass: `ruff check`, `ruff format --check`, `pyright` (strict), and `pytest`
  all pass in `backend/`.

## Reproducibility
- Verify on the `feat/phase-2-search-criteria` branch at the PR head.
- Start a local database with `docker compose up -d postgres`, and set
  `DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/sweet_catcher`.
- Commands in `backend/`: `uv sync`; `uv run alembic upgrade head`; `uv run ruff check .`;
  `uv run ruff format --check .`; `uv run pyright`; `uv run pytest`.
- Versions: Python 3.12; SQLAlchemy 2.x, Alembic, psycopg3, and pytest-asyncio as pinned in
  `pyproject.toml` and `uv.lock` (no new dependency is added). PostgreSQL via the pinned
  pgvector image. CI runs the same checks against the ephemeral PostgreSQL service.
- Tests run against the auto-created, isolated `sweet_catcher_test` database with per-test
  transactional rollback, via the existing `tests/conftest.py`. No randomness is involved.

## Risks and Assumptions
- Assumption: single-user V1 — exactly one criteria configuration exists, so the table is a
  singleton and no per-user scoping is needed. A move to multi-user would invalidate this.
- Assumption: FR #3 needs only the current configuration; no version history is required. A
  later requirement to audit or diff criteria changes would invalidate the non-versioned
  decision and call for the snapshot model used by the master profile.
- Assumption: `active_sources` and `run_frequency` are stored now and consumed by the
  not-yet-built discovery scheduler (FR #4) and connectors (FR #5); `active_sources` values
  are not yet validated against a connector registry. A requirement to reject unknown source
  names before the registry exists would invalidate this.
- Risk: JSONB is PostgreSQL-specific, so tests require a real PostgreSQL (no SQLite
  shortcut); mitigated by the existing CI PostgreSQL service and local Docker Compose.
- Risk: the criteria DTO shape will evolve as discovery lands; permissive input
  (`extra="ignore"`) and JSONB storage absorb non-breaking evolution without a migration,
  but a field rename or removal needs consideration for an already-stored document.
- Decision record: this slice does not promote a new ADR. The non-versioned singleton is a
  local, reversible choice recorded here in Alternatives Considered; it does not meet the
  "hard to reverse" ADR-promotion bar in `spec_method.md`. Reconsider if the Developer
  judges it ADR-worthy at the Gate.
