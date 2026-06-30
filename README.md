# Sweet Catcher — Personal AI Job Hunter

A personal, AI-assisted application copilot that discovers, triages, explains, prepares, and tracks job applications end to end.

## What It Does

- Runs a health-checked FastAPI backend (Phase 0 baseline).
- (Planned) Daily job discovery, fit analysis, tailored resumes, and an application funnel — see `prd.md`.

## What It Is

A REST API backend (modular monolith) plus a reserved frontend, run locally via Docker Compose. It produces, over the roadmap, a personal applicant-tracking system for junior tech roles.

## Tech Stack

- Language: Python 3.12
- Framework: FastAPI
- Data layer: PostgreSQL (pgvector), Redis; SQLAlchemy 2.x, Alembic
- Tooling: uv, ruff, pyright, pytest
- CI: GitHub Actions

## Engineering Decisions

| Decision | Record |
|----------|--------|
| Modular monolith with async workers | [docs/adr/0001-modular-monolith-architecture.md](docs/adr/0001-modular-monolith-architecture.md) |
| Backend and persistence stack | [docs/adr/0002-backend-and-persistence-stack.md](docs/adr/0002-backend-and-persistence-stack.md) |
| Async processing and scheduling | [docs/adr/0003-async-processing-dramatiq-apscheduler.md](docs/adr/0003-async-processing-dramatiq-apscheduler.md) |
| LLM provider abstraction | [docs/adr/0004-llm-provider-abstraction.md](docs/adr/0004-llm-provider-abstraction.md) |
| Async persistence (SQLAlchemy + psycopg3) | [docs/adr/0005-async-persistence-sqlalchemy-psycopg3.md](docs/adr/0005-async-persistence-sqlalchemy-psycopg3.md) |
| Master-profile versioning (JSONB snapshots) | [docs/adr/0006-master-profile-versioning-jsonb-snapshots.md](docs/adr/0006-master-profile-versioning-jsonb-snapshots.md) |
| Job storage (normalized columns + raw JSONB) | [docs/adr/0007-job-storage-normalized-columns-raw-jsonb.md](docs/adr/0007-job-storage-normalized-columns-raw-jsonb.md) |
| Multi-source ingestion (APIs + polite scraping) | [docs/adr/0008-multi-source-ingestion-api-and-scraping.md](docs/adr/0008-multi-source-ingestion-api-and-scraping.md) |

## Getting Started

### Prerequisites

- Python 3.12, uv (`pip install uv`)
- Docker Desktop (for the local stack)

### Installation

```bash
cd backend
uv sync
```

### Running

```bash
docker compose up -d --build
curl http://localhost:8000/health   # -> {"status":"ok"}
```

With the stack still running, apply migrations and use the profile API:

```bash
cd backend
uv run alembic upgrade head
# Set the master profile (creates a new version):
curl -X PUT http://localhost:8000/profile \
  -H 'content-type: application/json' \
  -d '{"basics": {"full_name": "Ada Lovelace"}}'
curl http://localhost:8000/profile            # current version
curl http://localhost:8000/profile/versions   # version history

# Configure global job-search criteria (FR #3); active_sources selects the connectors
# ("remotive", "remote_rocketship", and the deterministic "mock"):
curl -X PUT http://localhost:8000/search-criteria \
  -H 'content-type: application/json' \
  -d '{"keywords": ["python"], "work_modes": ["remote"], "active_sources": ["remotive", "remote_rocketship"]}'
curl http://localhost:8000/search-criteria    # current criteria

# Run a discovery pass over the active sources (real connectors) and list jobs:
curl -X POST http://localhost:8000/jobs/discover   # -> run summary (created/updated/duplicates)
curl http://localhost:8000/jobs                     # discovered jobs
```

Stop the stack when done:

```bash
docker compose down
```

### Tests

```bash
cd backend
uv run pytest
```

Tests run against an auto-created `sweet_catcher_test` database, isolated from the app
database. The test database is created on first run and reused on subsequent runs.

## Project Structure

```
backend/    FastAPI modular monolith (app/, tests/)
frontend/   Reserved for the Next.js app (later phase)
docs/adr/   Architecture Decision Records
prd.md      Product Requirements Document
SPEC.md     Current change specification
```

## Project Status

In development — Phase 0 (scaffolding) and Phase 1 (master profile API) complete; Phase 2 (job discovery) in progress: global job-search criteria and a job-collection core (normalization, deduplication) are live, now with two real source connectors — the Remotive JSON API and Remote Rocketship (polite web scraping) — alongside the mock source. The resume standard is defined in [docs/resume-standard.md](docs/resume-standard.md).

## Known Issues & Limitations

- Live: the versioned master-profile API (Phase 1), global job-search criteria, and a synchronous job-discovery core with normalization and deduplication (Phase 2), driven by two real source connectors — the Remotive JSON API and Remote Rocketship (web scraping) — plus the mock source. Not yet implemented: document import/parsing, authentication, multi-profile support, and tailored-resume generation.
- Discovery runs only on demand: more sources (Seek NZ, LinkedIn), scheduled runs (the Dramatiq worker and APScheduler scheduler), fit analysis, and the LLM client are deferred to later phases. Scraping is politeness-first and best-effort — it treats robots.txt as advisory and degrades per source on failure (ADR 0008).

## License

Personal project; no open-source license is granted at this time.
