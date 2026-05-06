# PostgreSQL Engine Wiki Overview

This wiki is an LLM-maintained knowledge base for PostgreSQL engine internals.

It is source-backed: durable claims should cite PostgreSQL source files, functions, structs, documentation, commits, or saved design discussions. The wiki should preserve uncertainty under `Open Questions` instead of inventing intent.

## Current Status

Phase 7 project-context packs are generated for every supported PostgreSQL version, including compiler databases, include dependency extracts, and focused callgraphs.

PostgreSQL 18 is the current primary version. Use [[versions]] as the main version index, then enter the PG 18 wiki through [[v18/index]].

## Source Navigation

Use the generated PostgreSQL 18 source-context pack for source orientation and call-path discovery. Source-tool invocations must still name their version explicitly, such as `--version 18`, even when PostgreSQL 18 is the current primary version:

- `.wiki-runtime/context/postgres-18/tree-L4.txt`
- `.wiki-runtime/context/postgres-18/compile_commands.json`
- `.wiki-runtime/context/postgres-18/include-deps.txt`
- `.wiki-runtime/context/postgres-18/callgraphs/`

Behavioral claims still need citations to matching raw source files or symbols under `raw/postgres-18/`.

## Source Checkouts

- PostgreSQL 18: `raw/postgres-18/`, branch `REL_18_STABLE`, pinned commit `6cb307251c5c6261286c1566496920976640108e`; context pack `.wiki-runtime/context/postgres-18/`.
- PostgreSQL 12: `raw/postgres-12/`, branch `REL_12_STABLE`, pinned commit `45b88269a353ad93744772791feb6d01bc7e1e42`; context pack `.wiki-runtime/context/postgres-12/`.

## Maintenance Tooling

- `scripts/recent_log` - recent entries from `wiki/log.md`.
- `scripts/wiki_lint` - broken links, metadata drift, source-reference checks, and orphan warnings.
- `scripts/source_lookup` - source search and file lookup inside `raw/postgres-NN/`; requires `--version NN`.
- `scripts/source_context` - generated source tree, build configuration, dependency, and graph-orientation packs under `.wiki-runtime/context/postgres-NN/`; requires `--version NN` or explicit `--all`.
- `scripts/version_diff` - path diff across two project-local source checkouts.
- `scripts/hermes_sessions` - list and clear project-local Hermes session files and database rows.

## Operating Principles

- Trace source code before summarizing behavior.
- Use generated source-context packs for source navigation and call-path discovery; extend or regenerate them instead of creating standalone call-chain page families.
- Prefer narrow, source-backed question pages over broad unsourced summaries.
- Keep version-local content under `wiki/vNN/`.
- Keep runtime dependencies and generated state under `.wiki-runtime/`.
