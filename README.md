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

In development — Phase 0 (project scaffolding) complete; Phase 1 (master profile API) in progress. The resume standard is defined in [docs/resume-standard.md](docs/resume-standard.md).

## Known Issues & Limitations

- The versioned master-profile API is live (Phase 1). Not yet implemented: document import/parsing, authentication, multi-profile support, and tailored-resume generation.
- The worker, scheduler, and LLM client are deferred to later phases.

## License

Personal project; no open-source license is granted at this time.
