# SPEC: feat(jobs): add Remotive and Remote Rocketship source connectors

## Problem

Job discovery only has a deterministic `MockConnector`, so the system cannot ingest real
postings from external sources.

## Design Decision

Introduce a multi-source ingestion layer behind the existing `SourceConnector` protocol: a
shared polite HTTP client plus two concrete connectors. `RemotiveConnector` reads the public
Remotive JSON API as a stable baseline, and `RemoteRocketshipConnector` extracts postings from
Remote Rocketship's embedded Next.js `__NEXT_DATA__` payload (structured JSON, not fragile DOM
scraping). The polite client centralises an identifiable User-Agent, timeouts, retry with
exponential backoff, and a per-host minimum interval; connectors map each posting into the
common `RawJob` payload vocabulary and let `normalize()`/`DiscoveryService` handle validation,
deduplication, and per-source error isolation that already exist.

## Alternatives Considered

- **Single API connector only (e.g. Remotive):** rejected — it does not satisfy the multi-source
  intent, and the architecture must prove the scraping path now so Seek NZ and LinkedIn can
  follow as later slices behind the same interface.
- **DOM/CSS scraping of Remote Rocketship's rendered HTML:** rejected — brittle against markup
  changes; the site is a Next.js Pages Router app that already embeds the full listing as
  structured JSON in `__NEXT_DATA__`, a far more stable extraction target.
- **Headless browser (Playwright) for scraping:** rejected — heavyweight dependency and slow;
  unnecessary because the listing data is present in the initial server-rendered HTML.
- **A third HTTP stack / HTML parser dependency (httpx, beautifulsoup4, lxml):** rejected for
  this slice — the repository already standardises on `httpx2`, and the only structured payload
  needed (`__NEXT_DATA__`) is extractable with the standard library, keeping the dependency
  footprint and the pyright-strict surface minimal.

## Scope

- Includes:
  - `app/jobs/connectors/http.py`: a `PoliteClient` wrapping `httpx2.AsyncClient` with an
    identifiable User-Agent, timeout, retry + exponential backoff on transient errors
    (transport failures, 429, 5xx), and a per-host minimum request interval. Injectable
    transport, clock, and sleep for hermetic, time-free tests.
  - `app/jobs/connectors/remotive.py`: `RemotiveConnector` (`name = "remotive"`) reading
    `https://remotive.com/api/remote-jobs` and mapping each job to a `RawJob`.
  - `app/jobs/connectors/remote_rocketship.py`: `RemoteRocketshipConnector`
    (`name = "remote_rocketship"`) reading the listing page(s), extracting
    `props.pageProps.initialJobOpenings` from `__NEXT_DATA__`, with a configurable page cap.
  - Register both in `default_connectors()` alongside `MockConnector`.
  - Promote `httpx2` from the dev group to a runtime dependency.
  - README API/decision touch-ups and ADR 0008 (multi-source ingestion strategy).
- Does NOT include:
  - Seek NZ and LinkedIn connectors (subsequent slices, same interface).
  - Mapping `SearchCriteria` filters (keywords, location, salary) into source query parameters;
    V1 fetches recent listings (Remote Rocketship sorted by date, capped pages; Remotive default
    feed). Criteria-driven querying is a later enhancement.
  - robots.txt enforcement (posture: advisory, not a hard block), response caching/persistence,
    proxy rotation, and any CAPTCHA/anti-detection handling (never).
  - Worker/scheduler execution (slice 2.4) and per-row atomic upsert hardening (still deferred).
  - Changes to the `SearchCriteria` schema; new source names are plain strings in
    `active_sources`.

## Acceptance Criteria

Polite HTTP client (`tests/jobs/connectors/test_http.py`):

- `polite_client_sends_identifiable_user_agent`
- `polite_client_retries_transient_error_then_returns_body`
- `polite_client_raises_after_exhausting_retries`
- `polite_client_does_not_retry_on_client_error`
- `polite_client_waits_minimum_interval_between_requests_to_same_host`

Remotive connector (`tests/jobs/connectors/test_remotive.py`):

- `remotive_maps_api_jobs_to_rawjobs` (source, external_id, title, company, url, work_mode
  "remote", contract_type from job_type, technologies from tags, posted_at, location, description)
- `remotive_produced_rawjobs_normalize_into_valid_jobdata`
- `remotive_returns_empty_list_when_api_has_no_jobs`

Remote Rocketship connector (`tests/jobs/connectors/test_remote_rocketship.py`):

- `remote_rocketship_extracts_jobs_from_next_data` (external_id from id, title from roleTitle,
  company from company.name, url, work_mode from locationType, contract_type from employmentType,
  technologies from techStack, languages from requiredLanguages, posted_at from created_at)
- `remote_rocketship_maps_salary_range_when_present` (salary_min/max/currency from salaryRange)
- `remote_rocketship_produced_rawjobs_normalize_into_valid_jobdata`
- `remote_rocketship_raises_when_next_data_is_missing`
- `remote_rocketship_respects_page_cap`

Registry and end-to-end (`tests/jobs/connectors/test_registry.py`, `tests/jobs/test_service.py`):

- `default_connectors_registers_mock_remotive_and_remote_rocketship`
- `discovery_run_persists_jobs_from_remotive_connector` (RemotiveConnector with a mock transport
  wired into `DiscoveryService`; `active_sources = ["remotive"]`; run reports created >= 1)

## Reproducibility

- Verify on the `feat/phase-2-source-connectors` branch at the PR head.
- Versions: Python 3.12, `httpx2` 2.5.0; gates pinned in `backend/pyproject.toml` (ruff 0.15.20,
  pyright strict, pytest 8.3+).
- Install and full gate, run from `backend/`:
  - `uv sync`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run pyright`
  - `uv run pytest`
- Tests are hermetic: connectors are driven by `httpx2.MockTransport` over fixtures derived from
  real responses captured on 2026-06-30; no network access is required.
- Optional live smoke (hits the network through the agent proxy), documented, not part of CI:
  fetch each source once via its connector and print the count.

## Risks and Assumptions

- Assumption: Remotive `/api/remote-jobs` returns `jobs[]` with
  `id, title, company_name, url, job_type, publication_date, candidate_required_location, salary,
  tags, description` — verified live on 2026-06-30. Remotive's response includes an attribution
  notice; source attribution is retained via the `source` field and the stored `raw` payload.
- Assumption: Remote Rocketship is a Next.js Pages Router app embedding
  `props.pageProps.initialJobOpenings` in `__NEXT_DATA__` — verified live on 2026-06-30. A move
  to client-side rendering or app-router streaming would break extraction; the connector then
  raises and the run degrades gracefully (that source reports an error, others continue).
- Assumption: all Remotive jobs are remote (`work_mode = "remote"`); Remote Rocketship work mode
  comes from `locationType`. Unrecognised enum values map to `None` and are tolerated downstream.
- Risk: scraping Remote Rocketship is ToS-gray. Mitigated by personal, low-volume use, an
  identifiable User-Agent, per-host rate limiting, robots.txt treated as advisory, and no
  evasion — consistent with ADR 0008.
- Risk: outbound network may be blocked by the environment's policy; this affects only the
  optional live smoke, never the hermetic test suite.
