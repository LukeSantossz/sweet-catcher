# Asynchronous processing and scheduling: Dramatiq and APScheduler on Redis

Discovery runs on a schedule, and analysis and resume generation are long-running; they
must run off the request path, be retryable and idempotent, and not require heavy
infrastructure in a single-user V1.

## Status

Accepted.

## Considered Options

- **Dramatiq (Redis broker) + APScheduler (chosen)**: a simple, lightweight task queue on
  Redis that fits a single-user V1, with APScheduler covering the daily discovery
  schedule.
- **Celery + Celery Beat**: rejected — more mature and feature-rich, but heavier and more
  configuration than V1 needs.
- **APScheduler only, in-process**: rejected — not a distributed queue; weaker retries and
  idempotency, and it couples scheduling to the application process.

## Consequences

- Redis is part of the stack and also serves caching, locks, and idempotency keys per the
  PRD.
- The worker and scheduler are deferred to Phase 2 (discovery); the Docker Compose file is
  structured so they can be added without rework.
- Scheduled and queued jobs must be idempotent and retryable per the PRD; this is enforced
  when they are implemented.
