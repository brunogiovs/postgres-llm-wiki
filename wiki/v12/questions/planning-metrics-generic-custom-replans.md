---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Planning metrics and generic/custom replanning visibility (unverified)

## Question

In PostgreSQL 12, what planning metrics are available, and how can you tell how many queries are getting replanned or switching between generic and custom plans?

## Answer

Assumption: "PostgreSQL 12" means the local source checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`.

Short answer: PG 12 does not expose a built-in SQL counter for "this prepared statement used N generic plans and M custom plans" or "this query switched from generic to custom." You can sample a prepared statement with `EXPLAIN EXECUTE` to see which kind of plan is being used, and you can measure planning time per sample, but exact generic/custom transition counts require external log sampling or code-level instrumentation around the plan-cache decision point.

The core reason is visible in the plan-cache state. `CachedPlanSource` stores one generic-plan link, `generic_cost`, `total_custom_cost`, and `num_custom_plans`; there is no `num_generic_plans` field in the PG 12 structure [[raw/postgres-12/src/include/utils/plancache.h#CachedPlanSource|plancache.h#CachedPlanSource]]. `GetCachedPlan()` keeps the generic/custom choice in a local `customplan` variable, uses `choose_custom_plan()` to decide, builds or reuses a generic plan through `CheckCachedPlan()`, and increments `num_custom_plans` only when it builds a custom plan [[raw/postgres-12/src/backend/utils/cache/plancache.c#GetCachedPlan|plancache.c#GetCachedPlan]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#choose_custom_plan|plancache.c#choose_custom_plan]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#CheckCachedPlan|plancache.c#CheckCachedPlan]].

## Available Metrics

| Surface | What it tells you in PG 12 | What it does not tell you |
|---|---|---|
| `EXPLAIN` / `EXPLAIN ANALYZE` | Plan shape, estimated costs, and, when summary output has a planning duration, `Planning Time`; `EXPLAIN ANALYZE` also reports execution timing when requested [[raw/postgres-12/doc/src/sgml/ref/explain.sgml#sql-explain|explain.sgml#EXPLAIN]], [[raw/postgres-12/src/backend/commands/explain.c#ExplainOnePlan|explain.c#ExplainOnePlan]]. | No cumulative counter. A single `EXPLAIN` sample does not tell you how many prior executions used generic or custom planning. |
| `EXPLAIN EXECUTE prepared_name(...)` | The documented way to distinguish plan type for one prepared-statement execution: generic output contains `$n` parameter symbols, while custom output has supplied values substituted [[raw/postgres-12/doc/src/sgml/ref/prepare.sgml#sql-prepare-notes|prepare.sgml#sql-prepare-notes]]. `ExplainExecuteQuery()` times the `GetCachedPlan()` call and passes that duration to `ExplainOnePlan()` [[raw/postgres-12/src/backend/commands/prepare.c#ExplainExecuteQuery|prepare.c#ExplainExecuteQuery]]. | Sampling only. It observes the plan chosen for that execution, not a history counter. |
| `pg_prepared_statements` | Current-session prepared statement inventory: name, statement text, prepare time, parameter types, and whether it came from SQL `PREPARE` [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-prepared-statements|catalogs.sgml#pg_prepared_statements]], [[raw/postgres-12/src/backend/commands/prepare.c#pg_prepared_statement|prepare.c#pg_prepared_statement]]. | No generic/custom plan counters and no planning-time columns; the tuple descriptor has exactly five output columns in PG 12 [[raw/postgres-12/src/backend/commands/prepare.c#pg_prepared_statement|prepare.c#pg_prepared_statement]], [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_prepared_statements|system_views.sql#pg_prepared_statements]]. |
| `pg_stat_statements` | Per-normalized-statement execution counters: `calls`, `total_time`, min/max/mean/stddev time, rows, block counters, temp block counters, and block I/O times [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements--1.4.sql#pg_stat_statements|pg_stat_statements--1.4.sql#pg_stat_statements]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#Counters|pg_stat_statements.c#Counters]]. For normal planned statements, the extension stores timing from executor hooks after planning has produced a `QueryDesc` [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pgss_ExecutorStart|pg_stat_statements.c#pgss_ExecutorStart]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pgss_ExecutorEnd|pg_stat_statements.c#pgss_ExecutorEnd]]. | No `plans`, no `total_plan_time`, and no generic/custom plan counters in PG 12's extension SQL definition [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements--1.4.sql#pg_stat_statements|pg_stat_statements--1.4.sql#pg_stat_statements]]. |
| `log_planner_stats` | Server-log `PLANNER STATISTICS` around each `planner()` call through `pg_plan_query()` [[raw/postgres-12/src/backend/tcop/postgres.c#pg_plan_query|postgres.c#pg_plan_query]]. The docs describe the stats-family GUCs as per-query crude profiling similar to `getrusage()` [[raw/postgres-12/doc/src/sgml/config.sgml#runtime-config-statistics-monitor|config.sgml#log_planner_stats]]. | Not grouped by `queryid`, not a generic/custom classifier, and not a durable SQL metric. It is `PGC_SUSET`, so use a superuser session for a short diagnostic run; no restart is needed for session use, while changing config-file defaults requires reload [[raw/postgres-12/src/backend/utils/misc/guc.c#ConfigureNamesBool|guc.c#log-stats-gucs]], [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]]. |
| `auto_explain` | Sampled execution-plan logging. `auto_explain.log_min_duration = 0` logs all sampled plans, and the plan text can be classified using the same `$n` versus substituted-value rule for prepared statements [[raw/postgres-12/doc/src/sgml/auto-explain.sgml#auto-explain|auto-explain.sgml#auto_explain]], [[raw/postgres-12/contrib/auto_explain/auto_explain.c#explain_ExecutorEnd|auto_explain.c#explain_ExecutorEnd]]. | It logs based on executor duration, not a plan-cache counter, and `log_analyze` / per-node timing can add heavy overhead [[raw/postgres-12/doc/src/sgml/auto-explain.sgml#auto-explain|auto-explain.sgml#log_analyze]], [[raw/postgres-12/contrib/auto_explain/auto_explain.c#explain_ExecutorStart|auto_explain.c#explain_ExecutorStart]]. The `auto_explain` GUCs are `PGC_SUSET` after the module is loaded, so use superuser session scope for probes; no restart is needed for `LOAD` plus session `SET`, while preload/config defaults follow normal reload/startup rules [[raw/postgres-12/contrib/auto_explain/auto_explain.c#_PG_init|auto_explain.c#_PG_init]], [[raw/postgres-12/doc/src/sgml/auto-explain.sgml#auto-explain|auto-explain.sgml#auto_explain]]. |

## Generic/Custom Decision Path

`plan_cache_mode` has three PG 12 values: `auto`, `force_generic_plan`, and `force_custom_plan` [[raw/postgres-12/src/include/utils/plancache.h#PlanCacheMode|plancache.h#PlanCacheMode]], and the GUC is `PGC_USERSET` with default `auto` [[raw/postgres-12/src/backend/utils/misc/guc.c#plan_cache_mode|guc.c#plan_cache_mode]]. `PGC_USERSET` means session or transaction `SET` needs no restart or reload; changing config-file or role/database defaults changes later defaults after normal reload/default propagation [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]].

In `auto`, `choose_custom_plan()` chooses custom plans for the first five parameterized executions, then compares the generic plan cost against average custom-plan cost [[raw/postgres-12/src/backend/utils/cache/plancache.c#choose_custom_plan|plancache.c#choose_custom_plan]]. The custom-plan cost includes an estimated planning charge, while generic-plan cost does not [[raw/postgres-12/src/backend/utils/cache/plancache.c#cached_plan_cost|plancache.c#cached_plan_cost]]. The PREPARE docs describe the same rule and explain the tradeoff: generic plans save planning work, but custom plans can exploit parameter values [[raw/postgres-12/doc/src/sgml/ref/prepare.sgml#sql-prepare-notes|prepare.sgml#sql-prepare-notes]].

Replanning also happens for validity reasons, not just because the generic/custom heuristic changes. `GetCachedPlan()` first calls `RevalidateCachedQuery()`, which can re-acquire locks, detect search-path or row-security changes, discard invalid query trees, and redo parse analysis/rewrite when needed [[raw/postgres-12/src/backend/utils/cache/plancache.c#RevalidateCachedQuery|plancache.c#RevalidateCachedQuery]]. A generic plan can be rejected by `CheckCachedPlan()` if no generic plan exists, if it is role-invalid, if invalidation arrives while acquiring executor locks, or if a transient plan's `TransactionXmin` has moved [[raw/postgres-12/src/backend/utils/cache/plancache.c#CheckCachedPlan|plancache.c#CheckCachedPlan]]. Relcache and syscache callbacks can invalidate the query tree plus generic plan, or just the generic plan when the generic plan has extra dependencies [[raw/postgres-12/src/backend/utils/cache/plancache.c#PlanCacheRelCallback|plancache.c#PlanCacheRelCallback]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#PlanCacheObjectCallback|plancache.c#PlanCacheObjectCallback]].

The same cached-plan path is used by SQL `EXECUTE`, extended-query protocol `Bind`, SPI, and PL/pgSQL prepared statements. SQL `EXECUTE` calls `GetCachedPlan()` after evaluating parameters [[raw/postgres-12/src/backend/commands/prepare.c#ExecuteQuery|prepare.c#ExecuteQuery]], the v3 protocol bind path marks parameters `PARAM_FLAG_CONST` and calls `GetCachedPlan()` [[raw/postgres-12/src/backend/tcop/postgres.c#exec_bind_message|postgres.c#exec_bind_message]], SPI execution calls `GetCachedPlan()` for saved plan sources [[raw/postgres-12/src/backend/executor/spi.c#_SPI_execute_plan|spi.c#_SPI_execute_plan]], and PL/pgSQL prepares SQL statements through `SPI_prepare_params()` before later SPI execution [[raw/postgres-12/src/pl/plpgsql/src/pl_exec.c#exec_prepare_plan|pl_exec.c#exec_prepare_plan]], [[raw/postgres-12/src/pl/plpgsql/src/pl_exec.c#exec_stmt_execsql|pl_exec.c#exec_stmt_execsql]].

## How To Tell In Practice

For a single prepared statement, use `EXPLAIN EXECUTE` and classify the plan:

- Generic plan: predicates show `$1`, `$2`, etc.
- Custom plan: predicates show the supplied parameter values.

The PG 12 regression test demonstrates this exact signal. A custom execution of `test_mode_pp(2)` shows `Index Cond: (a = 2)`, while forced or auto-selected generic planning shows `Filter: (a = $1)` [[raw/postgres-12/src/test/regress/sql/plancache.sql#plan_cache_mode|plancache.sql#plan_cache_mode]], [[raw/postgres-12/src/test/regress/expected/plancache.out#plan_cache_mode|plancache.out#plan_cache_mode]].

For a production-safe read-only probe, use short session-scoped timeouts. `statement_timeout`, `lock_timeout`, and `plan_cache_mode` are `PGC_USERSET`, so these `SET LOCAL` statements need no restart or reload [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout|guc.c#statement_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout|guc.c#lock_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#plan_cache_mode|guc.c#plan_cache_mode]]. The docs define `statement_timeout` as a statement-duration limit and `lock_timeout` as a per-lock-wait limit [[raw/postgres-12/doc/src/sgml/config.sgml#guc-statement-timeout|config.sgml#statement_timeout]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-lock-timeout|config.sgml#lock_timeout]].

```sql
BEGIN /* wiki_pg12_plan_probe */;
SET /* wiki_pg12_plan_probe */ LOCAL statement_timeout = '30s';
SET /* wiki_pg12_plan_probe */ LOCAL lock_timeout = '1s';

EXPLAIN /* wiki_pg12_plan_probe */ (ANALYZE, BUFFERS, TIMING OFF, SUMMARY ON)
EXECUTE prepared_statement_name(...);

ROLLBACK /* wiki_pg12_plan_probe */;
```

Use `EXPLAIN ANALYZE` only when executing the statement is safe; the EXPLAIN docs state that `ANALYZE` actually executes the statement, and recommend a transaction plus rollback for statements with side effects [[raw/postgres-12/doc/src/sgml/ref/explain.sgml#sql-explain|explain.sgml#EXPLAIN]]. For DML in production, use plain `EXPLAIN EXECUTE` or run the `ANALYZE` probe on staging with production-like data.

To compare both forced shapes for the same prepared statement:

```sql
BEGIN /* wiki_pg12_plan_shape_compare */;
SET /* wiki_pg12_plan_shape_compare */ LOCAL statement_timeout = '30s';
SET /* wiki_pg12_plan_shape_compare */ LOCAL lock_timeout = '1s';

SET /* wiki_pg12_plan_shape_compare */ LOCAL plan_cache_mode = force_generic_plan;
EXPLAIN /* wiki_pg12_plan_shape_compare */ (COSTS OFF)
EXECUTE prepared_statement_name(...);

SET /* wiki_pg12_plan_shape_compare */ LOCAL plan_cache_mode = force_custom_plan;
EXPLAIN /* wiki_pg12_plan_shape_compare */ (COSTS OFF)
EXECUTE prepared_statement_name(...);

ROLLBACK /* wiki_pg12_plan_shape_compare */;
```

To inventory current-session SQL/protocol prepared statements, the verified PG 12 columns are:

```sql
BEGIN /* wiki_pg12_prepared_inventory */;
SET /* wiki_pg12_prepared_inventory */ LOCAL statement_timeout = '5s';
SET /* wiki_pg12_prepared_inventory */ LOCAL lock_timeout = '500ms';

SELECT /* wiki_pg12_prepared_inventory */
       name,
       statement,
       prepare_time,
       parameter_types,
       from_sql
FROM pg_prepared_statements;

ROLLBACK /* wiki_pg12_prepared_inventory */;
```

This inventory does not include PL/pgSQL's internal saved SPI plans unless they are exposed as SQL/protocol prepared statements, and it does not include generic/custom counts [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-prepared-statements|catalogs.sgml#pg_prepared_statements]], [[raw/postgres-12/src/backend/commands/prepare.c#pg_prepared_statement|prepare.c#pg_prepared_statement]], [[raw/postgres-12/src/pl/plpgsql/src/pl_exec.c#exec_prepare_plan|pl_exec.c#exec_prepare_plan]].

## Counting Strategy

For exact counts in unmodified PG 12 core: there is no built-in answer. `pg_stat_statements` can rank statements by execution calls and time, but it has no plan-count or planning-time columns in PG 12 [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements--1.4.sql#pg_stat_statements|pg_stat_statements--1.4.sql#pg_stat_statements]]. `pg_prepared_statements` can list current-session prepared statements, but its PG 12 output has only five columns and no counters [[raw/postgres-12/src/backend/commands/prepare.c#pg_prepared_statement|prepare.c#pg_prepared_statement]].

For approximate production visibility, pick one of these:

1. Sample representative prepared statements with `EXPLAIN EXECUTE` and classify `$n` versus substituted constants. This gives plan type and `Planning Time` for each sample, not total fleet counts [[raw/postgres-12/doc/src/sgml/ref/prepare.sgml#sql-prepare-notes|prepare.sgml#sql-prepare-notes]], [[raw/postgres-12/src/backend/commands/explain.c#ExplainOnePlan|explain.c#ExplainOnePlan]].
2. Use `auto_explain` in a narrowly scoped superuser session or sampled preload configuration to log plans, then classify the logged plan text. Keep `auto_explain.log_analyze` and `auto_explain.log_timing` off unless you need executor detail, because PG 12 documents timing overhead and the module installs per-node instrumentation when analyze is enabled [[raw/postgres-12/doc/src/sgml/auto-explain.sgml#auto-explain|auto-explain.sgml#log_analyze]], [[raw/postgres-12/contrib/auto_explain/auto_explain.c#explain_ExecutorStart|auto_explain.c#explain_ExecutorStart]].
3. Use `log_planner_stats` only for short superuser diagnostics when you need to count planner invocations from logs. It can prove planning is occurring, but it does not identify generic/custom choice or give a queryid-level aggregate [[raw/postgres-12/src/backend/tcop/postgres.c#pg_plan_query|postgres.c#pg_plan_query]], [[raw/postgres-12/doc/src/sgml/config.sgml#runtime-config-statistics-monitor|config.sgml#log_planner_stats]].
4. If exact per-statement generic/custom counts are mandatory, instrument the plan-cache code path or use a custom build/extension strategy that records the result of `choose_custom_plan()` in `GetCachedPlan()`. In PG 12 that decision is otherwise local to `GetCachedPlan()` and is not copied into a public statistics view [[raw/postgres-12/src/backend/utils/cache/plancache.c#GetCachedPlan|plancache.c#GetCachedPlan]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#choose_custom_plan|plancache.c#choose_custom_plan]].

## Context Reviewed

- Navigation/bookkeeping: `wiki/versions.md`, `wiki/index.md`, last 20 log entries through `scripts/recent_log --limit 20`, `wiki/v12/index.md`, and the nearby v12 `plan_cache_mode` and inheritance question pages.
- Source scope: every source lookup used `scripts/source_graph_query --version 12 ...` against `raw/postgres-12/`; graph commands were used only for orientation.
- Primary plan-cache sources: `src/include/utils/plancache.h`, `src/backend/utils/cache/plancache.c`, and `src/backend/utils/misc/guc.c`, covering `PlanCacheMode`, `CachedPlanSource`, `choose_custom_plan()`, `cached_plan_cost()`, `GetCachedPlan()`, `CheckCachedPlan()`, `RevalidateCachedQuery()`, `PlanCacheRelCallback()`, `PlanCacheObjectCallback()`, and `ResetPlanCache()`.
- Metrics and exposure sources: `src/backend/commands/explain.c`, `src/backend/commands/prepare.c`, `src/backend/catalog/system_views.sql`, `contrib/pg_stat_statements/pg_stat_statements.c`, `contrib/pg_stat_statements/pg_stat_statements--1.4.sql`, `src/backend/tcop/postgres.c`, and `contrib/auto_explain/auto_explain.c`.
- Caller/callee boundaries: SQL `EXECUTE`, `EXPLAIN EXECUTE`, extended-query protocol bind, SPI, and PL/pgSQL preparation/execution paths.
- Documentation and tests: `doc/src/sgml/ref/prepare.sgml`, `doc/src/sgml/ref/explain.sgml`, `doc/src/sgml/catalogs.sgml`, `doc/src/sgml/config.sgml`, `doc/src/sgml/pgstatstatements.sgml`, `doc/src/sgml/auto-explain.sgml`, `src/test/regress/sql/plancache.sql`, and `src/test/regress/expected/plancache.out`.
- Include/history checks: direct includes for `plancache.c`, reverse include users of `utils/plancache.h`, graph explanation for `GetCachedPlan()`, graph path from protocol bind to `GetCachedPlan()`, and `plancache.c` history including `f7cb2842bf Add plan_cache_mode setting`.

## Evidence Map

| Claim | Evidence |
|---|---|
| PG 12 does not expose generic/custom counters in `pg_prepared_statements`. | [[raw/postgres-12/src/backend/commands/prepare.c#pg_prepared_statement|prepare.c#pg_prepared_statement]], [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_prepared_statements|system_views.sql#pg_prepared_statements]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-prepared-statements|catalogs.sgml#pg_prepared_statements]] |
| PG 12 `pg_stat_statements` exposes execution counters/times and block counters, not planning time or plan counts. | [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements--1.4.sql#pg_stat_statements|pg_stat_statements--1.4.sql#pg_stat_statements]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#Counters|pg_stat_statements.c#Counters]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pgss_ExecutorStart|pg_stat_statements.c#pgss_ExecutorStart]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pgss_ExecutorEnd|pg_stat_statements.c#pgss_ExecutorEnd]] |
| `EXPLAIN EXECUTE` distinguishes generic from custom plans by `$n` symbols versus substituted parameter values. | [[raw/postgres-12/doc/src/sgml/ref/prepare.sgml#sql-prepare-notes|prepare.sgml#sql-prepare-notes]], [[raw/postgres-12/src/test/regress/sql/plancache.sql#plan_cache_mode|plancache.sql#plan_cache_mode]], [[raw/postgres-12/src/test/regress/expected/plancache.out#plan_cache_mode|plancache.out#plan_cache_mode]] |
| `EXPLAIN` can report planning time for a sampled execution. | [[raw/postgres-12/src/backend/commands/explain.c#ExplainOnePlan|explain.c#ExplainOnePlan]], [[raw/postgres-12/src/backend/commands/prepare.c#ExplainExecuteQuery|prepare.c#ExplainExecuteQuery]] |
| In `auto`, PG 12 uses five custom plans before comparing generic cost against average custom cost. | [[raw/postgres-12/src/backend/utils/cache/plancache.c#choose_custom_plan|plancache.c#choose_custom_plan]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#cached_plan_cost|plancache.c#cached_plan_cost]], [[raw/postgres-12/doc/src/sgml/ref/prepare.sgml#sql-prepare-notes|prepare.sgml#sql-prepare-notes]] |
| The internal state tracks custom-plan count and costs, but not generic-plan count. | [[raw/postgres-12/src/include/utils/plancache.h#CachedPlanSource|plancache.h#CachedPlanSource]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#GetCachedPlan|plancache.c#GetCachedPlan]] |
| Replanning can be caused by invalidation/search-path/RLS/role/transient-plan checks, not only by the generic/custom heuristic. | [[raw/postgres-12/src/backend/utils/cache/plancache.c#RevalidateCachedQuery|plancache.c#RevalidateCachedQuery]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#CheckCachedPlan|plancache.c#CheckCachedPlan]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#PlanCacheRelCallback|plancache.c#PlanCacheRelCallback]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#PlanCacheObjectCallback|plancache.c#PlanCacheObjectCallback]] |
| SQL `EXECUTE`, protocol bind, SPI, and PL/pgSQL SQL statements can all reach `GetCachedPlan()`. | [[raw/postgres-12/src/backend/commands/prepare.c#ExecuteQuery|prepare.c#ExecuteQuery]], [[raw/postgres-12/src/backend/tcop/postgres.c#exec_bind_message|postgres.c#exec_bind_message]], [[raw/postgres-12/src/backend/executor/spi.c#_SPI_execute_plan|spi.c#_SPI_execute_plan]], [[raw/postgres-12/src/pl/plpgsql/src/pl_exec.c#exec_prepare_plan|pl_exec.c#exec_prepare_plan]], [[raw/postgres-12/src/pl/plpgsql/src/pl_exec.c#exec_stmt_execsql|pl_exec.c#exec_stmt_execsql]] |
| `log_planner_stats` and `auto_explain` are diagnostic/logging tools, not exact generic/custom counters. | [[raw/postgres-12/src/backend/tcop/postgres.c#pg_plan_query|postgres.c#pg_plan_query]], [[raw/postgres-12/doc/src/sgml/config.sgml#runtime-config-statistics-monitor|config.sgml#log_planner_stats]], [[raw/postgres-12/contrib/auto_explain/auto_explain.c#explain_ExecutorEnd|auto_explain.c#explain_ExecutorEnd]], [[raw/postgres-12/doc/src/sgml/auto-explain.sgml#auto-explain|auto-explain.sgml#auto_explain]] |
| Session/transaction probes can use `SET LOCAL` without restart for `plan_cache_mode`, `statement_timeout`, and `lock_timeout`; superuser-only diagnostics use `PGC_SUSET` session scope. | [[raw/postgres-12/src/backend/utils/misc/guc.c#plan_cache_mode|guc.c#plan_cache_mode]], [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout|guc.c#statement_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout|guc.c#lock_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#ConfigureNamesBool|guc.c#log-stats-gucs]], [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]] |

## Open Questions

- The pinned PG 12 source does not provide exact generic/custom execution counters. Exact production counts require external log sampling or custom instrumentation at the `GetCachedPlan()` decision point.
- Sampling can miss low-latency statements or statements executed through paths you did not sample, especially internal PL/pgSQL/SPI plans that are not visible in `pg_prepared_statements`.

## Source References

- Source pin: [[raw/postgres-12/]] at commit `45b88269a353ad93744772791feb6d01bc7e1e42`.
- Plan cache: [[raw/postgres-12/src/include/utils/plancache.h|plancache.h]], [[raw/postgres-12/src/backend/utils/cache/plancache.c|plancache.c]], [[raw/postgres-12/src/backend/utils/misc/guc.c|guc.c]], [[raw/postgres-12/src/include/utils/guc.h|guc.h]].
- Metrics and views: [[raw/postgres-12/src/backend/commands/explain.c|explain.c]], [[raw/postgres-12/src/backend/commands/prepare.c|prepare.c]], [[raw/postgres-12/src/backend/catalog/system_views.sql|system_views.sql]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c|pg_stat_statements.c]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements--1.4.sql|pg_stat_statements--1.4.sql]], [[raw/postgres-12/contrib/auto_explain/auto_explain.c|auto_explain.c]].
- Callers: [[raw/postgres-12/src/backend/tcop/postgres.c|postgres.c]], [[raw/postgres-12/src/backend/executor/spi.c|spi.c]], [[raw/postgres-12/src/pl/plpgsql/src/pl_exec.c|pl_exec.c]].
- Documentation and tests: [[raw/postgres-12/doc/src/sgml/ref/prepare.sgml|prepare.sgml]], [[raw/postgres-12/doc/src/sgml/ref/explain.sgml|explain.sgml]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml|catalogs.sgml]], [[raw/postgres-12/doc/src/sgml/config.sgml|config.sgml]], [[raw/postgres-12/doc/src/sgml/pgstatstatements.sgml|pgstatstatements.sgml]], [[raw/postgres-12/doc/src/sgml/auto-explain.sgml|auto-explain.sgml]], [[raw/postgres-12/src/test/regress/sql/plancache.sql|plancache.sql]], [[raw/postgres-12/src/test/regress/expected/plancache.out|plancache.out]].
