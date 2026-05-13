# PostgreSQL Versions

This page indexes the PostgreSQL versions covered by the wiki.

## Supported Versions

| Version | Status | Wiki Home | Branch | Pinned Commit | Coverage |
|---|---|---|---|---|---|
| 18 | primary | [[v18/index]] | `REL_18_STABLE` | `6cb307251c5c6261286c1566496920976640108e` | Graph-first source navigation under `.wiki-runtime/graph/postgres-18/`; behavioral claims cite the matching pinned checkout under `raw/postgres-18/`. |
| 12 | legacy | [[v12/index]] | `REL_12_STABLE` | `45b88269a353ad93744772791feb6d01bc7e1e42` | AST-only Graphify graph generated under `.wiki-runtime/graph/postgres-12/`; filed operational questions cover storage, WAL, bgwriter/checkpoints, inheritance overhead including `force_generic_plan` impact, I/O timing, planning metrics and generic/custom plan visibility, plan-cache mode including generic-plan validation, REINDEX CONCURRENTLY disk-space sizing, btree `avg_leaf_density` estimation, and a query-planner GUC inventory plus a non-default-settings `pg_settings` query covering every `Query Tuning / *` category, pinned to raw PostgreSQL 12 source citations. |

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
- Generated runtime artifacts must live under `.wiki-runtime/`: Graphify source graphs under `.wiki-runtime/graph/postgres-NN/`, caches under `.wiki-runtime/cache/`, and logs under `.wiki-runtime/logs/`.

## Current Primary

- PostgreSQL 18
- Source path: `raw/postgres-18/`
- Branch: `REL_18_STABLE`
- Pinned commit: `6cb307251c5c6261286c1566496920976640108e`
