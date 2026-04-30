---
type: concept
scope: shared
verified_against:
  18: 6cb307251c5c6261286c1566496920976640108e
primary_example_version: 18
---

# ModifyTable

## Definition

`ModifyTable` is the planner and executor plan node family for table-changing statements: `INSERT`, `UPDATE`, `DELETE`, and `MERGE`.

## Why It Exists

DML statements share a high-level execution shape: produce candidate rows from a subplan, identify target result relations, apply checks/triggers/FDW behavior as needed, perform the table operation, and optionally return rows. `ModifyTablePath` represents this shape while planning, `ModifyTable` represents it in the final plan, and `ModifyTableState` holds runtime executor state.

## Where It Appears

- [[v18/code-paths/insert-path]] builds a `ModifyTable` plan and dispatches to `ExecInsert`.
- [[v18/code-paths/update-path]] builds a `ModifyTable` plan and dispatches to `ExecUpdate`.
- [[v18/code-paths/delete-path]] builds a `ModifyTable` plan and dispatches to `ExecDelete`.
- [[v18/subsystems/planner]] reaches DML planning through `create_modifytable_path` and `make_modifytable`.
- [[v18/subsystems/executor]] initializes and runs `ModifyTableState`.

## Related Structures and Functions

- `ModifyTablePath` in `src/include/nodes/pathnodes.h`
- `ModifyTable` in `src/include/nodes/plannodes.h`
- `ModifyTableState` in `src/include/nodes/execnodes.h`
- `create_modifytable_path`
- `create_modifytable_plan`
- `make_modifytable`
- `ExecInitModifyTable`
- `ExecModifyTable`
- `ExecInsert`, `ExecUpdate`, and `ExecDelete`

## Interactions With Other Concepts

- `ModifyTablePath` belongs to the [[shared/concepts/path-and-reloptinfo|Path and RelOptInfo]] planning world.
- `ModifyTable` is a [[shared/concepts/plan-and-planstate|Plan]] node.
- Runtime DML uses [[shared/concepts/executor-state|EState]], `ResultRelInfo`, and [[shared/concepts/tuple-table-slot|TupleTableSlot]].
- Planned DML arrives through a [[shared/concepts/planned-statement|PlannedStmt]] and [[shared/concepts/querydesc|QueryDesc]].

## Version Notes

Verified against PostgreSQL 18 at commit `6cb307251c5c6261286c1566496920976640108e`.

## Source References

- `raw/postgres-18/src/include/nodes/pathnodes.h:ModifyTablePath`
- `raw/postgres-18/src/include/nodes/plannodes.h:ModifyTable`
- `raw/postgres-18/src/include/nodes/execnodes.h:ModifyTableState`
- `raw/postgres-18/src/backend/optimizer/util/pathnode.c:create_modifytable_path`
- `raw/postgres-18/src/backend/optimizer/plan/createplan.c:create_modifytable_plan`
- `raw/postgres-18/src/backend/optimizer/plan/createplan.c:make_modifytable`
- `raw/postgres-18/src/backend/executor/nodeModifyTable.c:ExecInitModifyTable`
- `raw/postgres-18/src/backend/executor/nodeModifyTable.c:ExecModifyTable`

## Open Questions

- Should `ExecInsert`, `ExecUpdate`, and `ExecDelete` each get deeper storage-level code-path pages?
- How should `MERGE`, `ON CONFLICT`, and partition routing be separated from the simple DML paths?
