# PostgreSQL Engine Wiki Implementation Steps

This directory breaks the implementation roadmap from `postgresql-engine-wiki-plan.md` into one actionable markdown file per phase.

Use these files as the execution checklist when building the PostgreSQL engine LLM wiki.

## Steps

1. [Phase 1 Done: Wiki Scaffold](phase-1-done-wiki-scaffold.md)
2. [Phase 2 Done: Bootstrap Supported Versions](phase-2-done-bootstrap-supported-versions.md)
3. [Phase 3 Done: Query Lifecycle Spine](phase-3-done-query-lifecycle-spine.md)
4. [Phase 4 Done: First Code Paths](phase-4-done-first-code-paths.md)
5. [Phase 5 Done: Backfill Concepts](phase-5-done-backfill-concepts.md)
6. [Phase 6 Done: Maintenance Tooling](phase-6-done-maintenance-tooling.md)

## Completion Convention

When a phase is implemented, rename its file from:

```text
phase-N-name.md
```

to:

```text
phase-N-done-name.md
```

Also update this index and add a `## Status` section to the completed phase file.

## Execution Rules

- Keep `wiki/versions.md` as the main version index.
- Keep each `wiki/vNN/index.md` as the version-local table of contents.
- Run all wiki tooling from the project root.
- Store all wiki-specific dependencies, caches, model/runtime state, indexes, logs, and temporary files inside this project directory.
- Make source-backed pages only after checking the pinned PostgreSQL source.
- Prefer narrow, verifiable source traces over broad unsourced summaries.
- Update `wiki/index.md`, `wiki/log.md`, and the relevant version landing page after every meaningful wiki change.
- On a 16GB NVIDIA GPU, keep local agent tasks small and source-grounded.
