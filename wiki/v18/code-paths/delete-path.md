---
type: code-path
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# DELETE Path

## Scope

This page traces a simple PostgreSQL 18 `DELETE` executed through the simple Query protocol.

Representative shape:

```sql
DELETE FROM some_table WHERE id = 1;
```

The main path assumes an ordinary target table, no `USING`, no `RETURNING`, no foreign table, no view `INSTEAD OF` trigger, and no rewrite rule expansion.

## High-Level Flow

1. The simple-protocol wrapper parses, analyzes/rewrite, plans, creates a portal, and runs it.
2. The analyzer dispatches `T_DeleteStmt` to `transformDeleteStmt`.
3. `transformDeleteStmt` records the target relation, transforms optional `USING`, transforms `WHERE`, and builds the query jointree.
4. Planner target-list preprocessing adds row-identity junk entries needed by the executor.
5. The planner creates a `ModifyTablePath` and then a [[shared/concepts/modifytable|ModifyTable]] plan.
6. A no-`RETURNING` `DELETE` runs through [[shared/concepts/portal|PORTAL_MULTI_QUERY]] and `ProcessQuery`.
7. [[shared/concepts/modifytable|ExecModifyTable]] fetches subplan rows, extracts row identity, and dispatches `CMD_DELETE` to `ExecDelete`.
8. `ExecDelete` handles prologue/triggers/FDW/ordinary table delete behavior and returns a `RETURNING` slot only when needed.

## Detailed Flow

| Step | Function | File | Notes |
|---|---|---|---|
| 1 | `exec_simple_query` | `src/backend/tcop/postgres.c` | Simple Query protocol entry point. |
| 2 | `pg_parse_query` -> `raw_parser` | `src/backend/tcop/postgres.c`, `src/backend/parser/parser.c` | Produces a raw parse tree containing a `DeleteStmt`. |
| 3 | `pg_analyze_and_rewrite_fixedparams` | `src/backend/tcop/postgres.c` | Calls parse analysis, then rewrite. |
| 4 | `parse_analyze_fixedparams` | `src/backend/parser/analyze.c` | Converts the raw statement to a `Query`. |
| 5 | `transformStmt` -> `transformDeleteStmt` | `src/backend/parser/analyze.c` | Dispatches `T_DeleteStmt` to delete-specific analysis. |
| 6 | `setTargetTable` | called from `src/backend/parser/analyze.c:transformDeleteStmt` | Adds the target relation with delete permissions. |
| 7 | `transformFromClause` | called from `src/backend/parser/analyze.c:transformDeleteStmt` | Handles the non-standard `USING` clause when present. |
| 8 | `transformWhereClause` | called from `src/backend/parser/analyze.c:transformDeleteStmt` | Transforms the delete predicate. |
| 9 | `pg_rewrite_query` -> `QueryRewrite` | `src/backend/tcop/postgres.c`, `src/backend/rewrite/rewriteHandler.c` | Runs rewrite for the analyzed `Query`. |
| 10 | `pg_plan_queries` -> `pg_plan_query` | `src/backend/tcop/postgres.c` | Plans the rewritten delete query. |
| 11 | `preprocess_targetlist` | `src/backend/optimizer/prep/preptlist.c` | For `DELETE`, adds row-identity junk entries so the executor can identify rows to delete. |
| 12 | `planner` / `standard_planner` / `subquery_planner` | `src/backend/optimizer/plan/planner.c` | Standard planning path. |
| 13 | `create_modifytable_path` | `src/backend/optimizer/util/pathnode.c` | Creates the DML path node. |
| 14 | `create_modifytable_plan` -> `make_modifytable` | `src/backend/optimizer/plan/createplan.c` | Builds the `ModifyTable` plan node. |
| 15 | `ChoosePortalStrategy` | `src/backend/tcop/pquery.c` | With no `RETURNING`, this falls through to `PORTAL_MULTI_QUERY`. |
| 16 | `PortalRunMulti` -> `ProcessQuery` | `src/backend/tcop/pquery.c` | Executes the planned delete statement. |
| 17 | `ProcessQuery` | `src/backend/tcop/pquery.c` | Creates `QueryDesc`, starts/runs/finishes/ends the executor. |
| 18 | `ExecInitNode` -> `ExecInitModifyTable` | `src/backend/executor/execProcnode.c`, `src/backend/executor/nodeModifyTable.c` | Initializes the `ModifyTable` plan state. |
| 19 | `ExecModifyTable` | `src/backend/executor/nodeModifyTable.c` | Fetches rows from the subplan with `ExecProcNode`. |
| 20 | row identity extraction | `src/backend/executor/nodeModifyTable.c:ExecModifyTable` | For `DELETE`, fetches row identity from junk columns such as `ctid` for heap relations. |
| 21 | `ExecDelete` | `src/backend/executor/nodeModifyTable.c` | Applies the delete, with trigger/FDW/ordinary table branches. |

## Key Data Structures

- `DeleteStmt` - raw parser node dispatched by `transformStmt`.
- [[shared/concepts/query-tree|Query]] with `commandType = CMD_DELETE`.
- row-identity junk entries - planner-added values such as `ctid` for locating rows.
- [[shared/concepts/portal|Portal]] - execution wrapper that chooses the multi-query path for no-`RETURNING` DML.
- [[shared/concepts/querydesc|QueryDesc]] - executor descriptor created by `ProcessQuery`.
- [[shared/concepts/path-and-reloptinfo|ModifyTablePath]] / [[shared/concepts/modifytable|ModifyTable / ModifyTableState]].
- `ResultRelInfo` - executor target relation metadata.
- [[shared/concepts/tuple-table-slot|TupleTableSlot]] - carries subplan output and row identity data.
- `ItemPointer` / `ctid` - heap tuple identity for ordinary heap relations.

## Cross-Links

- [[v18/subsystems/parser]]
- [[v18/subsystems/analyzer]]
- [[v18/subsystems/rewriter]]
- [[v18/subsystems/planner]]
- [[v18/subsystems/executor]]

## Source References

- `raw/postgres-18/src/backend/tcop/postgres.c:exec_simple_query`
- `raw/postgres-18/src/backend/parser/analyze.c:transformStmt`
- `raw/postgres-18/src/backend/parser/analyze.c:transformDeleteStmt`
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
- `raw/postgres-18/src/backend/executor/nodeModifyTable.c:ExecDelete`

## Open Questions

- Where exactly are row-identity junk columns wired into the final plan for heap versus non-heap table access methods?
- How should `DELETE ... USING` join planning be traced separately from the simple single-table case?
- Which lower-level table access method function should be the next storage trace for the ordinary heap delete path?
