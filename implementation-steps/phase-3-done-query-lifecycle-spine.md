# Phase 3 Done: Query Lifecycle Source Context

## Status

Done on 2026-05-06. The original subsystem-page spine was retired. Query-lifecycle source navigation now lives in generated context packs under `.wiki-runtime/context/postgres-NN/`.

## Goal

Seed the generated source-context packs with query-lifecycle entry points so agents can orient on parse, analyze, rewrite, plan, and execute paths without creating standalone source-trace documents.

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
- Generated source-context pack under `.wiki-runtime/context/postgres-NN/`
- `scripts/source_context`

## Tasks Per Source Area

1. Read `wiki/versions.md` and identify the target version.
2. Read `wiki/vNN/index.md` to confirm source pin and context-pack status.
3. Read `.wiki-runtime/context/postgres-NN/manifest.md` and relevant context artifacts.
4. Use `tree-L4.txt`, `compile_commands.json`, `include-deps.txt`, and `callgraphs/` to orient on source files, headers, compile context, and likely call edges.
5. Search the matching PostgreSQL source area under `raw/postgres-NN/` with `rg` or `git grep` before making claims.
6. If the generated context is stale or missing a needed source root, regenerate or extend `.wiki-runtime/context/postgres-NN/` with `scripts/source_context`.
7. File durable findings only as question pages when the user asks for an answer worth preserving.
8. Update `wiki/vNN/index.md`, `wiki/index.md`, and `wiki/versions.md` only when coverage or context-pack status changes.
9. Append a context or maintenance entry to `wiki/log.md`.

## Local Model Guidance

On the 16GB GPU setup, do not ask the model to ingest an entire source area in one pass. Slice the work:

- one generated context artifact at a time
- one key source file at a time
- one entry point at a time
- one filed question at a time

Use generated context as source navigation, not as behavioral proof.

Use only project-local source and context:

- Source must come from `raw/postgres-NN/`.
- Generated source context must come from `.wiki-runtime/context/postgres-NN/`.
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

## Context-Pack Requirements

The query-lifecycle source context should include, when tool support allows:

- `tree-L4.txt` for source-tree orientation.
- `compile_commands.json` for compilation units, include paths, defines, and generated-header context.
- `include-deps.txt` for direct include relationships.
- focused callgraphs under `callgraphs/` for roots such as `PostgresMain`, `exec_simple_query`, `standard_planner`, and `ExecutorRun`.

Do not create standalone code-path or source-trace pages. If a call-path view is useful, add it to the generated context pack.

## Definition Of Done

- The primary version has a generated `.wiki-runtime/context/postgres-NN/manifest.md`.
- Query-lifecycle source orientation is available through generated context artifacts rather than subsystem or code-path pages.
- Any deferred context artifacts are recorded in the manifest and version landing page.
- Durable answers are filed as question pages only when needed.
- `wiki/log.md` records context generation or maintenance.
- `scripts/wiki_lint` runs after any wiki-facing edits.
