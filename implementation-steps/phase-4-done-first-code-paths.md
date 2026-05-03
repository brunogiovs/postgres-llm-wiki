# Phase 4 Done: First Code Paths

## Status

Done on 2026-04-30.

## Goal

Trace the first end-to-end PostgreSQL engine operations through the source tree. Code-path pages are the highest-value artifacts in the wiki.

## Target Code Paths

1. Simple `SELECT`
2. `INSERT`
3. `UPDATE`
4. `DELETE`

## Inputs

- Query lifecycle subsystem pages from Phase 3
- Primary PostgreSQL source checkout
- `templates/code-path.md`
- `wiki/versions.md`
- Primary `wiki/vNN/index.md`

## Tasks Per Code Path

1. Read `wiki/versions.md` and identify the target version.
2. Read the target version landing page.
3. Search the source for likely entry points.
4. Follow calls through parser, analyzer, rewriter, planner, and executor where applicable.
5. Record the flow under `wiki/vNN/code-paths/<path-name>.md`.
6. Link to subsystem pages and concept pages.
7. Cite every source-backed claim.
8. Mark uncertain or skipped behavior under Open Questions.
9. Update affected subsystem pages with a link to the new code path.
10. Update `wiki/vNN/index.md`.
11. Update `wiki/index.md`.
12. Append a trace entry to `wiki/log.md`.

## Local Model Guidance

For local agent on a 16GB GPU:

- Trace only one operation at a time.
- Keep each pass narrow, such as "find the executor entry points for simple SELECT."
- Summarize verified findings into the code-path page before continuing.
- Stop and record Open Questions when the call chain becomes uncertain.
- Do not let the model fill gaps from memory.

Keep all runtime state project-local:

- Read source from `raw/postgres-NN/`.
- Use generated indexes from `.wiki-runtime/indexes/` only.
- Store temporary call-chain notes under `.wiki-runtime/tmp/` unless they become durable wiki pages.
- Store model logs under `.wiki-runtime/logs/`.

## Required Code Path Page Sections

```md
# Code Path Name

## Scope

## High-Level Flow

## Detailed Flow

| Step | Function | File | Notes |
|---|---|---|---|

## Key Data Structures

## Cross-Links

## Source References

## Open Questions
```

## Active-Version Checks

If active versions exist:

- Walk the same call chain in the active version's source checkout.
- Create a separate `wiki/vNN/code-paths/...` page only after checking that version.
- If the check is deferred, record it on that version's landing page.

## Definition Of Done

- At least one complete code-path page exists for the primary version.
- The first useful milestone prefers all four target code paths.
- Each code-path page cites real files and symbols.
- Relevant subsystem pages link back to the code paths.
- Open Questions are explicit where the trace is incomplete.
