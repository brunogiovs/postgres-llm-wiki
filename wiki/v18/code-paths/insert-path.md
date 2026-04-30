---
type: code-path
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# INSERT Path

## Scope

This page traces a simple PostgreSQL 18 `INSERT ... VALUES` executed through the simple Query protocol.

Representative shape:

```sql
INSERT INTO some_table (a, b) VALUES (1, 2);
```

The main path assumes an ordinary target table, no `ON CONFLICT`, no `RETURNING`, no partition routing, no foreign table, no view `INSTEAD OF` trigger, and no rewrite rule that expands the statement. Source references point to the richer branches where those cases begin.

## High-Level Flow

1. The simple-protocol wrapper parses, analyzes/rewrite, plans, creates a portal, and runs it.
2. The analyzer dispatches `T_InsertStmt` to `transformInsertStmt`.
3. For a single `VALUES` row, `transformInsertStmt` transforms the expression list, prepares it for assignment to target columns, and builds the query target list.
4. The planner creates a `ModifyTablePath` for non-`SELECT` commands and turns it into a [[shared/concepts/modifytable|ModifyTable]] plan.
5. A no-`RETURNING` `INSERT` uses the general [[shared/concepts/portal|Portal]] path; `PortalRunMulti` calls `ProcessQuery`.
6. `ProcessQuery` creates a [[shared/concepts/querydesc|QueryDesc]], calls `ExecutorStart`, runs the plan to completion, then calls `ExecutorFinish` and `ExecutorEnd`.
7. `ExecModifyTable` fetches source rows from its subplan and dispatches `CMD_INSERT` to `ExecInsert`.
8. `ExecInsert` stores the tuple in the target relation and maintains indexes.

## Detailed Flow

| Step | Function | File | Notes |
|---|---|---|---|
| 1 | `exec_simple_query` | `src/backend/tcop/postgres.c` | Simple Query protocol entry point. |
| 2 | `pg_parse_query` -> `raw_parser` | `src/backend/tcop/postgres.c`, `src/backend/parser/parser.c` | Produces a raw parse tree containing an `InsertStmt`. |
| 3 | `pg_analyze_and_rewrite_fixedparams` | `src/backend/tcop/postgres.c` | Calls parse analysis, then rewrite. |
| 4 | `parse_analyze_fixedparams` | `src/backend/parser/analyze.c` | Converts the raw statement to a `Query`. |
| 5 | `transformStmt` -> `transformInsertStmt` | `src/backend/parser/analyze.c` | Dispatches `T_InsertStmt` to insert-specific analysis. |
| 6 | `setTargetTable` | called from `src/backend/parser/analyze.c:transformInsertStmt` | Adds the target table as the result relation with insert permissions. |
| 7 | `transformExpressionList` | called from `src/backend/parser/analyze.c:transformInsertStmt` | For a single `VALUES` row, transforms source expressions. |
| 8 | `transformInsertRow` | `src/backend/parser/analyze.c` | Coerces/prepares source expressions for target columns. |
| 9 | target-list construction | `src/backend/parser/analyze.c:transformInsertStmt` | Builds `TargetEntry` nodes for insert target columns and marks inserted columns for permission checks. |
| 10 | `pg_rewrite_query` -> `QueryRewrite` | `src/backend/tcop/postgres.c`, `src/backend/rewrite/rewriteHandler.c` | Runs rewrite for the analyzed `Query`. |
| 11 | `pg_plan_queries` -> `pg_plan_query` | `src/backend/tcop/postgres.c` | Plans the rewritten insert query. |
| 12 | `preprocess_targetlist` | `src/backend/optimizer/prep/preptlist.c` | For `INSERT`, expands the target list to match target table attributes. |
| 13 | `planner` / `standard_planner` / `subquery_planner` | `src/backend/optimizer/plan/planner.c` | Standard planning path. |
| 14 | `create_modifytable_path` | `src/backend/optimizer/util/pathnode.c` | Creates a `ModifyTablePath` for `INSERT` / `UPDATE` / `DELETE` / `MERGE`. |
| 15 | `create_modifytable_plan` -> `make_modifytable` | `src/backend/optimizer/plan/createplan.c` | Builds the `ModifyTable` plan node. |
| 16 | `ChoosePortalStrategy` | `src/backend/tcop/pquery.c` | With no `RETURNING`, this falls through to `PORTAL_MULTI_QUERY`. |
| 17 | `PortalRunMulti` -> `ProcessQuery` | `src/backend/tcop/pquery.c` | Executes the planned DML statement. |
| 18 | `ProcessQuery` | `src/backend/tcop/pquery.c` | Creates `QueryDesc`, calls `ExecutorStart`, `ExecutorRun`, `ExecutorFinish`, and `ExecutorEnd`. |
| 19 | `ExecInitNode` -> `ExecInitModifyTable` | `src/backend/executor/execProcnode.c`, `src/backend/executor/nodeModifyTable.c` | Initializes the `ModifyTable` plan state. |
| 20 | `ExecutorRun` -> `ExecutePlan` -> `ExecProcNode` | `src/backend/executor/execMain.c`, `src/include/executor/executor.h` | Runs the plan tree. |
| 21 | `ExecModifyTable` | `src/backend/executor/nodeModifyTable.c` | Fetches rows from its subplan and dispatches by operation. |
| 22 | `ExecGetInsertNewTuple` -> `ExecInsert` | `src/backend/executor/nodeModifyTable.c` | Builds the new tuple for the result relation and inserts it. |

## Key Data Structures

- `InsertStmt` - raw parser node dispatched by `transformStmt`.
- [[shared/concepts/query-tree|Query]] with `commandType = CMD_INSERT`.
- `TargetEntry` - insert target-list entries.
- [[shared/concepts/planned-statement|PlannedStmt]] with a top-level [[shared/concepts/modifytable|ModifyTable]] plan for DML.
- [[shared/concepts/portal|Portal]] - execution wrapper that chooses the multi-query path for no-`RETURNING` DML.
- [[shared/concepts/querydesc|QueryDesc]] - executor descriptor created by `ProcessQuery`.
- [[shared/concepts/path-and-reloptinfo|ModifyTablePath]] - planner path node for DML.
- [[shared/concepts/modifytable|ModifyTable / ModifyTableState]] - executor plan and state for table modification.
- `ResultRelInfo` - executor metadata for the target relation.
- [[shared/concepts/tuple-table-slot|TupleTableSlot]] - carries source and inserted tuple values.

## Cross-Links

- [[v18/subsystems/parser]]
- [[v18/subsystems/analyzer]]
- [[v18/subsystems/rewriter]]
- [[v18/subsystems/planner]]
- [[v18/subsystems/executor]]

## Source References

- `raw/postgres-18/src/backend/tcop/postgres.c:exec_simple_query`
- `raw/postgres-18/src/backend/parser/analyze.c:transformStmt`
- `raw/postgres-18/src/backend/parser/analyze.c:transformInsertStmt`
- `raw/postgres-18/src/backend/parser/analyze.c:transformInsertRow`
- `raw/postgres-18/src/backend/rewrite/rewriteHandler.c:QueryRewrite`
- `raw/postgres-18/src/backend/optimizer/prep/preptlist.c:preprocess_targetlist`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:planner`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:subquery_planner`
- `raw/postgres-18/src/backend/optimizer/util/pathnode.c:create_modifytable_path`
- `raw/postgres-18/src/backend/optimizer/plan/createplan.c:create_modifytable_plan`
- `raw/postgres-18/src/backend/optimizer/plan/createplan.c:make_modifytable`
- `raw/postgres-18/src/backend/tcop/pquery.c:ChoosePortalStrategy`
- `raw/postgres-18/src/backend/tcop/pquery.c:PortalRunMulti`
- `raw/postgres-18/src/backend/tcop/pquery.c:ProcessQuery`
- `raw/postgres-18/src/backend/executor/execProcnode.c:ExecInitNode`
- `raw/postgres-18/src/backend/executor/nodeModifyTable.c:ExecInitModifyTable`
- `raw/postgres-18/src/backend/executor/nodeModifyTable.c:ExecModifyTable`
- `raw/postgres-18/src/backend/executor/nodeModifyTable.c:ExecInsert`

## Open Questions

- Where should `INSERT ... SELECT`, multi-row `VALUES`, and `DEFAULT VALUES` get separate subpaths?
- How should `ON CONFLICT` be split between analyzer, planner, and executor pages?
- Which table access method call inside `ExecInsert` should be the next lower-level storage trace?
