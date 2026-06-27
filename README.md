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
- Data layer: PostgreSQL (pgvector), Redis
- Tooling: uv, ruff, pyright, pytest
- CI: GitHub Actions

## Engineering Decisions

| Decision | Record |
|----------|--------|
| Modular monolith with async workers | `docs/adr/0001-modular-monolith-architecture.md` |
| Backend and persistence stack | `docs/adr/0002-backend-and-persistence-stack.md` |
| Async processing and scheduling | `docs/adr/0003-async-processing-dramatiq-apscheduler.md` |
| LLM provider abstraction | `docs/adr/0004-llm-provider-abstraction.md` |

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
docker compose down
```

### Tests

```bash
cd backend
uv run pytest
```

## Project Structure

```
backend/    FastAPI modular monolith (app/, tests/)
frontend/   Reserved for the Next.js app (later phase)
docs/adr/   Architecture Decision Records
prd.md      Product Requirements Document
SPEC.md     Current change specification
```

## Project Status

In development — Phase 0 (project scaffolding) complete: runnable health-checked skeleton with CI.

## Known Issues & Limitations

- No business features yet; Phase 0 delivers only the skeleton and a health endpoint.
- The worker, scheduler, and LLM client are deferred to later phases.

## License

Personal project; no open-source license is granted at this time.
