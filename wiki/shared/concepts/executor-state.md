---
type: concept
scope: shared
verified_against:
  18: 6cb307251c5c6261286c1566496920976640108e
primary_example_version: 18
---

# Executor State

## Definition

`EState` is the query-wide working state for one executor invocation.

## Why It Exists

Execution needs state that is shared by the whole plan tree: snapshots, range table data, relation arrays, result relation metadata, parameter values, tuple slots, expression contexts, subplan states, instrumentation flags, and counts of processed rows. Rather than duplicate that state in every node, each [[shared/concepts/plan-and-planstate|PlanState]] points to one `EState`.

## Where It Appears

- [[v18/subsystems/executor]] builds `EState` in `standard_ExecutorStart`.
- [[v18/code-paths/simple-select-query]] increments `es_processed` for selected rows.
- [[v18/code-paths/insert-path]], [[v18/code-paths/update-path]], and [[v18/code-paths/delete-path]] use result relation metadata through executor state.

## Related Structures and Functions

- `EState` in `src/include/nodes/execnodes.h`
- `CreateExecutorState`
- `standard_ExecutorStart`
- `ExecutorRun`
- `ExecutePlan`
- `FreeExecutorState`
- `ResultRelInfo`

## Interactions With Other Concepts

- [[shared/concepts/querydesc|QueryDesc]] receives `estate` when `ExecutorStart` initializes execution.
- [[shared/concepts/plan-and-planstate|PlanState]] nodes point to the shared `EState`.
- `EState.es_tupleTable` tracks [[shared/concepts/tuple-table-slot|TupleTableSlot]] objects.
- DML execution uses `EState.es_result_relations` and related fields for [[shared/concepts/modifytable|ModifyTable]].

## Version Notes

Verified against PostgreSQL 18 at commit `6cb307251c5c6261286c1566496920976640108e`.

## Source References

- `raw/postgres-18/src/include/nodes/execnodes.h:EState`
- `raw/postgres-18/src/backend/executor/execMain.c:standard_ExecutorStart`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorRun`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutePlan`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorEnd`

## Open Questions

- Which `EState` fields should get dedicated pages first: snapshots, result relations, tuple table, or expression contexts?
- How much of memory context ownership belongs here versus in a memory-context concept page?
