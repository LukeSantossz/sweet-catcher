# Backend and persistence stack: Python, FastAPI, PostgreSQL/pgvector, SQLAlchemy, Alembic

V1 needs a backend language and framework, a database, and an ORM and migrations tool
aligned with the AI, NLP, and scraping workload and with the open-source, local-first
constraint of the PRD.

## Status

Accepted.

## Considered Options

- **Python 3.12 + FastAPI + PostgreSQL (pgvector) + SQLAlchemy 2.x + Alembic (chosen)**:
  strong AI/ML/scraping/NLP ecosystem; async API with Pydantic validation and automatic
  OpenAPI; PostgreSQL as the relational source of truth with JSONB, full-text search, and
  pgvector for embeddings without a separate vector database; SQLAlchemy 2.x as a typed
  ORM with Alembic migrations.
- **TypeScript + NestJS**: rejected — weaker local-LLM, ML, and scraping ecosystem and
  more friction integrating open-source models.
- **Go**: rejected — the poorest AI/LLM ecosystem and more boilerplate for this domain.
- **SQLite instead of PostgreSQL**: rejected — no pgvector, weaker concurrency for
  workers, and limited full-text search; it would force a migration once embeddings and
  vector search are needed.
- **SQLModel instead of SQLAlchemy**: rejected — younger and a thinner abstraction with
  rough edges for advanced cases; SQLAlchemy 2.x chosen for maturity.

## Consequences

- Strong typing is enforced (pyright strict, Pydantic DTOs) per the PRD non-functional
  requirements.
- The pgvector Postgres image is present from Phase 0, but vector features are used only
  in later phases.
- Alembic migrations are introduced when the first models land (Phase 1), not in Phase 0.
- Running the system requires a Postgres instance plus the application; both are provided
  by Docker Compose.
- The choice between pgvector and a dedicated vector store (e.g., Qdrant) remains open per
  the PRD; pgvector is the V1 default and is revisited only if vector volume grows enough
  to warrant a dedicated store.
