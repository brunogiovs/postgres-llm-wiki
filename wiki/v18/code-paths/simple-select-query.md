---
type: code-path
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# Simple SELECT Query

## Scope

This page traces a simple PostgreSQL 18 `SELECT` executed through the simple Query protocol.

Representative shape:

```sql
SELECT * FROM some_table WHERE id = 1;
```

The trace intentionally excludes extended-protocol parse/bind/execute, prepared statements, cursors, set operations, CTEs, views/rules, row security, parallel plans, and detailed scan-path selection. The executor section includes a sequential scan as one concrete possible plan-node example, but the planner may choose another scan node depending on indexes, statistics, and costs.

## High-Level Flow

1. `exec_simple_query` receives the query string.
2. `pg_parse_query` calls the raw parser.
3. `pg_analyze_and_rewrite_fixedparams` turns each `RawStmt` into a [[shared/concepts/query-tree|Query]] and runs rewrite.
4. `pg_plan_queries` turns rewritten `Query` nodes into [[shared/concepts/planned-statement|PlannedStmt]] nodes.
5. The simple protocol path creates an unnamed [[shared/concepts/portal|Portal]], defines the planned query on it, starts it, and runs it to completion.
6. A one-statement plain `SELECT` uses `PORTAL_ONE_SELECT`, so `PortalStart` creates a [[shared/concepts/querydesc|QueryDesc]] and calls `ExecutorStart`.
7. `PortalRunSelect` calls `ExecutorRun`.
8. `ExecutorRun` calls `ExecutePlan`, which loops on `ExecProcNode` and sends result tuples to the destination receiver.

## Detailed Flow

| Step | Function | File | Notes |
|---|---|---|---|
| 1 | `exec_simple_query` | `src/backend/tcop/postgres.c` | Simple Query protocol entry point. |
| 2 | `pg_parse_query` | `src/backend/tcop/postgres.c` | Calls `raw_parser(query_string, RAW_PARSE_DEFAULT)`. |
| 3 | `raw_parser` | `src/backend/parser/parser.c` | Performs lexical and grammatical analysis and returns raw parse trees. |
| 4 | `pg_analyze_and_rewrite_fixedparams` | `src/backend/tcop/postgres.c` | Called by `exec_simple_query` with no fixed parameter list for the simple protocol path. |
| 5 | `parse_analyze_fixedparams` | `src/backend/parser/analyze.c` | Creates a `ParseState`, calls `transformTopLevelStmt`, and returns a `Query`. |
| 6 | `transformStmt` -> `transformSelectStmt` | `src/backend/parser/analyze.c` | Dispatches `T_SelectStmt` without set operations or `VALUES` lists to `transformSelectStmt`. |
| 7 | `transformSelectStmt` | `src/backend/parser/analyze.c` | Builds a `CMD_SELECT` `Query`, transforms `FROM`, target list, `WHERE`, grouping, sorting, and related clauses. |
| 8 | `pg_rewrite_query` | `src/backend/tcop/postgres.c` | For non-utility queries, calls `QueryRewrite`. |
| 9 | `QueryRewrite` | `src/backend/rewrite/rewriteHandler.c` | Applies the rewrite system and may return zero, one, or many `Query` nodes. |
| 10 | `pg_plan_queries` | `src/backend/tcop/postgres.c` | Loops over rewritten queries and calls `pg_plan_query` for non-utility queries. |
| 11 | `pg_plan_query` | `src/backend/tcop/postgres.c` | Calls the optimizer through `planner`. |
| 12 | `planner` -> `standard_planner` | `src/backend/optimizer/plan/planner.c` | Hook-aware planner entry point and standard implementation. |
| 13 | `subquery_planner` | `src/backend/optimizer/plan/planner.c` | Plans the query level and records path choices in planner structures. |
| 14 | `exec_simple_query` | `src/backend/tcop/postgres.c` | Creates an unnamed portal, calls `PortalDefineQuery`, `PortalStart`, then `PortalRun`. |
| 15 | `ChoosePortalStrategy` | `src/backend/tcop/pquery.c` | A single `CMD_SELECT` without modifying CTEs becomes `PORTAL_ONE_SELECT`. |
| 16 | `PortalStart` | `src/backend/tcop/pquery.c` | For `PORTAL_ONE_SELECT`, pushes a snapshot, creates a `QueryDesc`, and calls `ExecutorStart`. |
| 17 | `ExecutorStart` -> `standard_ExecutorStart` | `src/backend/executor/execMain.c` | Initializes executor state and the plan state tree. |
| 18 | `PortalRun` -> `PortalRunSelect` | `src/backend/tcop/pquery.c` | Fetches rows from the one-select portal. |
| 19 | `ExecutorRun` -> `standard_ExecutorRun` | `src/backend/executor/execMain.c` | Starts the destination receiver and calls `ExecutePlan` unless direction is `NoMovement`. |
| 20 | `ExecutePlan` | `src/backend/executor/execMain.c` | Loops on `ExecProcNode`, sends tuples to the receiver, and increments `es_processed` for `CMD_SELECT`. |
| 21 | `ExecProcNode` | `src/include/executor/executor.h` | Calls the current plan state's `ExecProcNode` method, rescanning first if parameters changed. |
| 22 | `ExecSeqScan` / variants | `src/backend/executor/nodeSeqscan.c` | Example scan node when the plan is a sequential scan; reads tuples through the table access method. |

## Key Data Structures

- `RawStmt` - raw parser output processed by analyzer entry points.
- [[shared/concepts/query-tree|Query]] - analyzer and rewriter representation.
- [[shared/concepts/planned-statement|PlannedStmt]] - planner output consumed by portal/executor code.
- [[shared/concepts/portal|Portal]] - execution wrapper used by simple query processing.
- [[shared/concepts/querydesc|QueryDesc]] - executor descriptor created by `PortalStart`.
- [[shared/concepts/executor-state|EState]] - executor state created by `standard_ExecutorStart`.
- [[shared/concepts/plan-and-planstate|Plan / PlanState]] - planner tree and executor state tree.
- [[shared/concepts/tuple-table-slot|TupleTableSlot]] - tuple container returned by executor nodes.

## Cross-Links

- [[v18/subsystems/parser]]
- [[v18/subsystems/analyzer]]
- [[v18/subsystems/rewriter]]
- [[v18/subsystems/planner]]
- [[v18/subsystems/executor]]

## Source References

- `raw/postgres-18/src/backend/tcop/postgres.c:exec_simple_query`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_parse_query`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_analyze_and_rewrite_fixedparams`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_rewrite_query`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_plan_query`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_plan_queries`
- `raw/postgres-18/src/backend/parser/parser.c:raw_parser`
- `raw/postgres-18/src/backend/parser/analyze.c:transformStmt`
- `raw/postgres-18/src/backend/parser/analyze.c:transformSelectStmt`
- `raw/postgres-18/src/backend/rewrite/rewriteHandler.c:QueryRewrite`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:planner`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:standard_planner`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:subquery_planner`
- `raw/postgres-18/src/backend/tcop/pquery.c:ChoosePortalStrategy`
- `raw/postgres-18/src/backend/tcop/pquery.c:PortalStart`
- `raw/postgres-18/src/backend/tcop/pquery.c:PortalRun`
- `raw/postgres-18/src/backend/tcop/pquery.c:PortalRunSelect`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorStart`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutorRun`
- `raw/postgres-18/src/backend/executor/execMain.c:ExecutePlan`
- `raw/postgres-18/src/include/executor/executor.h:ExecProcNode`
- `raw/postgres-18/src/backend/executor/nodeSeqscan.c:ExecSeqScan`

## Open Questions

- Which exact planner functions produce the first `SeqScan`, `IndexScan`, or `BitmapHeapScan` path for this example?
- How should extended-protocol execution be documented relative to this simple-protocol path?
