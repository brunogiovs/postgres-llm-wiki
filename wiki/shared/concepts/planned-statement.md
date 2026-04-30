---
type: concept
scope: shared
verified_against:
  18: 6cb307251c5c6261286c1566496920976640108e
primary_example_version: 18
---

# Planned Statement

## Definition

A `PlannedStmt` is the planner's top-level output for a statement. It wraps the executor-facing plan tree and the metadata the executor and command-processing paths need to run the statement.

## Why It Exists

The executor does not run a `Query` tree directly. Planning turns a rewritten [[shared/concepts/query-tree|Query]] into a `PlannedStmt` whose `planTree` points at the root [[shared/concepts/plan-and-planstate|Plan]] node. PostgreSQL also wraps utility statements in `PlannedStmt` nodes so upper APIs can handle planned and utility statements through a common list shape.

## Where It Appears

- [[v18/subsystems/planner]] returns `PlannedStmt` from `planner`.
- [[v18/code-paths/simple-select-query]] stores planned statements in a [[shared/concepts/portal|Portal]].
- [[v18/code-paths/insert-path]], [[v18/code-paths/update-path]], and [[v18/code-paths/delete-path]] execute planned DML through `ProcessQuery`.
- [[v18/subsystems/executor]] receives a `PlannedStmt` through [[shared/concepts/querydesc|QueryDesc]] and [[shared/concepts/executor-state|EState]].

## Related Structures and Functions

- `PlannedStmt` in `src/include/nodes/plannodes.h`
- `pg_plan_query` and `pg_plan_queries`
- `planner` and `standard_planner`
- `PortalData.stmts`
- `QueryDesc.plannedstmt`
- `EState.es_plannedstmt`

## Interactions With Other Concepts

- `PlannedStmt.planTree` is the top of the [[shared/concepts/plan-and-planstate|Plan]] tree.
- `PlannedStmt.resultRelations` records target relations for DML and feeds executor setup for [[shared/concepts/modifytable|ModifyTable]].
- A [[shared/concepts/portal|Portal]] stores a list of `PlannedStmt` nodes before execution.

## Version Notes

Verified against PostgreSQL 18 at commit `6cb307251c5c6261286c1566496920976640108e`.

## Source References

- `raw/postgres-18/src/include/nodes/plannodes.h:PlannedStmt`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_plan_query`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_plan_queries`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:planner`
- `raw/postgres-18/src/include/utils/portal.h:PortalData`
- `raw/postgres-18/src/include/executor/execdesc.h:QueryDesc`

## Open Questions

- Which `PlannedStmt` fields are essential for first-pass planner explanations versus advanced pages?
- Should utility-statement wrapping be covered here or in a separate utility execution page?
