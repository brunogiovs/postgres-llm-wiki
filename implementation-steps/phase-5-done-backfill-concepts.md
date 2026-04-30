# Phase 5 Done: Backfill Concepts

## Status

Done on 2026-04-30.

## Goal

Create durable concept pages for recurring PostgreSQL engine ideas that surfaced during subsystem sweeps and code-path traces.

## Timing

Do this after Phases 3 and 4 have produced enough links and notes to show which concepts genuinely recur.

## Inputs

- Existing subsystem pages
- Existing code-path pages
- `wiki/index.md`
- `wiki/vNN/index.md`
- Pinned PostgreSQL source checkout
- `templates/concept-shared.md`
- `templates/concept-version.md`

## Candidate Concepts

Create these only when source-backed references justify them:

- Memory contexts
- Resource owners
- Snapshots
- MVCC
- Tuple visibility
- Transaction IDs
- Locks
- Latches
- Buffer manager basics
- WAL basics
- Plan nodes
- Executor state
- Relcache
- Catcache
- Syscache

## Shared vs Version-Specific Concepts

Use `wiki/shared/concepts/` when the page explains stable theory or vocabulary across versions.

Use `wiki/vNN/concepts/` when the concept page names version-specific behavior, functions, files, signatures, or code flow.

## Tasks Per Concept

1. Identify repeated mentions or links across existing pages.
2. Search the pinned source and docs for supporting evidence.
3. Decide whether the concept belongs in `wiki/shared/concepts/` or `wiki/vNN/concepts/`.
4. Create or update the concept page.
5. Add source examples and version evidence.
6. Replace unlinked repeated mentions with Obsidian-style links.
7. Update related subsystem and code-path pages.
8. Update `wiki/vNN/index.md` if version-local coverage changed.
9. Update `wiki/index.md`.
10. Append a concept entry to `wiki/log.md`.

## Project-Local Dependency Rules

- Use source from `raw/postgres-NN/`.
- Use generated indexes from `.wiki-runtime/indexes/`.
- Put temporary concept clustering notes under `.wiki-runtime/tmp/` unless they become durable wiki pages.
- Do not rely on external notes, global source checkouts, or global model caches as hidden dependencies.

## Required Shared Concept Front Matter

```yaml
---
type: concept
scope: shared
verified_against:
  NN: COMMIT_HASH
primary_example_version: NN
---
```

## Required Version Concept Front Matter

```yaml
---
type: concept
version: NN
pinned_commit: COMMIT_HASH
verified: true
---
```

## Definition Of Done

- At least five foundational concept pages exist.
- Recurring concepts are linked from subsystem and code-path pages.
- Shared concept pages include `verified_against:`.
- Version-specific concept pages live under `wiki/vNN/concepts/`.
- Open Questions capture uncertainty instead of smoothing over it.
