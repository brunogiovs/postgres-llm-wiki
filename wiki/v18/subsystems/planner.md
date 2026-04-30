---
type: subsystem
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# Planner

## Role

The planner turns an already-rewritten [[shared/concepts/query-tree|Query]] tree into a [[shared/concepts/planned-statement|PlannedStmt]] containing a plan tree for the executor. In PostgreSQL 18, `pg_plan_query` is the top-level wrapper for a single rewritten query and calls `planner`.

The optimizer README summarizes the planner/optimizer area as taking the `Query` structure returned by the parser and generating a plan used by the executor. It distinguishes major subdirectories: `plan` for output plan generation, `path` for possible scan/join paths, `prep` for preprocessing, `util` for utilities, and `geqo` for genetic query optimization.

## Major Entry Points

| Symbol | File | Purpose |
|---|---|---|
| `pg_plan_query` | `src/backend/tcop/postgres.c` | Top-level wrapper for planning one rewritten query. |
| `planner` | `src/backend/optimizer/plan/planner.c` | Calls `planner_hook` if installed, otherwise calls `standard_planner`. |
| `standard_planner` | `src/backend/optimizer/plan/planner.c` | Standard planner implementation; builds planner global state and produces a `PlannedStmt`. |
| `subquery_planner` | `src/backend/optimizer/plan/planner.c` | Plans a `Query` level and is called recursively for subqueries. |
| `standard_planner` and `subquery_planner` | `src/include/optimizer/planner.h` | Planner-internal API declarations. |

## Core Data Structures

- [[shared/concepts/query-tree|Query]] - rewritten input tree.
- [[shared/concepts/planned-statement|PlannedStmt]] - planned output returned by `planner`.
- `PlannerGlobal` - global state across all subquery levels in one planner invocation.
- `PlannerInfo` - per-query-level planning state created by `subquery_planner`.
- [[shared/concepts/path-and-reloptinfo|RelOptInfo]] - represents base relations and join relations considered during planning.
- [[shared/concepts/path-and-reloptinfo|Path]] - candidate implementation path; the optimizer chooses cheaper paths and later turns one into a [[shared/concepts/plan-and-planstate|Plan]].
- [[shared/concepts/plan-and-planstate|Plan]] - executor-facing plan node tree.

## Related Concepts

- [[shared/concepts/query-tree|Query]] tree
- [[shared/concepts/planned-statement|PlannedStmt]]
- [[shared/concepts/path-and-reloptinfo|Path]] versus [[shared/concepts/plan-and-planstate|Plan]]
- `PlannerInfo`
- [[shared/concepts/path-and-reloptinfo|RelOptInfo]]
- Join search
- Cost estimates
- GEQO

`PlannedStmt`, `Path`, `RelOptInfo`, and `Plan` are now documented as shared concepts; remaining planner topics should be promoted when specific traces need them.

## Important Code Paths

- [[v18/code-paths/simple-select-query]] - Planning a simple `SELECT`.
- [[v18/code-paths/insert-path]] - Planning simple `INSERT` into `ModifyTable`.
- [[v18/code-paths/update-path]] - Planning simple `UPDATE` into `ModifyTable`.
- [[v18/code-paths/delete-path]] - Planning simple `DELETE` into `ModifyTable`.
- Join search, path selection, and plan creation: later planner-specific deep dives.

## Differences Across Supported Versions

Only PostgreSQL 18 is currently supported.

## Source References

- `raw/postgres-18/src/backend/tcop/postgres.c:pg_plan_query`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:planner`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:standard_planner`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:subquery_planner`
- `raw/postgres-18/src/include/optimizer/planner.h`
- `raw/postgres-18/src/backend/optimizer/README`
- `raw/postgres-18/src/backend/optimizer/plan/README`

## Open Questions

- Which planner functions are traversed by a minimal single-table `SELECT`?
- Where should path generation and path costing be split into separate pages?
- Which planner structs deserve early concept pages: `PlannerInfo`, `RelOptInfo`, `Path`, or `PlannedStmt`?
