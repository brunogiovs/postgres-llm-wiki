---
type: code-path
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# UPDATE Path

## Scope

This page traces a simple PostgreSQL 18 `UPDATE` executed through the simple Query protocol.

Representative shape:

```sql
UPDATE some_table SET value = value + 1 WHERE id = 1;
```

The main path assumes an ordinary target table, no `FROM`, no `RETURNING`, no partition-key movement, no foreign table, no view `INSTEAD OF` trigger, and no rewrite rule expansion. The source references include branches where PostgreSQL handles richer cases.

## High-Level Flow

1. The simple-protocol wrapper parses, analyzes/rewrite, plans, creates a portal, and runs it.
2. The analyzer dispatches `T_UpdateStmt` to `transformUpdateStmt`.
3. `transformUpdateStmt` records the target relation, transforms `WHERE`, transforms `RETURNING` if present, and transforms the `SET` target list.
4. Planner target-list preprocessing records update target column numbers and adds row-identity junk entries needed by the executor.
5. The planner creates a `ModifyTablePath` and then a [[shared/concepts/modifytable|ModifyTable]] plan.
6. A no-`RETURNING` `UPDATE` runs through [[shared/concepts/portal|PORTAL_MULTI_QUERY]] and `ProcessQuery`.
7. [[shared/concepts/modifytable|ExecModifyTable]] fetches subplan rows, extracts row identity, builds the new tuple from old tuple plus plan output, and calls `ExecUpdate`.
8. `ExecUpdate` handles triggers/FDWs/ordinary table update behavior and returns a `RETURNING` slot only when needed.

## Detailed Flow

| Step | Function | File | Notes |
|---|---|---|---|
| 1 | `exec_simple_query` | `src/backend/tcop/postgres.c` | Simple Query protocol entry point. |
| 2 | `pg_parse_query` -> `raw_parser` | `src/backend/tcop/postgres.c`, `src/backend/parser/parser.c` | Produces a raw parse tree containing an `UpdateStmt`. |
| 3 | `pg_analyze_and_rewrite_fixedparams` | `src/backend/tcop/postgres.c` | Calls parse analysis, then rewrite. |
| 4 | `parse_analyze_fixedparams` | `src/backend/parser/analyze.c` | Converts the raw statement to a `Query`. |
| 5 | `transformStmt` -> `transformUpdateStmt` | `src/backend/parser/analyze.c` | Dispatches `T_UpdateStmt` to update-specific analysis. |
| 6 | `setTargetTable` | called from `src/backend/parser/analyze.c:transformUpdateStmt` | Adds the target relation with update permissions. |
| 7 | `transformWhereClause` | called from `src/backend/parser/analyze.c:transformUpdateStmt` | Transforms the `WHERE` predicate. |
| 8 | `transformUpdateTargetList` | `src/backend/parser/analyze.c` | Handles the `SET` clause and update target columns. |
| 9 | `pg_rewrite_query` -> `QueryRewrite` | `src/backend/tcop/postgres.c`, `src/backend/rewrite/rewriteHandler.c` | Runs rewrite for the analyzed `Query`. |
| 10 | `pg_plan_queries` -> `pg_plan_query` | `src/backend/tcop/postgres.c` | Plans the rewritten update query. |
| 11 | `preprocess_targetlist` | `src/backend/optimizer/prep/preptlist.c` | For `UPDATE`, records target column numbers and adds row-identity junk entries for the executor. |
| 12 | `planner` / `standard_planner` / `subquery_planner` | `src/backend/optimizer/plan/planner.c` | Standard planning path. |
| 13 | `create_modifytable_path` | `src/backend/optimizer/util/pathnode.c` | Creates the DML path node and carries update column lists. |
| 14 | `create_modifytable_plan` -> `make_modifytable` | `src/backend/optimizer/plan/createplan.c` | Builds the `ModifyTable` plan node. |
| 15 | `ChoosePortalStrategy` | `src/backend/tcop/pquery.c` | With no `RETURNING`, this falls through to `PORTAL_MULTI_QUERY`. |
| 16 | `PortalRunMulti` -> `ProcessQuery` | `src/backend/tcop/pquery.c` | Executes the planned update statement. |
| 17 | `ProcessQuery` | `src/backend/tcop/pquery.c` | Creates `QueryDesc`, starts/runs/finishes/ends the executor. |
| 18 | `ExecInitNode` -> `ExecInitModifyTable` | `src/backend/executor/execProcnode.c`, `src/backend/executor/nodeModifyTable.c` | Initializes the `ModifyTable` plan state. |
| 19 | `ExecModifyTable` | `src/backend/executor/nodeModifyTable.c` | Fetches rows from the subplan with `ExecProcNode`. |
| 20 | row identity extraction | `src/backend/executor/nodeModifyTable.c:ExecModifyTable` | For `UPDATE`, fetches row identity from junk columns such as `ctid` for heap relations. |
| 21 | `ExecGetUpdateNewTuple` | `src/backend/executor/nodeModifyTable.c` | Builds the new tuple by combining plan output with the old tuple. |
| 22 | `ExecUpdate` | `src/backend/executor/nodeModifyTable.c` | Applies the update, with trigger/FDW/ordinary table branches. |

## Key Data Structures

- `UpdateStmt` - raw parser node dispatched by `transformStmt`.
- [[shared/concepts/query-tree|Query]] with `commandType = CMD_UPDATE`.
- `TargetEntry` - update expressions in the analyzed target list.
- `root->update_colnos` - planner-side update column list from `preprocess_targetlist`.
- row-identity junk entries - planner-added values such as `ctid` for locating rows.
- [[shared/concepts/portal|Portal]] - execution wrapper that chooses the multi-query path for no-`RETURNING` DML.
- [[shared/concepts/querydesc|QueryDesc]] - executor descriptor created by `ProcessQuery`.
- [[shared/concepts/path-and-reloptinfo|ModifyTablePath]] / [[shared/concepts/modifytable|ModifyTable / ModifyTableState]].
- `ResultRelInfo` - executor target relation metadata.
- [[shared/concepts/tuple-table-slot|TupleTableSlot]] - carries subplan output, old tuple, and new tuple values.

## Cross-Links

- [[v18/subsystems/parser]]
- [[v18/subsystems/analyzer]]
- [[v18/subsystems/rewriter]]
- [[v18/subsystems/planner]]
- [[v18/subsystems/executor]]

## Source References

- `raw/postgres-18/src/backend/tcop/postgres.c:exec_simple_query`
- `raw/postgres-18/src/backend/parser/analyze.c:transformStmt`
- `raw/postgres-18/src/backend/parser/analyze.c:transformUpdateStmt`
- `raw/postgres-18/src/backend/parser/analyze.c:transformUpdateTargetList`
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
- `raw/postgres-18/src/backend/executor/nodeModifyTable.c:ExecModifyTable`
- `raw/postgres-18/src/backend/executor/nodeModifyTable.c:ExecUpdate`

## Open Questions

- Where exactly are row-identity junk columns wired into the final plan for each table access method?
- How should EvalPlanQual rechecks be traced for concurrent update conflicts?
- Should cross-partition UPDATE be its own code-path page?
