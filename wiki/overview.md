# PostgreSQL Engine Wiki Overview

This wiki is an LLM-maintained knowledge base for PostgreSQL engine internals.

It is source-backed: durable claims should cite PostgreSQL source files, functions, structs, documentation, commits, or saved design discussions. The wiki should preserve uncertainty under `Open Questions` instead of inventing intent.

## Current Status

Phase 6 maintenance tooling is initialized for the PostgreSQL engine wiki.

PostgreSQL 18 is the current primary version. Use [[versions]] as the main version index, then enter the PG 18 wiki through [[v18/index]].

## Architecture Map

The first useful spine of the wiki will follow the query lifecycle:

1. [[v18/subsystems/parser]]
2. [[v18/subsystems/analyzer]]
3. [[v18/subsystems/rewriter]]
4. [[v18/subsystems/planner]]
5. [[v18/subsystems/executor]]

The first code-path pages should trace:

1. [[v18/code-paths/simple-select-query]]
2. [[v18/code-paths/insert-path]]
3. [[v18/code-paths/update-path]]
4. [[v18/code-paths/delete-path]]

The first shared concept layer covers:

1. [[shared/concepts/query-tree]]
2. [[shared/concepts/planned-statement]]
3. [[shared/concepts/plan-and-planstate]]
4. [[shared/concepts/path-and-reloptinfo]]
5. [[shared/concepts/executor-state]]
6. [[shared/concepts/tuple-table-slot]]
7. [[shared/concepts/modifytable]]
8. [[shared/concepts/portal]]
9. [[shared/concepts/querydesc]]

## Source Checkouts

- PostgreSQL 18: `raw/postgres-18/`, branch `REL_18_STABLE`, pinned commit `6cb307251c5c6261286c1566496920976640108e`.

## Maintenance Tooling

- `scripts/wiki_agent` - start, stop, status, and logs for the maintainer agent process. See [[operations/agent]].
- `scripts/recent_log` - recent entries from `wiki/log.md`.
- `scripts/wiki_lint` - broken links, metadata drift, source-reference checks, and orphan warnings.
- `scripts/source_lookup` - source search and file lookup inside `raw/postgres-NN/`.
- `scripts/version_diff` - path diff across two project-local source checkouts.
- `scripts/hermes_sessions` - list and clear project-local Hermes session files and database rows.

## Operating Principles

- Trace source code before summarizing behavior.
- Prefer code-path pages over vague subsystem summaries.
- Keep version-local content under `wiki/vNN/`.
- Keep shared theory under `wiki/shared/concepts/`.
- Keep runtime dependencies and generated state under `.wiki-runtime/`.
