---
type: concept
scope: shared
verified_against:
  18: 6cb307251c5c6261286c1566496920976640108e
primary_example_version: 18
---

# Query Tree

## Definition

A `Query` tree is PostgreSQL's analyzed representation of one SQL statement after parse analysis. It is richer than a raw parse tree: names have been resolved, semantic flags are set, range-table entries are available, and statement-specific clauses have been transformed into internal node structures.

## Why It Exists

The parser produces raw syntax nodes, but the rewriter and planner need a semantically meaningful tree. `Query` is the handoff shape between parse analysis, rewrite, and planning. PostgreSQL's own `Query` comment says parse analysis turns statements into `Query` trees for the rewriter and planner, and planning later converts them into `Plan` trees headed by a `PlannedStmt`.

## Where It Appears

- [[v18/subsystems/analyzer]] creates `Query` trees through `parse_analyze_*`.
- [[v18/subsystems/rewriter]] accepts analyzed `Query` trees and may return zero, one, or many rewritten trees.
- [[v18/subsystems/planner]] consumes rewritten `Query` trees.
- [[v18/code-paths/simple-select-query]], [[v18/code-paths/insert-path]], [[v18/code-paths/update-path]], and [[v18/code-paths/delete-path]] all cross this boundary.

## Related Structures and Functions

- `Query` in `src/include/nodes/parsenodes.h`
- `parse_analyze_fixedparams`, `parse_analyze_varparams`, and `parse_analyze_withcb`
- `transformTopLevelStmt` and statement-specific transformer functions
- `pg_rewrite_query` and `QueryRewrite`
- `pg_plan_query` and `pg_plan_queries`

## Interactions With Other Concepts

- A `Query` becomes a [[shared/concepts/planned-statement|PlannedStmt]] after planning.
- DML query trees carry `commandType`, `resultRelation`, `targetList`, and related fields that later inform [[shared/concepts/modifytable|ModifyTable]] planning.
- `Query.targetList` contains `TargetEntry` nodes, which recur in analyzer and planner traces.

## Version Notes

Verified against PostgreSQL 18 at commit `6cb307251c5c6261286c1566496920976640108e`.

## Source References

- `raw/postgres-18/src/include/nodes/parsenodes.h:Query`
- `raw/postgres-18/src/backend/parser/analyze.c:parse_analyze_fixedparams`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_rewrite_query`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_plan_query`

## Open Questions

- Which `Query` fields should get their own concept pages first: `rtable`, `jointree`, `targetList`, or command-specific fields?
- How much should utility-statement `CMD_UTILITY` behavior live here versus in a separate utility command page?
