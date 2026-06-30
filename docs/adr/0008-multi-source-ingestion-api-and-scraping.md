# Multi-source job ingestion: public APIs and polite web scraping behind one connector interface

Phase 2 discovery shipped with only a deterministic `MockConnector`. Real ingestion must pull
from heterogeneous external sources: a few expose JSON APIs, but most job sites do not and
require reading their served HTML. We need one strategy that accommodates both transports
without either leaking into normalization, deduplication, or persistence.

## Status

Accepted.

## Considered Options

- **Public APIs plus polite web scraping behind the `SourceConnector` protocol (chosen):**
  every source — a JSON API (Remotive) or an HTML page (Remote Rocketship now; Seek NZ and
  LinkedIn in later slices) — is a connector implementing `name` and
  `async fetch(criteria) -> list[RawJob]`. A shared polite HTTP client centralises an
  identifiable User-Agent, timeouts, retry with exponential backoff, and a per-host minimum
  interval. Scraping prefers embedded structured data (e.g. the Next.js `__NEXT_DATA__` payload
  or JSON-LD) over brittle DOM selectors. Per-source failures are isolated by the existing
  `DiscoveryService` boundary so one source cannot abort a run.
- **API-only ingestion:** rejected — the sources that matter for this user (Seek NZ, LinkedIn,
  Remote Rocketship) expose no public candidate API, so an API-only strategy cannot reach them.
- **A scraping framework or headless browser (Scrapy, Playwright) per source:** rejected —
  heavyweight and slow; the target listings are present in server-rendered HTML as structured
  JSON, so a thin `httpx2`-based fetch plus standard-library extraction suffices for V1.
- **Aggressive anti-blocking (rotating proxies, CAPTCHA solving, fake accounts):** rejected on
  principle — out of scope and against the project's posture; it is also what exposed scrapers
  such as Proxycurl to legal action.

## Consequences

- Compliance posture is politeness-first and personal-scale: identifiable User-Agent, per-host
  rate limiting, conservative volume, and retry with backoff. No CAPTCHA solving, proxy
  rotation, fake accounts, or anti-detection — ever.
- robots.txt is treated as advisory for personal-use fetches of public listings rather than a
  hard block — a deliberate, recorded choice for a single-user tool, to be revisited if the tool
  ever serves more than its owner.
- Sources whose terms prohibit automated access (Seek, LinkedIn) are best-effort and expected to
  be fragile; a layout or policy change degrades that source to an error in its `SourceResult`
  while other sources continue.
- The original source payload is retained (under `source_raw` inside the stored `raw` JSONB, per
  ADR 0007) so a connector mapping change can re-normalize historical rows.
- New sources are added as connectors behind the same interface, with no change to
  normalization, deduplication, or persistence.
- Source selection stays data-driven via `SearchCriteria.active_sources`; an unknown name is
  reported in the run summary, not fatal.
