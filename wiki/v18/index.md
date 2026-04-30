# PostgreSQL 18

## Source Pin

- Branch: `REL_18_STABLE`
- Commit: `6cb307251c5c6261286c1566496920976640108e`
- Status: `primary`
- Source path: `raw/postgres-18/`
- Added: 2026-04-30

## Coverage

Query lifecycle subsystem spine, first code-path pages, and foundational shared concept pages are initialized. Source-backed pages exist for parser, analyzer, rewriter, planner, executor, simple `SELECT`, `INSERT`, `UPDATE`, `DELETE`, and recurring planning/executor concepts.

## Subsystems

- [[v18/subsystems/parser]] - Raw SQL parsing into raw parse trees.
- [[v18/subsystems/analyzer]] - Raw parse tree transformation into `Query` trees.
- [[v18/subsystems/rewriter]] - Query rewrite system for analyzed `Query` trees.
- [[v18/subsystems/planner]] - Planning rewritten `Query` trees into `PlannedStmt` / `Plan` trees.
- [[v18/subsystems/executor]] - Running planned query trees through executor state and plan nodes.

## Code Paths

- [[v18/code-paths/simple-select-query]] - Simple `SELECT` through parse, analyze/rewrite, plan, portal execution, and executor.
- [[v18/code-paths/insert-path]] - Simple `INSERT ... VALUES` through `ModifyTable` and `ExecInsert`.
- [[v18/code-paths/update-path]] - Simple `UPDATE` through `ModifyTable` and `ExecUpdate`.
- [[v18/code-paths/delete-path]] - Simple `DELETE` through `ModifyTable` and `ExecDelete`.

## Concepts

No PostgreSQL 18-specific concept pages have been created yet.

### Shared Concepts Verified Against PG18

- [[shared/concepts/query-tree]] - `Query` trees.
- [[shared/concepts/planned-statement]] - `PlannedStmt`.
- [[shared/concepts/plan-and-planstate]] - `Plan` and `PlanState`.
- [[shared/concepts/path-and-reloptinfo]] - `Path` and `RelOptInfo`.
- [[shared/concepts/executor-state]] - `EState`.
- [[shared/concepts/tuple-table-slot]] - `TupleTableSlot`.
- [[shared/concepts/modifytable]] - `ModifyTable` and `ModifyTableState`.
- [[shared/concepts/portal]] - `Portal`.
- [[shared/concepts/querydesc]] - `QueryDesc`.

## Files

No source file map pages have been created yet.

## Questions

No filed question pages have been created yet.

## Open Questions

- Which lower-level storage paths should be traced after the DML code paths: heap insert, heap update, heap delete, WAL emission, or index maintenance?
- Which newly created shared concept pages should be expanded first with diagrams or deeper traces?
