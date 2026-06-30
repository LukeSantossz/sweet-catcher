# Job storage model: normalized relational columns with a raw JSONB payload

Phase 2 discovery introduces the Job entity. Unlike the master profile and the search
criteria — which are read and written as a whole — jobs must be filtered, deduplicated, and
aggregated in SQL (FR #8 deduplication, FR #25 filters, FR #26 market analytics). We need a
storage model for the first query-heavy domain.

## Status

Accepted.

## Considered Options

- **Normalized relational columns plus a `raw` JSONB payload (chosen):** the queryable and
  dedup fields are first-class columns (title, company, source, source_external_id, url,
  canonical_url, location, work_mode, contract_type, dates, salary, technologies, languages,
  status, description, description_hash), while the original source payload is kept verbatim
  in a `raw` JSONB column. Supports SQL filtering, dedup keys and constraints, and later
  analytics; retaining `raw` allows re-normalization as the schema evolves.
- **Whole-document JSONB snapshot (the profile/criteria model, ADR 0006):** rejected — opaque
  documents make filtering, deduplication, and aggregation awkward; the job access pattern is
  query-heavy, not read-as-whole.
- **Fully normalized with child tables for technologies, languages, and requirements:**
  rejected for now — premature at the domain's debut; list-valued fields can be array or
  JSONB columns until analytics genuinely needs join tables, avoiding many tables and
  migrations up front.

## Consequences

- A `jobs` table carries normalized columns plus a `raw` JSONB column, a unique constraint on
  `(source, source_external_id)`, and indexes on `canonical_url` and `description_hash` to
  back deduplication (FR #8).
- The Job stores only connector- and normalization-derived fields. Analysis-derived fields
  (inferred seniority, extracted requirements — FR #9/#10) are added later as nullable
  columns or a related table, without reshaping existing data destructively.
- Schema evolution as the first real connector lands is additive (new nullable columns); the
  retained `raw` payload allows re-normalizing historical rows if a mapping changes.
- This intentionally diverges from the profile/criteria JSONB-snapshot model (ADR 0006); the
  two patterns coexist, chosen per access pattern — read-as-whole versus query-heavy.
