# Phase 3 Done: Query Lifecycle Spine

## Status

Done on 2026-04-30.

## Goal

Build the first subsystem pages around PostgreSQL's query lifecycle. These pages create the navigational spine for later code-path traces.

## Target Subsystems

1. Parser
2. Analyzer
3. Rewriter
4. Planner
5. Executor

## Inputs

- `wiki/versions.md`
- Primary version landing page, such as `wiki/v17/index.md`
- Pinned PostgreSQL source checkout, such as `raw/postgres-17/`
- Page templates from `templates/`

## Tasks Per Subsystem

1. Read `wiki/versions.md` and identify the primary version.
2. Read `wiki/vNN/index.md` to understand current coverage.
3. Search the relevant PostgreSQL source area with `rg` or `git grep`.
4. Identify the subsystem's major source files, headers, entry points, and core structs.
5. Create or update `wiki/vNN/subsystems/<subsystem>.md`.
6. Add source references for every behavioral claim.
7. Add cross-links to known concepts and future code paths.
8. Add Open Questions for uncertain behavior.
9. Update `wiki/vNN/index.md`.
10. Update `wiki/index.md`.
11. Append an ingest entry to `wiki/log.md`.

## Local Model Guidance

On the 16GB GPU setup, do not ask the model to ingest an entire subsystem directory in one pass. Slice the work:

- one key source file at a time
- one entry point at a time
- one subsystem page section at a time

Use the wiki page itself as accumulated working memory.

Use only project-local source and indexes:

- Source must come from `raw/postgres-NN/`.
- Generated symbol/search indexes must come from `.wiki-runtime/indexes/`.
- Temporary notes or extracted snippets should go under `.wiki-runtime/tmp/` if they are not durable wiki content.
- Do not depend on global ctags, global search indexes, or source checkouts outside this project.

## Suggested Source Search Starting Points

These are starting points, not claims. Verify against the pinned source.

```bash
rg "raw_parser|parse_analyze|QueryRewrite|planner|ExecutorStart|ExecutorRun" raw/postgres-NN/src
git -C raw/postgres-NN grep "ExecutorRun"
git -C raw/postgres-NN grep "standard_planner"
```

## Required Subsystem Page Sections

```md
# Subsystem Name

## Role

## Major Entry Points

## Core Data Structures

## Related Concepts

## Important Code Paths

## Differences Across Supported Versions

## Source References

## Open Questions
```

## Definition Of Done

- The primary version has subsystem pages for parser, analyzer, rewriter, planner, and executor.
- Each subsystem page cites source paths and symbols.
- `wiki/vNN/index.md` links to each subsystem page.
- `wiki/index.md` lists each subsystem page.
- `wiki/log.md` records each subsystem ingest.
