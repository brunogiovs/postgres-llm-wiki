---
type: concept
scope: shared
verified_against:
  18: 6cb307251c5c6261286c1566496920976640108e
primary_example_version: 18
---

# Portal

## Definition

A `Portal` is PostgreSQL's execution wrapper for one query or a list of planned statements. It tracks the statement list, execution strategy, active executor descriptor, snapshots, destination details, cursor position, and held cursor storage.

## Why It Exists

The traffic controller layer needs a durable object that can define, start, run, suspend, resume, and clean up execution. Portals serve both simple query execution and cursor-like behavior. In the simple protocol, `exec_simple_query` creates an unnamed portal, defines planned statements on it, starts it, and runs it.

## Where It Appears

- [[v18/code-paths/simple-select-query]] uses `PORTAL_ONE_SELECT` for a single plain `SELECT`.
- [[v18/code-paths/insert-path]], [[v18/code-paths/update-path]], and [[v18/code-paths/delete-path]] use `PORTAL_MULTI_QUERY` when there is no `RETURNING`.
- [[v18/subsystems/executor]] is invoked from portal execution through [[shared/concepts/querydesc|QueryDesc]].

## Related Structures and Functions

- `PortalData` in `src/include/utils/portal.h`
- `PortalDefineQuery`
- `ChoosePortalStrategy`
- `PortalStart`
- `PortalRun`
- `PortalRunSelect`
- `PortalRunMulti`
- `ProcessQuery`

## Interactions With Other Concepts

- `PortalData.stmts` holds [[shared/concepts/planned-statement|PlannedStmt]] nodes.
- `PortalData.queryDesc` points to the active [[shared/concepts/querydesc|QueryDesc]] when the executor is running.
- Portal strategy determines whether a statement runs as one select, one returning statement, a utility select, or a multi-query execution path.
- Portal snapshots interact with executor snapshots stored in [[shared/concepts/executor-state|EState]].

## Version Notes

Verified against PostgreSQL 18 at commit `6cb307251c5c6261286c1566496920976640108e`.

## Source References

- `raw/postgres-18/src/include/utils/portal.h:PortalData`
- `raw/postgres-18/src/backend/tcop/postgres.c:exec_simple_query`
- `raw/postgres-18/src/backend/tcop/pquery.c:ChoosePortalStrategy`
- `raw/postgres-18/src/backend/tcop/pquery.c:PortalStart`
- `raw/postgres-18/src/backend/tcop/pquery.c:PortalRun`
- `raw/postgres-18/src/backend/tcop/pquery.c:PortalRunSelect`
- `raw/postgres-18/src/backend/tcop/pquery.c:PortalRunMulti`
- `raw/postgres-18/src/backend/tcop/pquery.c:ProcessQuery`

## Open Questions

- Which extended-query protocol paths should link to the same portal concept?
- Should holdable cursor storage be split into a cursor-specific concept page?
