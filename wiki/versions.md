# PostgreSQL Versions

This page indexes the PostgreSQL versions covered by the wiki.

## Supported Versions

| Version | Status | Wiki Home | Branch | Pinned Commit | Coverage |
|---|---|---|---|---|---|
| 18 | primary | [[v18/index]] | `REL_18_STABLE` | `6cb307251c5c6261286c1566496920976640108e` | Query lifecycle spine, first code paths, and foundational concepts for planning/executor structures. |
| 12 | legacy | [[v12/index]] | `REL_12_STABLE` | `45b88269a353ad93744772791feb6d01bc7e1e42` | Initial scaffold for version 12.2. |

## Archived Versions

| Version | Removed On | Reason |
|---|---|---|

No PostgreSQL versions have been archived yet.

## Status Meanings

- `primary` - exactly one supported version; default target for new ingests, traces, and answers.
- `active` - kept close to the primary through active-version verification.
- `legacy` - preserved for reference and questions, but not checked by default.
- `archived` - removed from active maintenance and kept under `wiki/_archive/`.

## Source Pin Rules

- Pins must be exact commit hashes, not floating branch names.
- Source checkouts must live under `raw/postgres-NN/`.
- Version landing pages must live under `wiki/vNN/index.md`.
- Generated indexes for a source checkout must live under `.wiki-runtime/indexes/`.

## Current Primary

- PostgreSQL 18
- Source path: `raw/postgres-18/`
- Branch: `REL_18_STABLE`
- Pinned commit: `6cb307251c5c6261286c1566496920976640108e`
