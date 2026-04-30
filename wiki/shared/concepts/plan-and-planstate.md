---
type: concept
scope: shared
verified_against:
  18: 6cb307251c5c6261286c1566496920976640108e
primary_example_version: 18
---

# Plan and PlanState

## Definition

`Plan` is the planner-produced tree of executor-facing nodes. `PlanState` is the executor's runtime state tree that corresponds to the `Plan` tree.

## Why It Exists

PostgreSQL separates the read-only plan description from runtime state. A `Plan` node records estimated costs, row counts, target lists, quals, and child plan links. During executor startup, `ExecInitNode` walks that tree and builds matching `PlanState` nodes with runtime function pointers, slots, expression state, instrumentation, and links to the shared [[shared/concepts/executor-state|EState]].

## Where It Appears

- [[v18/subsystems/planner]] produces the `Plan` tree inside a [[shared/concepts/planned-statement|PlannedStmt]].
- [[v18/subsystems/executor]] initializes and executes the `PlanState` tree.
- [[v18/code-paths/simple-select-query]] reaches `ExecProcNode` through `ExecutePlan`.
- [[v18/code-paths/insert-path]], [[v18/code-paths/update-path]], and [[v18/code-paths/delete-path]] use a [[shared/concepts/modifytable|ModifyTable]] `Plan` and `ModifyTableState`.

## Related Structures and Functions

- `Plan` in `src/include/nodes/plannodes.h`
- `PlanState` in `src/include/nodes/execnodes.h`
- `ExecInitNode`
- `ExecProcNode`
- `ExecutePlan`
- `innerPlan`, `outerPlan`, `innerPlanState`, and `outerPlanState`

## Interactions With Other Concepts

- [[shared/concepts/planned-statement|PlannedStmt]] owns the root `Plan`.
- [[shared/concepts/querydesc|QueryDesc]] stores the root `PlanState` after `ExecutorStart`.
- Most executor node calls return a [[shared/concepts/tuple-table-slot|TupleTableSlot]] or `NULL`.
- `PlanState.state` points at the query-wide [[shared/concepts/executor-state|EState]].

## Version Notes

Verified against PostgreSQL 18 at commit `6cb307251c5c6261286c1566496920976640108e`.

## Source References

- `raw/postgres-18/src/include/nodes/plannodes.h:Plan`
- `raw/postgres-18/src/include/nodes/execnodes.h:PlanState`
- `raw/postgres-18/src/backend/executor/README`
- `raw/postgres-18/src/backend/executor/execProcnode.c:ExecInitNode`
- `raw/postgres-18/src/include/executor/executor.h:ExecProcNode`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutePlan`

## Open Questions

- Which plan node families should be documented next: scan nodes, join nodes, aggregate nodes, or DML nodes?
- Should `Path` to `Plan` conversion be covered here or only in [[shared/concepts/path-and-reloptinfo]]?
