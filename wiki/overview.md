# PostgreSQL Engine Wiki Overview

This wiki is an LLM-maintained knowledge base for PostgreSQL engine internals.

It is source-backed: durable claims should cite PostgreSQL source files, functions, structs, documentation, commits, or saved design discussions. The wiki should preserve uncertainty under `Open Questions` instead of inventing intent.

## Current Status

PostgreSQL 18 is the current primary version. Use [[versions]] as the main version index, then enter the PG 18 wiki through [[v18/index]].

## Source Evidence

Use the matching pinned checkout under `raw/postgres-NN/` for source evidence.

Behavioral claims still need citations to matching raw source files or symbols under `raw/postgres-NN/`.

## Source Checkouts

- PostgreSQL 18: `raw/postgres-18/`, branch `REL_18_STABLE`, pinned commit `6cb307251c5c6261286c1566496920976640108e`.
- PostgreSQL 12: `raw/postgres-12/`, branch `REL_12_STABLE`, pinned commit `45b88269a353ad93744772791feb6d01bc7e1e42`.

## Maintenance Tooling

- `scripts/recent_log` - recent entries from `wiki/log.md`.
- `scripts/wiki_lint` - broken links, metadata drift, source-reference checks, and orphan warnings.

## Operating Principles

- Trace source code before summarizing behavior.
- Use the matching pinned checkout for raw source evidence.
- Prefer narrow, source-backed filed answer pages over broad unsourced summaries.
- Keep version-local content under `wiki/vNN/`.
- Keep runtime dependencies and generated state under `.wiki-runtime/`.
