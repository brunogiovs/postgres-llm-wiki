---
type: concept
scope: shared
verified_against:
  18: 6cb307251c5c6261286c1566496920976640108e
primary_example_version: 18
---

# QueryDesc

## Definition

`QueryDesc` is the executor descriptor for one planned statement execution.

## Why It Exists

The top-level executor API needs a single object that carries input planning data, snapshots, parameters, destination receiver, query environment, and instrumentation options. During `ExecutorStart`, PostgreSQL attaches executor outputs to the same object: result tuple descriptor, query-wide [[shared/concepts/executor-state|EState]], and root [[shared/concepts/plan-and-planstate|PlanState]].

## Where It Appears

- [[v18/subsystems/executor]] starts execution from `ExecutorStart(QueryDesc *queryDesc, ...)`.
- [[v18/code-paths/simple-select-query]] creates a `QueryDesc` inside `PortalStart`.
- [[v18/code-paths/insert-path]], [[v18/code-paths/update-path]], and [[v18/code-paths/delete-path]] create a `QueryDesc` in `ProcessQuery`.
- [[shared/concepts/portal|Portal]] keeps the active `QueryDesc` while executor state is active.

## Related Structures and Functions

- `QueryDesc` in `src/include/executor/execdesc.h`
- `CreateQueryDesc`
- `FreeQueryDesc`
- `ExecutorStart`
- `ExecutorRun`
- `ExecutorFinish`
- `ExecutorEnd`
- `ProcessQuery`
- `PortalStart`

## Interactions With Other Concepts

- `QueryDesc.plannedstmt` points at the [[shared/concepts/planned-statement|PlannedStmt]] being run.
- `QueryDesc.estate` points at [[shared/concepts/executor-state|EState]] after startup.
- `QueryDesc.planstate` points at the root runtime [[shared/concepts/plan-and-planstate|PlanState]].
- Destination receivers consume rows produced as [[shared/concepts/tuple-table-slot|TupleTableSlot]] values flow through execution.

## Version Notes

Verified against PostgreSQL 18 at commit `6cb307251c5c6261286c1566496920976640108e`.

## Source References

- `raw/postgres-18/src/include/executor/execdesc.h:QueryDesc`
- `raw/postgres-18/src/backend/tcop/pquery.c:CreateQueryDesc`
- `raw/postgres-18/src/backend/tcop/pquery.c:ProcessQuery`
- `raw/postgres-18/src/backend/tcop/pquery.c:PortalStart`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorStart`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorRun`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorEnd`

## Open Questions

- Should destination receivers be promoted into a dedicated concept page?
- Where should instrumentation and `EXPLAIN ANALYZE` fields be documented?
