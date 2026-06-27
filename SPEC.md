# SPEC: chore: scaffold project skeleton with backend, tooling, CI, and Docker Compose

## Problem
The repository holds the PRD and the standards submodule but no runnable codebase, toolchain, CI, or local environment, so there is no foundation on which to build the system's features test-first.

## Design Decision
Establish a monorepo modular monolith. A Python 3.12 + FastAPI backend lives under `backend/`, managed by uv, with ruff, pyright (strict), and pytest configured through `pyproject.toml` and pre-commit. A root `docker-compose.yml` runs the API plus PostgreSQL (pgvector) and Redis. GitHub Actions CI runs lint, format check, type check, and tests on every push and pull request. A single minimal vertical slice — a `GET /health` endpoint built test-first — proves the toolchain end to end. The foundational stack and architecture decisions are promoted to ADRs under `docs/adr/` at the Spec Gate. Business domains, source connectors, the LLM client, the Dramatiq worker, the APScheduler scheduler, and the Next.js frontend are explicitly deferred to later phases.

## Alternatives Considered
- Backend at the repository root instead of a `backend/` + `frontend/` monorepo: rejected — the planned Next.js frontend would force a disruptive directory move later; the monorepo separates concerns now at low cost.
- Include the Dramatiq worker and APScheduler scheduler services in this phase: rejected for now — there is no job to schedule or actor to process yet, so empty worker and scheduler containers are dead infrastructure; they arrive in Phase 2 (discovery), with the compose file left structured to receive them.
- uv versus Poetry or pip-tools for packaging: chose uv for its speed and integrated lock and virtual-environment handling; Poetry was rejected as slower to resolve and install, and pip-tools as more manual for the dev and CI workflow.

## Scope
- Includes:
  - Monorepo layout: `backend/` (Python package `app/`, `tests/`), a `frontend/` placeholder reserved for the later Next.js app, `docs/adr/`, and root configuration files.
  - `backend/pyproject.toml` with runtime and dev dependencies and tool configuration (ruff, pyright strict, pytest), plus `uv.lock`.
  - `backend/app/main.py` (FastAPI app factory), `backend/app/config.py` (pydantic-settings, env-driven), `backend/app/api/health.py` (`GET /health`).
  - `backend/tests/test_health.py`, written before the implementation (red then green).
  - Root `docker-compose.yml` with three services: api, postgres (pgvector image), redis.
  - `backend/Dockerfile` and `backend/.dockerignore`.
  - `.github/workflows/ci.yml`: `uv sync`, then `ruff check`, `ruff format --check`, `pyright`, and `pytest`.
  - `.pre-commit-config.yaml` (ruff plus standard hooks), `.gitignore`, and `.gitattributes` (normalize line endings to LF).
  - `README.md` following the `github.md` README section order, with runnable Getting Started commands.
  - `docs/adr/0001`–`0004`: the foundational architecture and stack decisions.
  - `.githooks/pre-push`, `scripts/codex-review.sh`, and `AGENTS.md`: the Codex R2 cross-provider review pre-push gate (per `.standards/docs/standards/codex_review.md`), activated locally with `git config core.hooksPath .githooks`.
- Does NOT include:
  - Any business domain (jobs, applications, resumes, profiles, analytics, automations).
  - Source connectors or scraping; the LLM client and provider abstraction; embeddings or any pgvector usage.
  - The Dramatiq worker and APScheduler scheduler services and the Redis-backed queue wiring.
  - Database models, Alembic migrations, or any persistence beyond the running Postgres container.
  - The Next.js frontend implementation (only the reserved directory).
  - Authentication, readiness or database-backed health checks, and notifications.

## Acceptance Criteria
- repo_layout_present: `backend/` (with `pyproject.toml`, `app/`, `tests/`), the `frontend/` placeholder, `docs/adr/`, and the root config files all exist as specified.
- dependencies_install: running `uv sync` in `backend/` installs all dependencies and produces `uv.lock` with no error.
- lint_and_format_clean: `uv run ruff check .` and `uv run ruff format --check .` both pass in `backend/`.
- type_check_clean: `uv run pyright` passes in strict mode with no errors in `backend/`.
- health_test_written_first_and_passes: `backend/tests/test_health.py` asserts `GET /health` returns 200 and body `{"status": "ok"}`; it is committed as a failing test before the implementation commit, then passes.
- compose_starts_and_health_responds: `docker compose up -d` brings up api, postgres, and redis, and `GET http://localhost:8000/health` returns 200 with `{"status": "ok"}`.
- ci_pipeline_runs_checks: `.github/workflows/ci.yml` runs `uv sync`, `ruff check`, `ruff format --check`, `pyright`, and `pytest` on push and pull_request to `main`.
- adrs_recorded: `docs/adr/0001`–`0004` exist, each with Status, Considered Options, and Consequences sections.
- readme_follows_model: `README.md` follows the `github.md` section order and includes runnable Getting Started commands.

## Reproducibility
- Verify on the `chore/phase-0-scaffolding` branch at the PR head.
- Commands (run in `backend/` unless noted): `uv sync`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run pyright`; `uv run pytest`; from the repo root: `docker compose up -d` then `curl http://localhost:8000/health`.
- Versions: Python 3.12; uv pinned in CI; FastAPI, ruff, pyright, and pytest versions pinned in `pyproject.toml` and `uv.lock`; Docker images pinned by tag.
- Platform: Windows 11 for local development; CI on `ubuntu-latest` (GitHub Actions).

## Risks and Assumptions
- Assumption: the recommended-but-open stack items not needed for this phase (vector-store specifics, LLM runtimes, frontend framework details, worker library version) remain open per the PRD Open Questions and do not block scaffolding.
- Assumption: the pgvector Postgres image is used now only to fix the database baseline; no vector features are exercised in this phase.
- Risk: pyright strict on a near-empty codebase is trivially green; real type coverage is exercised as domains land in Phase 1. Mitigation: enable strict from day one so later code inherits it.
- Risk: the root `SPEC.md` is transient and will be overwritten by the next phase's SPEC; the durable rationale for the foundational decisions is captured in ADRs `0001`–`0004` at the Gate, per the decision-records flow.
- Risk: Windows line endings can introduce noise in diffs and CI; mitigated by `.gitattributes` normalizing to LF.
