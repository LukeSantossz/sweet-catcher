# SPEC: feat: structured, versioned master profile with manual entry API

## Problem
The backend has no persistent, versioned store of the user's structured professional
data, so no downstream feature (fit analysis, tailored resumes, claim validation) has a
source of truth to draw from.

## Design Decision
Introduce the project's first persistence layer and a single, structured master profile
saved as immutable, monotonically numbered version snapshots. The full profile — a basics
header plus the eight PRD content sections (experiences, projects, skills split into
technical and interpersonal, education, certifications, languages, links, job
preferences) — is validated by Pydantic v2 DTOs and stored as one JSONB
document per version in PostgreSQL, through async SQLAlchemy 2.x (psycopg3 driver) with
Alembic migrations. A `MasterProfileManager` service exposes create-version (with no-op
dedupe), get-current, list/get version, and restore, and a FastAPI router under `/profile`
provides manual structured entry and read access. Rich-document import (PDF, DOCX,
Markdown) is deferred to a later slice that depends on the not-yet-built LLM provider
abstraction.

## Alternatives Considered
- **Normalized relational tables per section** (one table per section, versioned by
  copying rows): rejected — 9+ tables and many migrations at the persistence debut,
  snapshotting duplicates every section row on each edit, and most relational power stays
  unused until later analytics phases; the profile is written and read as a whole.
- **Current-state plus audit-log versioning** (a single mutable profile and a per-field
  change log): rejected — reconstructing a full historical version and assigning the
  discrete "profile version" number that FR #30 (audit) and FR #17 (diff) rely on is
  awkward; immutable snapshots make rollback and diff trivial.
- **Hybrid (normalized current plus JSONB history)**: rejected for this slice — redundant
  data kept in sync adds complexity without a present need.
- **Synchronous SQLAlchemy sessions**: rejected — contradicts the async API direction in
  ADR 0002, and a later sync-to-async migration would touch every repository.
- **Including PDF/DOCX parsing now**: rejected — reliable document-to-structured
  extraction needs the LLM provider abstraction scheduled for Phase 4 (ADR 0004); merging
  it here would fuse two subsystems and break the decision sequence.

## Scope
- Includes:
  - `app/db/base.py` (`DeclarativeBase`) and `app/db/session.py` (async engine, async
    session factory, `get_session` FastAPI dependency).
  - `app/config.py`: `database_url` default updated to the psycopg3 driver
    (`postgresql+psycopg://...`).
  - `app/profile/schemas.py`: Pydantic v2 DTOs — `MasterProfileData` plus the section
    models (`Basics`, `Experience`, `Project`, `TechnicalSkill`, `Education`,
    `Certification`, `Language`, `Link`, `JobPreferences`) and enums (`ProficiencyLevel`,
    `LanguageProficiency`, `WorkMode`, `LinkType`); permissive input (`extra="ignore"`);
    cross-field validation
    (`end_date >= start_date`, `is_current` consistent with `end_date`); only
    `basics.full_name` required, every other field optional or an empty list.
  - `app/profile/models.py`: SQLAlchemy ORM `MasterProfile` and `MasterProfileVersion`
    (UUID primary keys, `version_number`, `created_at`, `note`, `data` JSONB, unique
    `(profile_id, version_number)`).
  - `app/profile/service.py`: `MasterProfileManager` — `get_or_create_profile`,
    `create_version` (dedupe when identical to latest), `get_current`, `list_versions`,
    `get_version`, `restore_version`.
  - `app/profile/router.py`: FastAPI router under `/profile` — `GET /profile`,
    `PUT /profile`, `GET /profile/versions`, `GET /profile/versions/{version_number}`,
    `POST /profile/versions/{version_number}/restore`; wired into `create_app()`.
  - Alembic: `alembic.ini`, `alembic/env.py` (bound to `Base.metadata` and
    `database_url`), and migration `0001_create_master_profile`.
  - Tests, written first: `tests/profile/test_schemas.py`, `tests/profile/test_service.py`,
    `tests/profile/test_router.py`, and `tests/conftest.py` (async engine,
    `alembic upgrade head` schema setup, per-test transactional rollback against a real
    PostgreSQL).
  - Dependencies: runtime `sqlalchemy[asyncio]`, `alembic`, `psycopg[binary]`; dev
    `pytest-asyncio`; `uv.lock` updated.
  - CI: a PostgreSQL service (pgvector image) added to `.github/workflows/ci.yml`, with a
    test `DATABASE_URL`.
  - ADRs promoted at the Gate: `0005` (async SQLAlchemy 2.x session pattern plus psycopg3
    single driver) and `0006` (master-profile versioning: immutable JSONB snapshots plus
    monotonic version number).
  - README: a short note on the profile API and the migrations command, in the
    `github.md` section order.
- Does NOT include:
  - File import or parsing of PDF, DOCX, Markdown, or free text, and any LLM-backed field
    extraction (deferred; depends on the LLM provider abstraction, ADR 0004 / Phase 4).
  - Multiple or named profiles; the model is a single profile for the single-user V1.
  - Authentication, authorization, or per-user scoping (open question #7).
  - Diff endpoints between profile versions, and the master-versus-tailored resume diff
    (FR #17), which belongs to the resume phase.
  - Search-criteria configuration (FR #3) beyond the profile-side `job_preferences`
    object; discovery, analysis, scoring, resume generation, applications, dashboard,
    analytics, notifications, exports, and attachments.
  - Concurrency control beyond the unique `(profile_id, version_number)` constraint
    (single-user assumption).
  - pgvector or embeddings usage.

## Acceptance Criteria
- schema_requires_full_name: `MasterProfileData` validation fails when `basics.full_name`
  is missing and succeeds with only `full_name` set and all other sections empty.
- schema_rejects_inverted_dates: an `Experience` with `end_date` earlier than `start_date`
  fails validation.
- schema_enforces_is_current_rule: an `Experience` with `is_current` true and a non-null
  `end_date` fails validation, and one with `is_current` false and a null `end_date` fails
  validation.
- schema_ignores_unknown_fields: unknown keys in the input are ignored, not rejected.
- service_first_save_creates_version_one: `create_version` on an empty profile returns
  `version_number` equal to 1.
- service_distinct_save_increments_version: a second `create_version` with different data
  returns `version_number` equal to 2.
- service_identical_save_is_deduped: `create_version` with data identical to the latest
  version creates no new version and returns the existing latest.
- service_get_current_returns_latest: `get_current` returns the highest-numbered version.
- service_list_versions_excludes_data: `list_versions` returns metadata (version_number,
  created_at, note) ordered by version_number descending and omits the full `data` payload.
- service_restore_creates_new_version_from_source: `restore_version(n)` creates a new
  latest version whose `data` equals version `n`'s data.
- api_get_current_returns_404_when_empty: `GET /profile` returns 404 before any version
  exists.
- api_put_creates_version_and_returns_201: `PUT /profile` with a valid body returns 201 and
  `version_number` 1; a subsequent changed `PUT` returns 201 and `version_number` 2.
- api_put_identical_returns_200_without_new_version: a `PUT /profile` identical to the
  current state returns 200 and does not increment `version_number`.
- api_get_version_returns_404_when_missing: `GET /profile/versions/{n}` for a non-existent
  number returns 404.
- api_invalid_body_returns_422: `PUT /profile` with an invalid body (for example a missing
  `full_name`) returns 422.
- api_restore_returns_201_or_404: `POST /profile/versions/{n}/restore` for an existing
  version returns 201 with a new highest `version_number`, and for a missing version
  returns 404.
- migration_creates_tables: `alembic upgrade head` on an empty database creates
  `master_profile` and `master_profile_version` with the unique
  `(profile_id, version_number)` constraint.
- quality_gates_pass: `ruff check`, `ruff format --check`, `pyright` (strict), and `pytest`
  all pass in `backend/`.

## Reproducibility
- Verify on the `feat/phase-1-master-profile` branch at the PR head.
- Start a local database with `docker compose up -d postgres` (or the full stack), and set
  `DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/sweet_catcher`.
- Commands in `backend/`: `uv sync`; `uv run alembic upgrade head`; `uv run ruff check .`;
  `uv run ruff format --check .`; `uv run pyright`; `uv run pytest`.
- Versions: Python 3.12; SQLAlchemy 2.x, Alembic, psycopg3, and pytest-asyncio pinned in
  `pyproject.toml` and `uv.lock`; PostgreSQL via the pinned pgvector image. CI runs the
  same checks against an ephemeral PostgreSQL service on `ubuntu-latest`.
- No randomness is involved; tests are deterministic.

## Risks and Assumptions
- Assumption: single-user V1 — exactly one master profile exists, so no auth or per-user
  scoping is needed yet (open question #7).
- Assumption: structured manual entry satisfies the V1 minimum of FR #2; rich-document
  import arrives in a later slice once the LLM provider abstraction (ADR 0004) exists. A
  decision to require document import before that abstraction would invalidate this.
- Assumption: storing the profile as a JSONB snapshot is acceptable, and per-section
  relational querying is a later-phase need. An early requirement to query or aggregate
  across profile sections in SQL would invalidate this.
- Risk: JSONB is PostgreSQL-specific, so tests require a real PostgreSQL (no SQLite
  shortcut); mitigated by a CI PostgreSQL service and Docker Compose locally.
- Risk: async SQLAlchemy adds test-fixture complexity (async engine, transactional
  rollback, greenlet); accepted as a one-time cost to match the async API direction
  (ADR 0002).
- Risk: the profile DTO shape will evolve; permissive input (`extra="ignore"`) and
  snapshot versioning absorb non-breaking evolution without DB migrations, but a field
  rename or removal needs a data-migration consideration for old snapshots. A need to
  re-validate historical snapshots against the latest schema would invalidate this.
