# Phase 0 Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a runnable, CI-checked modular-monolith skeleton (FastAPI backend + Postgres/pgvector + Redis via Docker Compose) proven by a single test-first `GET /health` slice.

**Architecture:** Monorepo with a Python 3.12 + FastAPI backend under `backend/` and a reserved `frontend/` directory. The backend is a modular monolith; in Phase 0 it contains only configuration and a health endpoint. Dependencies and tooling are managed by uv; quality gates are ruff, pyright (strict), and pytest, enforced locally (pre-commit) and in GitHub Actions CI.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, pydantic-settings, uv, ruff, pyright, pytest, httpx, Docker Compose (PostgreSQL/pgvector, Redis), GitHub Actions.

## Global Constraints

- Python version floor: `requires-python = ">=3.12"`.
- Packaging/dev workflow: uv only; `uv.lock` is committed; the project is a non-package app (`[tool.uv] package = false`).
- Quality gates that must pass: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` (strict), `uv run pytest` — all run from `backend/`.
- Test-first: every implementation step is preceded by a failing-test commit (red → green → refactor). An implementation commit without a preceding failing-test commit is a process violation.
- Commits: Conventional Commits (`type(scope): subject`, imperative, lowercase, no trailing period). No co-author or AI-attribution lines.
- Language: all identifiers, comments, and documentation in English.
- Database: the Postgres image must include pgvector; the relational DB is the source of truth but is NOT exercised in Phase 0 (no models, no migrations, no queries).
- Out of scope for every task here: business domains, source connectors, the LLM client, the Dramatiq worker, the APScheduler scheduler, and the Next.js frontend implementation.

**Prerequisites (executor's machine):** uv installed (`pip install uv` or the official installer); Docker Desktop running (for Task 4 only). pyright is installed as a dev dependency, so Node is not a separate prerequisite.

---

### Task 1: Bootstrap backend project, toolchain, and repo ignores

**Files:**
- Create: `backend/pyproject.toml`
- Create: `.gitignore`
- Create: `.gitattributes`
- Create: `frontend/.gitkeep`
- Generated: `backend/uv.lock`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: a synced uv environment in `backend/` with runtime deps (fastapi, uvicorn, pydantic-settings) and dev deps (pytest, httpx, ruff, pyright); tool config for ruff, pyright (strict), and pytest read from `backend/pyproject.toml`.

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "sweet-catcher-backend"
version = "0.1.0"
description = "Personal AI Job Hunter backend"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic-settings>=2.4",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "httpx>=0.27",
    "ruff>=0.6",
    "pyright>=1.1.380",
]

[tool.uv]
package = false

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pyright]
include = ["app", "tests"]
typeCheckingMode = "strict"
pythonVersion = "3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Create `.gitignore` (repo root)**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/

# Environment
.env

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Create `.gitattributes` (repo root)**

```gitattributes
* text=auto eol=lf
```

- [ ] **Step 4: Create `frontend/.gitkeep`**

Create an empty file at `frontend/.gitkeep` (reserves the directory for the later Next.js app).

- [ ] **Step 5: Sync the environment**

Run (from `backend/`): `uv sync`
Expected: resolves and installs all dependencies and creates `backend/uv.lock` with no error.

- [ ] **Step 6: Verify ruff runs clean**

Run (from `backend/`): `uv run ruff check .` then `uv run ruff format --check .`
Expected: both pass (no files to fix yet).

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock .gitignore .gitattributes frontend/.gitkeep
git commit -m "chore: bootstrap backend project and toolchain"
```

---

### Task 2: Settings module (`config.py`), test-first

**Files:**
- Test: `backend/tests/test_config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`

**Interfaces:**
- Consumes: the uv environment and pytest config from Task 1.
- Produces: `app.config.Settings` (a `pydantic_settings.BaseSettings` with fields `app_env: str`, `database_url: str`, `redis_url: str`) and `app.config.get_settings() -> Settings`.

- [ ] **Step 1: Create empty package markers**

Create empty files `backend/app/__init__.py` and `backend/tests/__init__.py`.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_config.py`:

```python
from app.config import Settings


def test_settings_defaults_to_development() -> None:
    settings = Settings()
    assert settings.app_env == "development"


def test_settings_reads_app_env_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    settings = Settings()
    assert settings.app_env == "production"
```

- [ ] **Step 3: Run the test to verify it fails**

Run (from `backend/`): `uv run pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 4: Write the minimal implementation**

Create `backend/app/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql://app:app@localhost:5432/sweet_catcher"
    redis_url: str = "redis://localhost:6379/0"


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Run the test to verify it passes**

Run (from `backend/`): `uv run pytest tests/test_config.py -v`
Expected: 2 passed.

- [ ] **Step 6: Verify type-check and lint pass**

Run (from `backend/`): `uv run pyright` then `uv run ruff check .`
Expected: both pass with no errors.

- [ ] **Step 7: Commit (test then implementation in one task, test written first)**

```bash
git add backend/app/__init__.py backend/tests/__init__.py backend/tests/test_config.py backend/app/config.py
git commit -m "feat(config): add env-driven settings module"
```

---

### Task 3: Health endpoint (`GET /health`), test-first

**Files:**
- Test: `backend/tests/test_health.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/main.py`

**Interfaces:**
- Consumes: the uv environment from Task 1; `httpx` (dev dep) backs `fastapi.testclient.TestClient`.
- Produces: `app.api.health.router` (an `APIRouter` exposing `GET /health`), `app.main.create_app() -> FastAPI`, and the module-level `app.main.app` ASGI application.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run (from `backend/`): `uv run pytest tests/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3: Create the health router**

Create `backend/app/api/__init__.py` (empty) and `backend/app/api/health.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Create the app factory**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Personal AI Job Hunter")
    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 5: Run the test to verify it passes**

Run (from `backend/`): `uv run pytest tests/test_health.py -v`
Expected: 1 passed.

- [ ] **Step 6: Verify the full gate passes**

Run (from `backend/`): `uv run ruff check .` then `uv run ruff format --check .` then `uv run pyright` then `uv run pytest`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/__init__.py backend/app/api/health.py backend/app/main.py backend/tests/test_health.py
git commit -m "feat(api): add health endpoint"
```

---

### Task 4: Dockerfile and Docker Compose (api + postgres + redis)

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `docker-compose.yml` (repo root)

**Interfaces:**
- Consumes: `app.main:app` from Task 3 (the uvicorn entrypoint) and `backend/pyproject.toml` + `backend/uv.lock` from Task 1.
- Produces: a `docker compose up` environment exposing the API on `localhost:8000`, plus Postgres (pgvector) on `5432` and Redis on `6379`.

- [ ] **Step 1: Create `backend/.dockerignore`**

```dockerignore
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
tests/
.env
```

- [ ] **Step 2: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create `docker-compose.yml` (repo root)**

```yaml
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      APP_ENV: development
      DATABASE_URL: postgresql://app:app@postgres:5432/sweet_catcher
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: sweet_catcher
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

- [ ] **Step 4: Build and start the stack**

Run (from repo root): `docker compose up -d --build`
Expected: `api`, `postgres`, and `redis` containers start.

- [ ] **Step 5: Verify the health endpoint responds**

Run: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}` with HTTP 200.

- [ ] **Step 6: Tear down**

Run (from repo root): `docker compose down`
Expected: containers stop and are removed (the `postgres_data` volume persists).

- [ ] **Step 7: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore docker-compose.yml
git commit -m "chore: add dockerfile and docker compose for local stack"
```

---

### Task 5: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: the quality gates from Tasks 1–3 (`uv sync`, ruff, pyright, pytest), all run with working directory `backend`.
- Produces: a CI workflow that runs on push to `main` and on every pull request.

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

defaults:
  run:
    working-directory: backend

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync --frozen
      - name: Lint
        run: uv run ruff check .
      - name: Format check
        run: uv run ruff format --check .
      - name: Type check
        run: uv run pyright
      - name: Test
        run: uv run pytest
```

- [ ] **Step 2: Verify the workflow commands pass locally (CI parity)**

Run (from `backend/`): `uv sync --frozen` then `uv run ruff check .` then `uv run ruff format --check .` then `uv run pyright` then `uv run pytest`
Expected: every command exits 0 — this is exactly what CI runs.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add lint, type-check, and test workflow"
```

---

### Task 6: pre-commit hooks and README

**Files:**
- Create: `.pre-commit-config.yaml` (repo root)
- Create: `README.md` (repo root)

**Interfaces:**
- Consumes: ruff (from the toolchain) and the ADRs in `docs/adr/`.
- Produces: a working `pre-commit` configuration and a `README.md` following the `github.md` section order.

- [ ] **Step 1: Create `.pre-commit-config.yaml` (repo root)**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
```

- [ ] **Step 2: Pin hook revisions and run them**

Run (from repo root): `pre-commit autoupdate` (pins `rev`s to the latest stable tags), then `pre-commit run --all-files`
Expected: hooks install and pass (or auto-fix, after which re-running passes).

- [ ] **Step 3: Create `README.md` (repo root)**

```markdown
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
```

- [ ] **Step 4: Verify README links resolve**

Run (from repo root): `ls docs/adr`
Expected: the four ADR files referenced in the README's Engineering Decisions table exist.

- [ ] **Step 5: Commit**

```bash
git add .pre-commit-config.yaml README.md
git commit -m "docs: add pre-commit config and project readme"
```

---

## Self-Review

**1. Spec coverage:**
- `repo_layout_present` → Task 1 (backend project, ignores, frontend placeholder) + Tasks 2–3 (`app/`, `tests/`).
- `dependencies_install` → Task 1 Step 5 (`uv sync`).
- `lint_and_format_clean` → Tasks 1/2/3 ruff steps.
- `type_check_clean` → Tasks 2/3 pyright steps.
- `health_test_written_first_and_passes` → Task 3 (test written Step 1, passes Step 5).
- `compose_starts_and_health_responds` → Task 4 Steps 4–5.
- `ci_pipeline_runs_checks` → Task 5.
- `adrs_recorded` → already committed at the Gate; README references them in Task 6.
- `readme_follows_model` → Task 6 Step 3.
No gaps.

**2. Placeholder scan:** No "TBD/TODO/implement later"; every code step shows complete content. The only deferred items are explicitly out of Phase 0 scope.

**3. Type consistency:** `create_app() -> FastAPI` and module-level `app` (Task 3) are consumed verbatim by the Dockerfile/compose `app.main:app` (Task 4). `Settings`/`get_settings` (Task 2) names are stable. `health()` returns `dict[str, str]` matching the test's `{"status": "ok"}` assertion.
