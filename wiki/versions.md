# PostgreSQL Versions

This page indexes the PostgreSQL versions covered by the wiki.

## Supported Versions

| Version | Status | Wiki Home | Branch | Pinned Commit | Coverage |
|---|---|---|---|---|---|
| 18 | primary | [[v18/index]] | `REL_18_STABLE` | `6cb307251c5c6261286c1566496920976640108e` | Generated project-context pack with compiler database, include dependencies, and focused query-lifecycle callgraphs. |
| 12 | legacy | [[v12/index]] | `REL_12_STABLE` | `45b88269a353ad93744772791feb6d01bc7e1e42` | Generated project-context pack with compiler database including appended contrib build capture, include dependencies, and focused callgraphs; one filed (unverified) Azure disk configuration question covering planner cost settings, `effective_io_concurrency`, checkpoints/WAL, bgwriter/writeback, temp spill placement, durability settings, rollout scope, and production-safe inventory queries; one filed (unverified) bgwriter tuning question covering the four bgwriter GUCs, `pg_stat_bgwriter` counter wiring, and practical backend-write-share threshold bands; one filed (unverified) checkpoint monitoring and optimization question covering `pg_stat_bgwriter`, `log_checkpoints`, a `pg_settings` checkpoint-configuration inventory query, checkpoint/WAL GUCs, and deployment scenarios; one agent-reviewed query-lifecycle disk-I/O review with exact `track_io_timing` scope boundaries; one agent-reviewed production `track_io_timing` enablement procedure; one agent-reviewed traditional-inheritance no-pruning overhead matrix; one agent-reviewed separate-WAL-disk question covering full `pg_wal` filesystem PANIC behavior, replication-slot WAL retention, and corruption-risk boundaries. |

## Archived Versions

| Version | Removed On | Reason |
|---|---|---|

No PostgreSQL versions have been archived yet.

## Status Meanings

- `primary` - exactly one supported version; default target for new ingests and answers.
- `active` - kept close to the primary through active-version verification.
- `legacy` - preserved for reference and questions, but not checked by default.
- `archived` - removed from active maintenance and kept under `wiki/_archive/`.

## Source Pin Rules

- Pins must be exact commit hashes, not floating branch names.
- Source checkouts must live under `raw/postgres-NN/`.
- Version landing pages must live under `wiki/vNN/index.md`.
- Generated runtime artifacts must live under `.wiki-runtime/`: search and symbol indexes under `.wiki-runtime/indexes/`, project-context packs under `.wiki-runtime/context/postgres-NN/`, and build trees under `.wiki-runtime/build/postgres-NN/`.

## Current Primary

- PostgreSQL 18
- Source path: `raw/postgres-18/`
- Branch: `REL_18_STABLE`
- Pinned commit: `6cb307251c5c6261286c1566496920976640108e`
