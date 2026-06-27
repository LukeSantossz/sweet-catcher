# Master Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single, structured, versioned master profile with a manual-entry REST API, backed by the project's first persistence layer.

**Architecture:** Async FastAPI over async SQLAlchemy 2.x (psycopg3) and PostgreSQL. The full profile is a Pydantic v2 DTO stored as one JSONB document per immutable, monotonically numbered version row; the current profile is the highest-numbered version. A `MasterProfileManager` service owns versioning; a `/profile` router exposes manual entry and reads.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x (async), psycopg3, Alembic, Pydantic v2, pytest, pytest-asyncio, httpx (httpx2), uv, ruff, pyright.

## Global Constraints

- Python `>=3.12`; `uv` for dependencies; `package = false`.
- Async SQLAlchemy 2.x with a single `psycopg3` driver; `database_url` scheme `postgresql+psycopg://`.
- Pydantic v2 DTOs, permissive input (`extra="ignore"`); only `basics.full_name` is required, every other field optional or an empty list.
- Versioning: immutable JSONB snapshots, monotonic `version_number` starting at 1; an identical save (equal to the latest) creates no new version (dedupe).
- Tests run against a real PostgreSQL; per-test rollback (no commits in tests). JSONB has no SQLite fallback.
- ruff `select = ["E","F","I","UP","B"]`, `line-length = 100`; pyright `typeCheckingMode = "strict"` over `app` and `tests`.
- Conventional Commits, imperative, lowercase, no trailing period; no co-author or AI-attribution lines. All output in English.
- TDD: a failing-test commit (`test(...)`) precedes its implementation commit (`feat(...)`).
- Local DB: `docker compose up -d postgres`. Default `DATABASE_URL=postgresql+psycopg://app:app@localhost:5432/sweet_catcher`.

---

## File Structure

- `backend/app/db/base.py` — `Base` declarative base (shared metadata).
- `backend/app/db/session.py` — async engine, `AsyncSession` factory, `get_session` dependency.
- `backend/app/config.py` — modify: `database_url` default to the psycopg3 scheme.
- `backend/app/profile/__init__.py` — package marker.
- `backend/app/profile/schemas.py` — Pydantic DTOs + enums + response models.
- `backend/app/profile/models.py` — ORM `MasterProfile`, `MasterProfileVersion`.
- `backend/app/profile/service.py` — `MasterProfileManager` versioning logic.
- `backend/app/profile/router.py` — `/profile` FastAPI router.
- `backend/app/main.py` — modify: include the profile router.
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_create_master_profile.py` — migrations.
- `backend/tests/test_session.py` — session-module unit tests.
- `backend/tests/conftest.py` — async DB fixtures (engine, session, client).
- `backend/tests/profile/__init__.py`, `test_schemas.py`, `test_service.py`, `test_router.py`, `test_migration.py`.
- `backend/pyproject.toml` — modify: dependencies + `asyncio_mode`.
- `docker-compose.yml` — modify: api `DATABASE_URL` scheme.
- `.github/workflows/ci.yml` — modify: PostgreSQL service + `DATABASE_URL`.
- `README.md` — modify: profile API + migrations note.

---

## Task 1: Persistence foundation (deps, db module, config)

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/app/db/base.py`, `backend/app/db/session.py`
- Modify: `backend/app/config.py:8`
- Modify: `docker-compose.yml:8`
- Test: `backend/tests/test_session.py`

**Interfaces:**
- Produces: `app.db.base.Base` (DeclarativeBase subclass); `app.db.session.engine` (`AsyncEngine`), `app.db.session.SessionFactory` (`async_sessionmaker[AsyncSession]`), `app.db.session.get_session() -> AsyncIterator[AsyncSession]`.

- [ ] **Step 1: Add runtime dependencies**

Run (in `backend/`):
```bash
uv add 'sqlalchemy[asyncio]>=2.0' alembic 'psycopg[binary]>=3.2'
```
Expected: `pyproject.toml` `[project].dependencies` now also lists `sqlalchemy[asyncio]`, `alembic`, `psycopg[binary]`; `uv.lock` updated.

- [ ] **Step 2: Commit the dependency change**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "build: add async persistence dependencies"
```

- [ ] **Step 3: Write the failing tests**

Create `backend/tests/test_session.py`:
```python
import inspect

from app.config import get_settings
from app.db.session import get_session


def test_database_url_uses_psycopg_driver() -> None:
    assert get_settings().database_url.startswith("postgresql+psycopg://")


def test_get_session_is_async_generator() -> None:
    assert inspect.isasyncgenfunction(get_session)
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_session.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'` (and the URL assertion would fail too).

- [ ] **Step 5: Create the declarative base**

Create `backend/app/db/base.py`:
```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 6: Create the session module**

Create `backend/app/db/session.py`:
```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

engine: AsyncEngine = create_async_engine(get_settings().database_url)
SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 7: Switch the database URL to psycopg3**

Modify `backend/app/config.py` line 8:
```python
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/sweet_catcher"
```

- [ ] **Step 8: Align Docker Compose to the psycopg3 scheme**

Modify `docker-compose.yml` line 8 (the api service `DATABASE_URL`):
```yaml
      DATABASE_URL: postgresql+psycopg://app:app@postgres:5432/sweet_catcher
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `uv run pytest tests/test_session.py -v`
Expected: PASS (2 passed).

- [ ] **Step 10: Run the quality gates**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: no errors.

- [ ] **Step 11: Commit**

```bash
git add backend/app/db backend/app/config.py backend/tests/test_session.py docker-compose.yml
git commit -m "feat(db): add async engine and session on psycopg3 driver"
```

---

## Task 2: Profile schemas (Pydantic DTOs)

**Files:**
- Create: `backend/app/profile/__init__.py`, `backend/app/profile/schemas.py`
- Test: `backend/tests/profile/__init__.py`, `backend/tests/profile/test_schemas.py`

**Interfaces:**
- Produces: `MasterProfileData` and section models `Basics`, `Experience`, `Project`, `TechnicalSkill`, `Education`, `Certification`, `Language`, `Link`, `JobPreferences`; enums `ProficiencyLevel`, `LanguageProficiency`, `WorkMode`, `LinkType`; response models `ProfileVersionData`, `ProfileVersionMeta`. `MasterProfileData` fields: `basics: Basics`, `experiences`, `projects`, `technical_skills`, `interpersonal_skills: list[str]`, `education`, `certifications`, `languages`, `links`, `job_preferences: JobPreferences`, `key_achievements: list[str]`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/profile/__init__.py` (empty file).

Create `backend/tests/profile/test_schemas.py`:
```python
import pytest
from pydantic import ValidationError

from app.profile.schemas import Experience, MasterProfileData


def test_requires_full_name() -> None:
    with pytest.raises(ValidationError):
        MasterProfileData.model_validate({"basics": {}})


def test_minimal_profile_is_valid() -> None:
    profile = MasterProfileData.model_validate({"basics": {"full_name": "Ada Lovelace"}})
    assert profile.basics.full_name == "Ada Lovelace"
    assert profile.experiences == []
    assert profile.key_achievements == []


def test_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        Experience.model_validate(
            {
                "company": "Acme",
                "role": "Dev",
                "start_date": "2023-01-01",
                "end_date": "2022-01-01",
            }
        )


def test_is_current_forbids_end_date() -> None:
    with pytest.raises(ValidationError):
        Experience.model_validate(
            {
                "company": "Acme",
                "role": "Dev",
                "start_date": "2023-01-01",
                "end_date": "2024-01-01",
                "is_current": True,
            }
        )


def test_not_current_requires_end_date() -> None:
    with pytest.raises(ValidationError):
        Experience.model_validate(
            {"company": "Acme", "role": "Dev", "start_date": "2023-01-01"}
        )


def test_ignores_unknown_fields() -> None:
    profile = MasterProfileData.model_validate(
        {"basics": {"full_name": "Ada"}, "unexpected": "x"}
    )
    assert not hasattr(profile, "unexpected")


def test_accepts_key_achievements() -> None:
    profile = MasterProfileData.model_validate(
        {"basics": {"full_name": "Ada"}, "key_achievements": ["Cut latency by 60%"]}
    )
    assert profile.key_achievements == ["Cut latency by 60%"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/profile/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.profile'`.

- [ ] **Step 3: Create the profile package marker**

Create `backend/app/profile/__init__.py` (empty file).

- [ ] **Step 4: Implement the schemas**

Create `backend/app/profile/schemas.py`:
```python
from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class _ProfileModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ProficiencyLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class LanguageProficiency(str, Enum):
    elementary = "elementary"
    limited_working = "limited_working"
    professional_working = "professional_working"
    full_professional = "full_professional"
    native = "native"


class WorkMode(str, Enum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class LinkType(str, Enum):
    github = "github"
    linkedin = "linkedin"
    portfolio = "portfolio"
    website = "website"
    other = "other"


class Basics(_ProfileModel):
    full_name: str
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None


class Experience(_ProfileModel):
    company: str
    role: str
    employment_type: str | None = None
    location: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_dates(self) -> Experience:
        if self.is_current and self.end_date is not None:
            raise ValueError("end_date must be empty when is_current is true")
        if not self.is_current and self.end_date is None:
            raise ValueError("end_date is required when is_current is false")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must not be earlier than start_date")
        return self


class Project(_ProfileModel):
    name: str
    description: str | None = None
    role: str | None = None
    url: HttpUrl | None = None
    repository_url: HttpUrl | None = None
    start_date: date | None = None
    end_date: date | None = None
    highlights: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class TechnicalSkill(_ProfileModel):
    name: str
    category: str | None = None
    proficiency: ProficiencyLevel | None = None
    years_experience: float | None = None


class Education(_ProfileModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    location: str | None = None
    description: str | None = None


class Certification(_ProfileModel):
    name: str
    issuer: str | None = None
    issue_date: date | None = None
    expiration_date: date | None = None
    credential_id: str | None = None
    url: HttpUrl | None = None


class Language(_ProfileModel):
    name: str
    proficiency: LanguageProficiency


class Link(_ProfileModel):
    url: HttpUrl
    type: LinkType | None = None
    label: str | None = None


class JobPreferences(_ProfileModel):
    desired_roles: list[str] = Field(default_factory=list)
    seniority_levels: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)
    work_modes: list[WorkMode] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    min_salary: int | None = None
    salary_currency: str | None = None
    accepted_languages: list[str] = Field(default_factory=list)
    employment_types: list[str] = Field(default_factory=list)
    open_to_relocation: bool | None = None
    availability: str | None = None


class MasterProfileData(_ProfileModel):
    basics: Basics
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    technical_skills: list[TechnicalSkill] = Field(default_factory=list)
    interpersonal_skills: list[str] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    job_preferences: JobPreferences = Field(default_factory=JobPreferences)
    key_achievements: list[str] = Field(default_factory=list)


class ProfileVersionMeta(BaseModel):
    version_number: int
    created_at: datetime
    note: str | None = None


class ProfileVersionData(BaseModel):
    version_number: int
    created_at: datetime
    note: str | None = None
    data: MasterProfileData
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/profile/test_schemas.py -v`
Expected: PASS (7 passed).

- [ ] **Step 6: Run the quality gates**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: no errors.

- [ ] **Step 7: Commit (red then green)**

```bash
git add backend/tests/profile/__init__.py backend/tests/profile/test_schemas.py
git commit -m "test(profile): specify master profile schema validation"
git add backend/app/profile/__init__.py backend/app/profile/schemas.py
git commit -m "feat(profile): add master profile data schemas"
```

---

## Task 3: ORM models, Alembic, and test DB scaffolding

**Files:**
- Create: `backend/app/profile/models.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_create_master_profile.py`
- Modify: `backend/pyproject.toml` (`asyncio_mode`, dev dep)
- Create: `backend/tests/conftest.py`, `backend/tests/profile/test_migration.py`

**Interfaces:**
- Consumes: `app.db.base.Base`, `app.db.session.get_session`, `app.config.get_settings`.
- Produces: ORM `MasterProfile` (`id`, `created_at`, `updated_at`, `versions`) and `MasterProfileVersion` (`id`, `profile_id`, `version_number`, `created_at`, `note`, `data: dict[str, Any]`); pytest fixtures `engine` (`AsyncEngine`), `db_session` (`AsyncSession`), `client` (`AsyncClient`).

- [ ] **Step 1: Add the async test dependency and config**

Run (in `backend/`): `uv add --dev pytest-asyncio`

Then modify `backend/pyproject.toml` `[tool.pytest.ini_options]` to:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
```

- [ ] **Step 2: Write the failing migration test**

Create `backend/tests/profile/test_migration.py`:
```python
from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import AsyncEngine


def _table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


async def test_migration_creates_master_profile_tables(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        tables = await connection.run_sync(_table_names)
    assert {"master_profile", "master_profile_version"} <= tables
```

- [ ] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/profile/test_migration.py -v`
Expected: FAIL — `fixture 'engine' not found` (conftest and migration not yet present).

- [ ] **Step 4: Implement the ORM models**

Create `backend/app/profile/models.py`:
```python
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MasterProfile(Base):
    __tablename__ = "master_profile"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["MasterProfileVersion"]] = relationship(
        back_populates="profile",
        order_by="MasterProfileVersion.version_number",
    )


class MasterProfileVersion(Base):
    __tablename__ = "master_profile_version"
    __table_args__ = (UniqueConstraint("profile_id", "version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("master_profile.id"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)

    profile: Mapped["MasterProfile"] = relationship(back_populates="versions")
```

- [ ] **Step 5: Create the Alembic config**

Create `backend/alembic.ini`:
```ini
[alembic]
script_location = %(here)s/alembic
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 6: Create the Alembic environment**

Create `backend/alembic/env.py`:
```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db.base import Base
from app.profile import models  # noqa: F401  (register tables on the metadata)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Create the initial migration**

Create `backend/alembic/versions/0001_create_master_profile.py`:
```python
"""create master profile tables

Revision ID: 0001_create_master_profile
Revises:
Create Date: 2026-06-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_master_profile"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "master_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "master_profile_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["master_profile.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "version_number"),
    )
    op.create_index(
        op.f("ix_master_profile_version_profile_id"),
        "master_profile_version",
        ["profile_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_master_profile_version_profile_id"),
        table_name="master_profile_version",
    )
    op.drop_table("master_profile_version")
    op.drop_table("master_profile")
```

- [ ] **Step 8: Create the test fixtures**

Create `backend/tests/conftest.py`:
```python
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.config import get_settings
from app.db.session import get_session
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


@pytest.fixture(scope="session")
def _schema() -> None:
    command.upgrade(Config(str(ALEMBIC_INI)), "head")


@pytest_asyncio.fixture
async def engine(_schema: None) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(get_settings().database_url)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def _override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
```

- [ ] **Step 9: Run the migration test to verify it passes**

Prerequisite: `docker compose up -d postgres` is running.
Run: `uv run pytest tests/profile/test_migration.py -v`
Expected: PASS (1 passed).

- [ ] **Step 10: Run the quality gates**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: no errors.

- [ ] **Step 11: Commit (red then green)**

```bash
git add backend/tests/profile/test_migration.py backend/pyproject.toml backend/uv.lock
git commit -m "test(profile): assert the initial migration creates the profile tables"
git add backend/app/profile/models.py backend/alembic.ini backend/alembic backend/tests/conftest.py
git commit -m "feat(profile): add profile ORM models and initial migration"
```

---

## Task 4: MasterProfileManager service

**Files:**
- Create: `backend/app/profile/service.py`
- Test: `backend/tests/profile/test_service.py`

**Interfaces:**
- Consumes: `MasterProfileData` (schemas), `MasterProfile`/`MasterProfileVersion` (models), `AsyncSession`.
- Produces: `MasterProfileManager(session)` with `async get_or_create_profile() -> MasterProfile`, `async get_current() -> MasterProfileVersion | None`, `async create_version(data: MasterProfileData, note: str | None = None) -> MasterProfileVersion`, `async list_versions() -> list[MasterProfileVersion]`, `async get_version(version_number: int) -> MasterProfileVersion | None`, `async restore_version(version_number: int) -> MasterProfileVersion | None`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/profile/test_service.py`:
```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.profile.schemas import MasterProfileData
from app.profile.service import MasterProfileManager


def _data(full_name: str) -> MasterProfileData:
    return MasterProfileData.model_validate({"basics": {"full_name": full_name}})


async def test_first_save_creates_version_one(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    version = await manager.create_version(_data("Ada"))
    assert version.version_number == 1


async def test_distinct_save_increments_version(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    await manager.create_version(_data("Ada"))
    second = await manager.create_version(_data("Grace"))
    assert second.version_number == 2


async def test_identical_save_is_deduped(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    first = await manager.create_version(_data("Ada"))
    again = await manager.create_version(_data("Ada"))
    assert again.version_number == first.version_number
    assert len(await manager.list_versions()) == 1


async def test_get_current_returns_latest(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    await manager.create_version(_data("Ada"))
    await manager.create_version(_data("Grace"))
    current = await manager.get_current()
    assert current is not None
    assert current.version_number == 2
    assert current.data["basics"]["full_name"] == "Grace"


async def test_list_versions_is_descending(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    await manager.create_version(_data("Ada"))
    await manager.create_version(_data("Grace"))
    numbers = [v.version_number for v in await manager.list_versions()]
    assert numbers == [2, 1]


async def test_restore_creates_new_version_from_source(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    await manager.create_version(_data("Ada"))
    await manager.create_version(_data("Grace"))
    restored = await manager.restore_version(1)
    assert restored is not None
    assert restored.version_number == 3
    assert restored.data["basics"]["full_name"] == "Ada"


async def test_restore_missing_version_returns_none(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    assert await manager.restore_version(99) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/profile/test_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.profile.service'`.

- [ ] **Step 3: Implement the service**

Create `backend/app/profile/service.py`:
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.profile.models import MasterProfile, MasterProfileVersion
from app.profile.schemas import MasterProfileData


class MasterProfileManager:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_profile(self) -> MasterProfile:
        result = await self._session.execute(select(MasterProfile).limit(1))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = MasterProfile()
            self._session.add(profile)
            await self._session.flush()
        return profile

    async def get_current(self) -> MasterProfileVersion | None:
        result = await self._session.execute(
            select(MasterProfileVersion)
            .order_by(MasterProfileVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_version(
        self, data: MasterProfileData, note: str | None = None
    ) -> MasterProfileVersion:
        profile = await self.get_or_create_profile()
        latest = await self.get_current()
        payload = data.model_dump(mode="json")
        if latest is not None and latest.data == payload:
            return latest
        next_number = latest.version_number + 1 if latest is not None else 1
        version = MasterProfileVersion(
            profile_id=profile.id,
            version_number=next_number,
            note=note,
            data=payload,
        )
        self._session.add(version)
        await self._session.flush()
        await self._session.refresh(version)
        return version

    async def list_versions(self) -> list[MasterProfileVersion]:
        result = await self._session.execute(
            select(MasterProfileVersion).order_by(
                MasterProfileVersion.version_number.desc()
            )
        )
        return list(result.scalars().all())

    async def get_version(self, version_number: int) -> MasterProfileVersion | None:
        result = await self._session.execute(
            select(MasterProfileVersion).where(
                MasterProfileVersion.version_number == version_number
            )
        )
        return result.scalar_one_or_none()

    async def restore_version(
        self, version_number: int
    ) -> MasterProfileVersion | None:
        source = await self.get_version(version_number)
        if source is None:
            return None
        data = MasterProfileData.model_validate(source.data)
        return await self.create_version(data, note=f"restored from v{version_number}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/profile/test_service.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Run the quality gates**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: no errors.

- [ ] **Step 6: Commit (red then green)**

```bash
git add backend/tests/profile/test_service.py
git commit -m "test(profile): specify master profile versioning service"
git add backend/app/profile/service.py
git commit -m "feat(profile): add master profile versioning service"
```

---

## Task 5: Profile API router

**Files:**
- Create: `backend/app/profile/router.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/profile/test_router.py`

**Interfaces:**
- Consumes: `get_session` (session), `MasterProfileManager` (service), `MasterProfileData`/`ProfileVersionData`/`ProfileVersionMeta` (schemas), `MasterProfileVersion` (models).
- Produces: `router` (APIRouter, prefix `/profile`) with `GET ""`, `PUT ""`, `GET "/versions"`, `GET "/versions/{version_number}"`, `POST "/versions/{version_number}/restore"`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/profile/test_router.py`:
```python
from httpx import AsyncClient

ADA = {"basics": {"full_name": "Ada"}}
GRACE = {"basics": {"full_name": "Grace"}}


async def test_get_current_returns_404_when_empty(client: AsyncClient) -> None:
    response = await client.get("/profile")
    assert response.status_code == 404


async def test_put_creates_versions(client: AsyncClient) -> None:
    first = await client.put("/profile", json=ADA)
    assert first.status_code == 201
    assert first.json()["version_number"] == 1
    second = await client.put("/profile", json=GRACE)
    assert second.status_code == 201
    assert second.json()["version_number"] == 2


async def test_put_identical_returns_200_without_new_version(
    client: AsyncClient,
) -> None:
    await client.put("/profile", json=ADA)
    again = await client.put("/profile", json=ADA)
    assert again.status_code == 200
    assert again.json()["version_number"] == 1


async def test_get_current_returns_latest(client: AsyncClient) -> None:
    await client.put("/profile", json=ADA)
    await client.put("/profile", json=GRACE)
    response = await client.get("/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["version_number"] == 2
    assert body["data"]["basics"]["full_name"] == "Grace"


async def test_list_versions(client: AsyncClient) -> None:
    await client.put("/profile", json=ADA)
    await client.put("/profile", json=GRACE)
    response = await client.get("/profile/versions")
    assert response.status_code == 200
    items = response.json()
    assert [v["version_number"] for v in items] == [2, 1]
    assert all("data" not in v for v in items)


async def test_get_version_not_found(client: AsyncClient) -> None:
    response = await client.get("/profile/versions/99")
    assert response.status_code == 404


async def test_invalid_body_returns_422(client: AsyncClient) -> None:
    response = await client.put("/profile", json={"basics": {}})
    assert response.status_code == 422


async def test_restore_creates_new_version(client: AsyncClient) -> None:
    await client.put("/profile", json=ADA)
    await client.put("/profile", json=GRACE)
    response = await client.post("/profile/versions/1/restore")
    assert response.status_code == 201
    assert response.json()["version_number"] == 3
    assert response.json()["data"]["basics"]["full_name"] == "Ada"


async def test_restore_missing_returns_404(client: AsyncClient) -> None:
    response = await client.post("/profile/versions/99/restore")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/profile/test_router.py -v`
Expected: FAIL — every request returns 404 (the `/profile` routes are not registered yet).

- [ ] **Step 3: Implement the router**

Create `backend/app/profile/router.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.profile.models import MasterProfileVersion
from app.profile.schemas import (
    MasterProfileData,
    ProfileVersionData,
    ProfileVersionMeta,
)
from app.profile.service import MasterProfileManager

router = APIRouter(prefix="/profile", tags=["profile"])


def get_manager(
    session: AsyncSession = Depends(get_session),
) -> MasterProfileManager:
    return MasterProfileManager(session)


def _to_version_data(version: MasterProfileVersion) -> ProfileVersionData:
    return ProfileVersionData(
        version_number=version.version_number,
        created_at=version.created_at,
        note=version.note,
        data=MasterProfileData.model_validate(version.data),
    )


@router.get("", response_model=ProfileVersionData)
async def get_current_profile(
    manager: MasterProfileManager = Depends(get_manager),
) -> ProfileVersionData:
    version = await manager.get_current()
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no master profile yet"
        )
    return _to_version_data(version)


@router.put("", response_model=ProfileVersionData)
async def put_profile(
    data: MasterProfileData,
    response: Response,
    manager: MasterProfileManager = Depends(get_manager),
) -> ProfileVersionData:
    before = await manager.get_current()
    version = await manager.create_version(data)
    is_new = before is None or version.version_number != before.version_number
    response.status_code = (
        status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
    )
    return _to_version_data(version)


@router.get("/versions", response_model=list[ProfileVersionMeta])
async def list_versions(
    manager: MasterProfileManager = Depends(get_manager),
) -> list[ProfileVersionMeta]:
    versions = await manager.list_versions()
    return [
        ProfileVersionMeta(
            version_number=v.version_number, created_at=v.created_at, note=v.note
        )
        for v in versions
    ]


@router.get("/versions/{version_number}", response_model=ProfileVersionData)
async def get_version(
    version_number: int,
    manager: MasterProfileManager = Depends(get_manager),
) -> ProfileVersionData:
    version = await manager.get_version(version_number)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="version not found"
        )
    return _to_version_data(version)


@router.post(
    "/versions/{version_number}/restore",
    response_model=ProfileVersionData,
    status_code=status.HTTP_201_CREATED,
)
async def restore_version(
    version_number: int,
    manager: MasterProfileManager = Depends(get_manager),
) -> ProfileVersionData:
    version = await manager.restore_version(version_number)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="version not found"
        )
    return _to_version_data(version)
```

- [ ] **Step 4: Wire the router into the app**

Modify `backend/app/main.py` to:
```python
from fastapi import FastAPI

from app.api.health import router as health_router
from app.profile.router import router as profile_router


def create_app() -> FastAPI:
    app = FastAPI(title="Personal AI Job Hunter")
    app.include_router(health_router)
    app.include_router(profile_router)
    return app


app = create_app()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/profile/test_router.py -v`
Expected: PASS (9 passed).

- [ ] **Step 6: Run the full suite and quality gates**

Run: `uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: all pass; no errors.

- [ ] **Step 7: Commit (red then green)**

```bash
git add backend/tests/profile/test_router.py
git commit -m "test(profile): specify master profile API endpoints"
git add backend/app/profile/router.py backend/app/main.py
git commit -m "feat(profile): add master profile API router"
```

---

## Task 6: CI PostgreSQL service and README

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing new; provides a PostgreSQL service so `pytest` (which migrates and rolls back) can run in CI.

- [ ] **Step 1: Add a PostgreSQL service to the check job**

Modify `.github/workflows/ci.yml` so the `check` job declares a service and a test `DATABASE_URL`. Replace the `jobs:` block with:
```yaml
jobs:
  check:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
          POSTGRES_DB: sweet_catcher
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+psycopg://app:app@localhost:5432/sweet_catcher
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "0.11.15"
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

- [ ] **Step 2: Verify the workflow indentation**

Re-read `.github/workflows/ci.yml` and confirm 2-space YAML indentation: `services`, `env`, and `steps` are all keys of the `check` job at the same level. The workflow is fully validated by GitHub Actions on the next push.

- [ ] **Step 3: Update the README**

In `README.md`, under `## Tech Stack`, add `SQLAlchemy 2.x, Alembic` to the data-layer line; under `## Engineering Decisions`, add two rows:
```markdown
| Async persistence (SQLAlchemy + psycopg3) | [docs/adr/0005-async-persistence-sqlalchemy-psycopg3.md](docs/adr/0005-async-persistence-sqlalchemy-psycopg3.md) |
| Master-profile versioning (JSONB snapshots) | [docs/adr/0006-master-profile-versioning-jsonb-snapshots.md](docs/adr/0006-master-profile-versioning-jsonb-snapshots.md) |
```
Under `### Running`, after the compose block, add a migrations-and-profile note:
```markdown
Apply migrations and use the profile API:

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
```
Update `## Project Status` to note Phase 1 (master profile) in progress, and the resume standard reference (`docs/resume-standard.md`).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml README.md
git commit -m "ci: run tests against a postgresql service and document the profile api"
```

---

## Self-Review

**Spec coverage** — each Acceptance Criterion maps to a task:
- schema_requires_full_name, schema_rejects_inverted_dates, schema_enforces_is_current_rule, schema_ignores_unknown_fields, schema_accepts_key_achievements → Task 2.
- service_first_save_creates_version_one, service_distinct_save_increments_version, service_identical_save_is_deduped, service_get_current_returns_latest, service_list_versions_excludes_data, service_restore_creates_new_version_from_source → Task 4.
- api_get_current_returns_404_when_empty, api_put_creates_version_and_returns_201, api_put_identical_returns_200_without_new_version, api_get_version_returns_404_when_missing, api_invalid_body_returns_422, api_restore_returns_201_or_404 → Task 5.
- migration_creates_tables → Task 3.
- resume_standard_present → already delivered (`docs/resume-standard.md`).
- quality_gates_pass → every task ends with the ruff/pyright/pytest gate; Task 5/6 run the full suite.

**Note on `service_list_versions_excludes_data`:** the ORM `list_versions` returns full rows, but the API (`ProfileVersionMeta`, Task 5) is what omits `data`; the criterion is verified at the API boundary by `test_list_versions` (no `data` key in the response items). If a service-level guarantee is wanted, it is already covered by the response model.

**Placeholder scan:** none — every code and command step is concrete.

**Type consistency:** `MasterProfileManager` method names and signatures match across Tasks 4–5; `ProfileVersionData`/`ProfileVersionMeta` fields match the router usage; `MasterProfileVersion.data` is `dict[str, Any]` consistent with `model_dump(mode="json")` payloads.
