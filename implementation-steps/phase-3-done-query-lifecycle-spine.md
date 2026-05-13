# Phase 3 Done: Query Lifecycle Spine

## Status

Done on 2026-05-06. The original subsystem-page spine was retired.

## Goal

Keep query-lifecycle entry points easy to trace from the pinned raw checkout without creating standalone source-trace documents.

Behavioral claims still require direct citations into the matching `raw/postgres-NN/` checkout.

## Target Source Areas

1. Parser
2. Analyzer
3. Rewriter
4. Planner
5. Executor

## Inputs

- `wiki/versions.md`
- Primary version landing page, such as `wiki/v18/index.md`
- Pinned PostgreSQL source checkout, such as `raw/postgres-18/`

## Tasks Per Source Area

1. Read `wiki/versions.md` and identify the target version.
2. Read `wiki/vNN/index.md` to confirm the source pin.
3. Search the matching PostgreSQL source area under `raw/postgres-NN/` with `rg` or `git grep` before making claims.
4. Inspect adjacent callers, callees, structs, macros, includes, tests, docs, catalogs, grammar, error paths, GUC definitions, and extension boundaries as needed.
5. File durable findings only as version-local pages when the user asks for an answer worth preserving.
6. Update `wiki/vNN/index.md`, `wiki/index.md`, and `wiki/versions.md` only when coverage changes.
7. Append a maintenance entry to `wiki/log.md`.

## Local Model Guidance

On the 16GB GPU setup, do not ask the model to ingest an entire source area in one pass. Slice the work:

- one generated context artifact at a time
- one key source file at a time
- one entry point at a time
- one filed answer at a time

Use only project-local source:

- Source must come from `raw/postgres-NN/`.
- Generated symbol/search indexes, if used, must come from `.wiki-runtime/indexes/`.
- Temporary notes or extracted snippets should go under `.wiki-runtime/tmp/` if they are not durable wiki content.
- Do not depend on global ctags, global search indexes, or source checkouts outside this project.

## Suggested Source Search Starting Points

These are starting points, not claims. Verify against the pinned source.

```bash
rg "raw_parser|parse_analyze|QueryRewrite|planner|ExecutorStart|ExecutorRun" raw/postgres-NN/src
git -C raw/postgres-NN grep "ExecutorRun"
git -C raw/postgres-NN grep "standard_planner"
```

## Trace Requirements

For query-lifecycle traces, inspect source around roots such as `PostgresMain`, `exec_simple_query`, `standard_planner`, and `ExecutorRun`.

Do not create standalone code-path or source-trace pages.

## Definition Of Done

- Query-lifecycle source orientation is available through pinned raw source citations rather than subsystem or code-path pages.
- Durable answers are filed as version-local pages only when needed.
- `wiki/log.md` records maintenance.
- `scripts/wiki_lint` runs after any wiki-facing edits.
