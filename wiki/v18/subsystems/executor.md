---
type: subsystem
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# Executor

## Role

The executor runs a planned query tree. In PostgreSQL 18, the top-level executor interface is `ExecutorStart`, `ExecutorRun`, `ExecutorFinish`, and `ExecutorEnd`, all implemented in `src/backend/executor/execMain.c`.

The executor README describes the executor as processing a tree of plan nodes in a demand-pull pipeline: each node produces its next tuple when called, or `NULL` when it has no more output. It also distinguishes the read-only planner-produced [[shared/concepts/plan-and-planstate|Plan]] tree from the executor's runtime [[shared/concepts/plan-and-planstate|PlanState]] tree.

## Major Entry Points

| Symbol | File | Purpose |
|---|---|---|
| `ExecutorStart` | `src/backend/executor/execMain.c` | Starts execution for a [[shared/concepts/querydesc|QueryDesc]] and dispatches to the hook or `standard_ExecutorStart`. |
| `standard_ExecutorStart` | `src/backend/executor/execMain.c` | Builds `EState`, switches to the per-query memory context, initializes parameters, and starts plan setup. |
| `ExecutorRun` | `src/backend/executor/execMain.c` | Runs an initialized executor instance and dispatches to the hook or `standard_ExecutorRun`. |
| `standard_ExecutorRun` | `src/backend/executor/execMain.c` | Starts the destination receiver when tuples are emitted and calls `ExecutePlan` unless direction is `NoMovement`. |
| `ExecutorFinish` | `src/backend/executor/execMain.c` | Performs post-run work, including `ExecPostprocessPlan` and queued AFTER triggers when not skipped. |
| `ExecutorEnd` | `src/backend/executor/execMain.c` | Ends execution, calls `ExecEndPlan`, unregisters snapshots, and frees executor state. |
| `ExecInitNode` | `src/backend/executor/execProcnode.c` | Initializes executor state for plan nodes. |
| `ExecProcNode` | `src/include/executor/executor.h` | Inline call path for executing a [[shared/concepts/plan-and-planstate|PlanState]] node to return another tuple. |

## Core Data Structures

- [[shared/concepts/querydesc|QueryDesc]] - execution descriptor passed through the top-level executor interface.
- [[shared/concepts/executor-state|EState]] - executor state allocated by `CreateExecutorState` in `standard_ExecutorStart`.
- [[shared/concepts/plan-and-planstate|Plan]] - read-only plan node tree produced by the planner.
- [[shared/concepts/plan-and-planstate|PlanState]] - executor runtime state tree corresponding to plan nodes.
- `ExprState` - runtime representation of executable expressions, described in `src/backend/executor/README`.
- [[shared/concepts/tuple-table-slot|TupleTableSlot]] - tuple container returned by executor node calls such as `ExecProcNode`.
- `DestReceiver` - tuple destination receiver started and shut down by `standard_ExecutorRun` when tuples are emitted.

## Related Concepts

- [[shared/concepts/plan-and-planstate|Plan tree]]
- [[shared/concepts/plan-and-planstate|Plan state tree]]
- Demand-pull execution
- [[shared/concepts/executor-state|EState]]
- [[shared/concepts/querydesc|QueryDesc]]
- [[shared/concepts/tuple-table-slot|TupleTableSlot]]
- Executor memory contexts
- Expression evaluation

`PlanState`, `EState`, `QueryDesc`, and `TupleTableSlot` are now documented as shared concepts; memory contexts and expression evaluation remain future concept candidates.

## Important Code Paths

- [[v18/code-paths/simple-select-query]] - Simple `SELECT` execution through portal and `ExecutePlan`.
- [[v18/code-paths/insert-path]] - Simple `INSERT` execution through `ModifyTable` and `ExecInsert`.
- [[v18/code-paths/update-path]] - Simple `UPDATE` execution through `ModifyTable` and `ExecUpdate`.
- [[v18/code-paths/delete-path]] - Simple `DELETE` execution through `ModifyTable` and `ExecDelete`.
- Expression initialization and evaluation: later executor-specific deep dive.
- Node initialization and execution dispatch: later file pages for `execProcnode.c` and selected `node*.c` files.

## Differences Across Supported Versions

Only PostgreSQL 18 is currently supported.

## Source References

- `raw/postgres-18/src/backend/tcop/pquery.c:ExecutorStart`
- `raw/postgres-18/src/backend/tcop/pquery.c:ExecutorRun`
- `raw/postgres-18/src/backend/tcop/pquery.c:ExecutorFinish`
- `raw/postgres-18/src/backend/tcop/pquery.c:ExecutorEnd`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorStart`
- `raw/postgres-18/src/backend/executor/execMain.c:standard_ExecutorStart`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorRun`
- `raw/postgres-18/src/backend/executor/execMain.c:standard_ExecutorRun`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorFinish`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorEnd`
- `raw/postgres-18/src/backend/executor/execProcnode.c:ExecInitNode`
- `raw/postgres-18/src/include/executor/executor.h:ExecProcNode`
- `raw/postgres-18/src/backend/executor/README`

## Open Questions

- Which executor node types are traversed by a minimal single-table `SELECT`?
- Where should `ModifyTable` behavior be split between `INSERT`, `UPDATE`, and `DELETE` code-path pages?
- Which executor concepts should be promoted first: `EState`, `PlanState`, `TupleTableSlot`, or expression evaluation?
