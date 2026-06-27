# Architecture: modular monolith with asynchronous workers

The system spans job discovery, normalization, deduplication, analysis, scoring, resume
tailoring, application tracking, analytics, and a dashboard, but targets a single user in
V1 and must run locally with minimal operational overhead. We need an architecture that
keeps clear internal boundaries and room to grow without the infrastructure cost of a
distributed system.

## Status

Accepted.

## Considered Options

- **Modular monolith with asynchronous workers (chosen)**: one deployable application
  organized by domain modules, with long-running and scheduled work offloaded to async
  workers. Simple to deploy and operate, low infrastructure, well suited to a single-user
  V1, and evolvable toward extraction later.
- **Microservices**: rejected — excessive complexity and infrastructure for a personal
  single-user system, and premature decomposition before boundaries are proven.
- **Full event-driven system**: partially adopted, not wholesale — an internal queue
  drives the discovery and analysis pipeline, but a fully event-driven architecture is
  rejected as over-engineering for V1; events are used selectively.

## Consequences

- Domain boundaries are enforced by module structure and clear interfaces (group by
  feature, per `code_conventions.md`), not by network boundaries; this requires
  discipline to avoid coupling.
- Background work (discovery, analysis, resume generation) runs via asynchronous workers;
  the processing and scheduling tools are recorded in ADR 0003.
- A module can be extracted into a separate service later if scale demands it; this is not
  anticipated for V1.
