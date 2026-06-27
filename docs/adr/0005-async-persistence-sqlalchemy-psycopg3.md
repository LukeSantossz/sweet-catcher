# Async persistence: SQLAlchemy 2.x sessions with a single psycopg3 driver

Phase 1 introduces the first persistence layer. The backend is an async FastAPI
application (ADR 0002 framed an async API), and database migrations need a driver as well.
We must choose synchronous versus asynchronous sessions and which PostgreSQL driver(s) to
depend on.

## Status

Accepted.

## Considered Options

- **Async SQLAlchemy 2.x with psycopg3 as the single driver (chosen)**: an async engine and
  async sessions for the application via `postgresql+psycopg://`, with the same psycopg3
  driver running Alembic's synchronous migrations. One dependency to pin; async matches the
  FastAPI application and the IO-heavy later phases (workers, LLM, scraping).
- **Synchronous SQLAlchemy sessions**: rejected — contradicts the async API direction of
  ADR 0002, and a later sync-to-async migration would touch every repository.
- **Async application with asyncpg plus a separate sync driver (psycopg2) for Alembic**:
  rejected — two PostgreSQL drivers to pin and maintain; psycopg3 serves both sync and
  async from one dependency.

## Consequences

- `app/db/session.py` holds an async engine and an async session factory; a `get_session`
  FastAPI dependency yields an `AsyncSession`.
- Alembic runs migrations synchronously through the same psycopg3 driver; the application
  uses the async variant of the same URL.
- `database_url` uses the `postgresql+psycopg://` scheme.
- Tests run against a real PostgreSQL with an async engine and per-test transactional
  rollback; `pytest-asyncio` is a dev dependency. JSONB cannot be exercised on SQLite, so a
  PostgreSQL service is required in CI.
- This sets the session and repository pattern that every later domain module follows.
