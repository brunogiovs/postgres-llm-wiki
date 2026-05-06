---
type: concept
scope: shared
verified_against:
  18: 6cb307251c5c6261286c1566496920976640108e
primary_example_version: 18
---

# Path and RelOptInfo

## Definition

`RelOptInfo` is the planner's representation of a relation-like planning unit. `Path` is a candidate way to produce rows for a `RelOptInfo`, with estimated rows, cost, ordering, parallel-safety, and implementation type.

## Why It Exists

The planner often considers many possible ways to produce the same logical rows. `RelOptInfo` gathers relation-level planning information and candidate path lists; `Path` nodes describe specific alternatives. The planner chooses cheaper paths and later converts selected paths into executor-facing [[shared/concepts/plan-and-planstate|Plan]] nodes.

## Where It Appears

- [[v18/subsystems/planner]] names `RelOptInfo` and `Path` as core planning structures.
- [[v18/code-paths/simple-select-query]] reaches path selection before a scan plan is produced.
- [[v18/code-paths/insert-path]], [[v18/code-paths/update-path]], and [[v18/code-paths/delete-path]] create `ModifyTablePath` before making a [[shared/concepts/modifytable|ModifyTable]] plan.

## Related Structures and Functions

- `RelOptInfo` in `src/include/nodes/pathnodes.h`
- `Path` in `src/include/nodes/pathnodes.h`
- `ModifyTablePath`
- `subquery_planner`
- `create_modifytable_path`
- `create_modifytable_plan`

## Interactions With Other Concepts

- Paths are planner-side alternatives; [[shared/concepts/plan-and-planstate|Plan]] nodes are executor-facing output.
- `ModifyTablePath` stores a child `Path`, while [[shared/concepts/modifytable|ModifyTable]] stores a child `Plan`.
- `RelOptInfo.pathlist`, `partial_pathlist`, and cheapest-path fields are key handoff points for scan and join planning pages.

## Version Notes

Verified against PostgreSQL 18 at commit `6cb307251c5c6261286c1566496920976640108e`.

## Source References

- `raw/postgres-18/src/include/nodes/pathnodes.h:RelOptInfo`
- `raw/postgres-18/src/include/nodes/pathnodes.h:Path`
- `raw/postgres-18/src/include/nodes/pathnodes.h:ModifyTablePath`
- `raw/postgres-18/src/backend/optimizer/README`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:subquery_planner`
- `raw/postgres-18/src/backend/optimizer/util/pathnode.c:create_modifytable_path`
- `raw/postgres-18/src/backend/optimizer/plan/createplan.c:create_modifytable_plan`

## Open Questions

- Which scan path constructors should get focused source-backed pages first?
- How should join search and upper relations be split into separate concept pages?
