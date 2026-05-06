# PostgreSQL Engine Wiki Overview

This wiki is an LLM-maintained knowledge base for PostgreSQL engine internals.

It is source-backed: durable claims should cite PostgreSQL source files, functions, structs, documentation, commits, or saved design discussions. The wiki should preserve uncertainty under `Open Questions` instead of inventing intent.

## Current Status

Phase 7 project-context packs are generated for every supported PostgreSQL version, including compiler databases, include dependency extracts, and focused callgraphs.

PostgreSQL 18 is the current primary version. Use [[versions]] as the main version index, then enter the PG 18 wiki through [[v18/index]].

## Architecture Map

The first useful spine of the wiki will follow the query lifecycle:

1. [[v18/subsystems/parser]]
2. [[v18/subsystems/analyzer]]
3. [[v18/subsystems/rewriter]]
4. [[v18/subsystems/planner]]
5. [[v18/subsystems/executor]]

## Source Checkouts

- PostgreSQL 18: `raw/postgres-18/`, branch `REL_18_STABLE`, pinned commit `6cb307251c5c6261286c1566496920976640108e`; context pack `.wiki-runtime/context/postgres-18/`.
- PostgreSQL 12: `raw/postgres-12/`, branch `REL_12_STABLE`, pinned commit `45b88269a353ad93744772791feb6d01bc7e1e42`; context pack `.wiki-runtime/context/postgres-12/`.

## Maintenance Tooling

- `scripts/recent_log` - recent entries from `wiki/log.md`.
- `scripts/wiki_lint` - broken links, metadata drift, source-reference checks, and orphan warnings.
- `scripts/source_lookup` - source search and file lookup inside `raw/postgres-NN/`.
- `scripts/source_context` - generated source tree, build configuration, dependency, and graph-orientation packs under `.wiki-runtime/context/postgres-NN/`.
- `scripts/version_diff` - path diff across two project-local source checkouts.
- `scripts/hermes_sessions` - list and clear project-local Hermes session files and database rows.

## Operating Principles

- Trace source code before summarizing behavior.
- Prefer narrow, source-backed subsystem and question pages over broad unsourced summaries.
- Keep version-local content under `wiki/vNN/`.
- Keep runtime dependencies and generated state under `.wiki-runtime/`.
