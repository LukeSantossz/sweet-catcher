# Master-profile versioning: immutable JSONB snapshots with a monotonic version number

FR #1 requires recording every relevant change to the master profile as a new version;
FR #30 (audit) and FR #17 (diff) rely on a discrete "profile version". The profile is
written and read as a whole. We need a versioning and storage model for this first domain.

## Status

Accepted.

## Considered Options

- **Immutable JSONB snapshots with a monotonic version number (chosen)**: each save inserts
  a new `master_profile_version` row holding the full, Pydantic-validated profile as a
  JSONB document, numbered v1, v2, and so on; the current profile is the highest-numbered
  version. Rollback and diff are trivial, the version number is the audit's "profile
  version", and the schema is two tables.
- **Current state plus a per-field audit log**: rejected — reconstructing a full historical
  version and assigning a discrete version number is awkward.
- **Normalized relational tables per section, versioned by copying rows**: rejected — 9+
  tables and many migrations at the persistence debut, and snapshotting duplicates every
  row on each edit; the relational power stays unused until later phases.
- **Hybrid (normalized current plus JSONB history)**: rejected — redundant data kept in
  sync without a present need.

## Consequences

- Two tables: `master_profile` and `master_profile_version` (UUID primary keys,
  `version_number`, `created_at`, `note`, `data` JSONB, unique `(profile_id,
  version_number)`).
- The profile structure (the eight PRD sections plus a curated `key_achievements` list)
  lives in Pydantic v2 DTOs; strong typing is enforced at the boundary, not in the database
  schema.
- An identical save is deduped: no new version is created when the data equals the latest.
- The profile shape can evolve without database migrations (permissive input, snapshot
  storage); a field rename or removal needs a data-migration consideration for old
  snapshots.
- Per-section SQL querying is not available now; it is a later-phase concern served by
  JSONB operators or derived projections.
