---
type: question
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: false
verified_by_agent: not yet
---

# Query Plan Interpretation Inputs

## Question

For a given SQL statement and an `EXPLAIN`, what information should be collected from PostgreSQL 18 to strongly interpret the plan, explain why the planner made its choices, and estimate production impact?

## Short Answer

Assume PostgreSQL 18, the primary version in [[versions]]. A strong plan interpretation needs a diagnostic packet, not just the visible plan tree:

1. the exact SQL, parameter values and types, and whether the plan is generic or custom;
2. `EXPLAIN` output with planner metadata and, when safe, execution instrumentation;
3. session, role, search path, row-security, and planner-related GUCs;
4. relation, column, index, partition, constraint, function, operator, collation, FDW, and trigger metadata for every referenced object;
5. table/index size estimates, per-column statistics, extended statistics, and statistics freshness;
6. workload history, object access history, table churn, lock/wait state, and cumulative query cost if the question includes production impact.

`standard_planner` selects a best `Path` and turns it into a `Plan`; `query_planner` builds base relation and join alternatives, while `make_one_rel` computes base sizes, generates base access paths, and generates join paths. Those facts make the packet above the minimum useful evidence for explaining both the visible plan and the paths that lost. Citations: `raw/postgres-18/src/backend/optimizer/plan/planner.c:standard_planner`, `raw/postgres-18/src/backend/optimizer/plan/planmain.c:query_planner`, `raw/postgres-18/src/backend/optimizer/path/allpaths.c:make_one_rel`.

## Plan And Execution Evidence

Collect the original SQL exactly as the application sent it, including comments only if they are part of the submitted text. For parameterized SQL, collect parameter values, parameter types, prepared-statement name, and whether the observed plan came from plain `EXPLAIN`, `EXPLAIN EXECUTE`, a cached prepared statement, or production logging. The plan cache can choose a generic plan or a custom parameter-value-specific plan; `BuildCachedPlan` treats `NULL` `boundParams` as generic and non-`NULL` actual parameter values as custom, and `choose_custom_plan` contains the policy controlled by `plan_cache_mode` and accumulated generic/custom costs. Citations: `raw/postgres-18/src/backend/utils/cache/plancache.c:BuildCachedPlan`, `raw/postgres-18/src/backend/utils/cache/plancache.c:choose_custom_plan`, `raw/postgres-18/src/include/utils/plancache.h:CachedPlanSource`.

Prefer machine-readable plans:

```sql
EXPLAIN (FORMAT JSON, VERBOSE, SETTINGS, COSTS, SUMMARY)
<sql>;
```

When it is safe to execute the SQL in the target environment, collect:

```sql
EXPLAIN (ANALYZE, BUFFERS, WAL, VERBOSE, SETTINGS, SUMMARY, FORMAT JSON)
<sql>;
```

`EXPLAIN` parses options into `ExplainState`; `standard_ExplainOneQuery` plans through `pg_plan_query`; and `ExplainOnePlan` executes the plan only when `ANALYZE` is set. With `ANALYZE`, instrumentation can include actual rows, loops, node timing, buffer usage, WAL usage, trigger timing, JIT summary, planning time, and execution time depending on options and server settings. Citations: `raw/postgres-18/src/backend/commands/explain_state.c:ParseExplainOptionList`, `raw/postgres-18/src/backend/commands/explain.c:standard_ExplainOneQuery`, `raw/postgres-18/src/backend/commands/explain.c:ExplainOnePlan`, `raw/postgres-18/src/backend/commands/explain.c:show_buffer_usage`, `raw/postgres-18/src/backend/commands/explain.c:show_wal_usage`, `raw/postgres-18/src/backend/commands/explain.c:ExplainPrintTriggers`, `raw/postgres-18/src/backend/commands/explain.c:ExplainPrintJITSummary`.

For production statements, also capture `queryid` when available. `EXPLAIN VERBOSE` can print `Query Identifier` when query ID computation produced one, and `pg_stat_statements` stores counters keyed by query ID. Citations: `raw/postgres-18/src/backend/commands/explain.c:ExplainPrintPlan`, `raw/postgres-18/src/include/nodes/parsenodes.h:Query`, `raw/postgres-18/contrib/pg_stat_statements/pg_stat_statements.c:pgssEntry`.

## Session And Planner Settings

Collect the session context that can affect planning or object visibility:

```sql
SELECT
  version(),
  current_database(),
  current_user,
  session_user,
  current_setting('search_path') AS search_path,
  current_setting('row_security') AS row_security,
  current_setting('plan_cache_mode') AS plan_cache_mode;

SELECT name, setting, unit, source, boot_val, reset_val, context
FROM pg_settings
WHERE name IN (
  'search_path',
  'row_security',
  'plan_cache_mode',
  'default_statistics_target',
  'from_collapse_limit',
  'join_collapse_limit',
  'geqo',
  'geqo_threshold',
  'work_mem',
  'hash_mem_multiplier',
  'effective_cache_size',
  'effective_io_concurrency',
  'seq_page_cost',
  'random_page_cost',
  'cpu_tuple_cost',
  'cpu_index_tuple_cost',
  'cpu_operator_cost',
  'parallel_setup_cost',
  'parallel_tuple_cost',
  'max_parallel_workers_per_gather',
  'min_parallel_table_scan_size',
  'min_parallel_index_scan_size',
  'parallel_leader_participation',
  'jit',
  'jit_above_cost',
  'jit_inline_above_cost',
  'jit_optimize_above_cost',
  'track_io_timing'
)
OR name LIKE 'enable_%'
ORDER BY name;
```

`EXPLAIN (SETTINGS)` prints only modified GUCs marked `GUC_EXPLAIN` and visible to the current user, so a full `pg_settings` capture is still useful when comparing environments. Planner method switches, cost constants, collapse limits, GEQO, work memory, parallelism, JIT thresholds, and cache-size assumptions are registered as planner-relevant GUCs. Citations: `raw/postgres-18/src/backend/commands/explain.c:ExplainPrintSettings`, `raw/postgres-18/src/backend/utils/misc/guc.c:get_explain_guc_options`, `raw/postgres-18/src/backend/utils/misc/guc_tables.c:ConfigureNamesBool`, `raw/postgres-18/src/backend/utils/misc/guc_tables.c:ConfigureNamesInt`, `raw/postgres-18/src/backend/utils/misc/guc_tables.c:ConfigureNamesReal`.

The cost model uses `seq_page_cost`, `random_page_cost`, CPU cost constants, `parallel_*` costs, and `effective_cache_size`; it also allows per-tablespace overrides of sequential and random page costs. Sort, materialize, bitmap, and hash-related costing use `work_mem` or hash memory sizing, so memory settings can explain sort spill risk, hash batching risk, and bitmap precision changes. Citations: `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_seqscan`, `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_index`, `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_tuplesort`, `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_material`, `raw/postgres-18/src/backend/optimizer/path/costsize.c:initial_cost_hashjoin`, `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_bitmap_heap_scan`.

## Object Metadata

For each relation, view, materialized view, partition, foreign table, CTE-backed relation, function, and operator visible in `EXPLAIN VERBOSE`, collect object identity and definition:

```sql
SELECT c.oid::regclass AS rel, n.nspname, c.relkind, c.relpersistence,
       c.reltablespace, c.relpages, c.reltuples, c.relallvisible,
       c.reloptions, c.relrowsecurity, c.relforcerowsecurity,
       c.relispartition, c.relpartbound
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.oid = ANY ($1::regclass[]);

SELECT attrelid::regclass AS rel, attnum, attname, atttypid::regtype,
       atttypmod, attnotnull, attcollation::regcollation,
       attstorage, attcompression, attstattarget
FROM pg_attribute
WHERE attrelid = ANY ($1::regclass[]) AND attnum > 0 AND NOT attisdropped
ORDER BY attrelid::regclass::text, attnum;
```

The planner reads relation descriptors and catalog data in `get_relation_info`: relation tablespace, columns, NOT NULL columns, relation size estimates, `parallel_workers` reloption, index list, foreign-table FDW routine, foreign keys, table-AM capabilities, and partitioning information. Citations: `raw/postgres-18/src/backend/optimizer/util/plancat.c:get_relation_info`, `raw/postgres-18/src/include/catalog/pg_class.h`, `raw/postgres-18/src/include/catalog/pg_attribute.h`.

For indexes:

```sql
SELECT
  i.indrelid::regclass AS table_name,
  i.indexrelid::regclass AS index_name,
  am.amname,
  pg_get_indexdef(i.indexrelid) AS indexdef,
  i.indisunique, i.indnullsnotdistinct, i.indisvalid, i.indcheckxmin,
  i.indisready, i.indisreplident,
  pg_get_expr(i.indpred, i.indrelid) AS predicate,
  pg_get_expr(i.indexprs, i.indrelid) AS expressions,
  ci.relpages AS index_relpages,
  ci.reltuples AS index_reltuples,
  ci.reloptions AS index_reloptions
FROM pg_index i
JOIN pg_class ci ON ci.oid = i.indexrelid
JOIN pg_am am ON am.oid = ci.relam
WHERE i.indrelid = ANY ($1::regclass[])
ORDER BY i.indrelid::regclass::text, i.indexrelid::regclass::text;
```

Index path interpretation needs index validity, predicate, expression columns, opclasses/collations, ordering flags, access-method capabilities, page/tuple estimates, and whether the access method supplies a cost estimator. `get_relation_info` builds `IndexOptInfo` from `pg_index`, relcache, AM callbacks, index expressions, partial-index predicates, uniqueness, and index size estimates; `cost_index` then asks the AM-specific estimator for index cost, selectivity, correlation, and page count. Citations: `raw/postgres-18/src/backend/optimizer/util/plancat.c:get_relation_info`, `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_index`, `raw/postgres-18/src/include/catalog/pg_index.h`.

For constraints and partitioning:

```sql
SELECT conrelid::regclass AS rel, contype, conname,
       pg_get_constraintdef(oid, true) AS definition
FROM pg_constraint
WHERE conrelid = ANY ($1::regclass[])
ORDER BY conrelid::regclass::text, contype, conname;

SELECT inhparent::regclass AS parent, inhrelid::regclass AS child, inhseqno
FROM pg_inherits
WHERE inhparent = ANY ($1::regclass[]) OR inhrelid = ANY ($1::regclass[])
ORDER BY parent::text, inhseqno;
```

Constraint and partition metadata explain why a relation or partition may vanish from a plan. `set_rel_size` can replace a relation with a dummy path after constraint exclusion, and `create_append_plan` / `create_merge_append_plan` can attach runtime partition pruning information when useful quals exist and `enable_partition_pruning` is enabled. Citations: `raw/postgres-18/src/backend/optimizer/path/allpaths.c:set_rel_size`, `raw/postgres-18/src/backend/optimizer/util/plancat.c:relation_excluded_by_constraints`, `raw/postgres-18/src/backend/optimizer/plan/createplan.c:create_append_plan`, `raw/postgres-18/src/backend/optimizer/plan/createplan.c:create_merge_append_plan`.

For functions and operators used in filters, joins, projections, indexes, generated columns, policies, or constraints, collect `pg_proc` rows and definitions:

```sql
SELECT p.oid::regprocedure, n.nspname, p.procost, p.prorows, p.prosupport::regprocedure,
       p.provolatile, p.proparallel, p.proleakproof, p.proisstrict, p.proretset
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE p.oid = ANY ($1::regprocedure[]);
```

Function metadata can affect selectivity, expression simplification, cost, set-returning row estimates, and parallel safety. PostgreSQL consults function support hooks for selectivity/cost/rows when present, otherwise falls back to defaults or `procost` / `prorows`; volatility controls which functions can be folded for planning estimates; `proparallel` controls parallel safety checks. Citations: `raw/postgres-18/src/backend/optimizer/util/plancat.c:function_selectivity`, `raw/postgres-18/src/backend/optimizer/util/plancat.c:add_function_cost`, `raw/postgres-18/src/backend/optimizer/util/plancat.c:get_function_rows`, `raw/postgres-18/src/backend/optimizer/util/clauses.c:ece_function_is_safe`, `raw/postgres-18/src/backend/optimizer/util/clauses.c:max_parallel_hazard_test`, `raw/postgres-18/src/include/catalog/pg_proc.h`.

## Statistics And Freshness

Collect per-column statistics for all join, filter, group, order, distinct, and projected wide columns:

```sql
SELECT *
FROM pg_stats
WHERE (schemaname, tablename) IN (($schema, $table))
ORDER BY schemaname, tablename, attname;

SELECT *
FROM pg_stats_ext
WHERE (schemaname, tablename) IN (($schema, $table))
ORDER BY schemaname, tablename, statistics_name;
```

For privileged diagnosis, `pg_statistic` and `pg_statistic_ext_data` expose lower-level data. The planner reads `pg_statistic` through `STATRELATTINH`, uses fields such as null fraction, average width, ndistinct, MCVs, histograms, and correlation, and uses extended statistics first for clause lists when matching multicolumn objects exist. Citations: `raw/postgres-18/src/backend/utils/adt/selfuncs.c:examine_variable`, `raw/postgres-18/src/backend/utils/adt/selfuncs.c:examine_simple_variable`, `raw/postgres-18/src/backend/utils/adt/selfuncs.c:get_variable_numdistinct`, `raw/postgres-18/src/backend/optimizer/path/clausesel.c:clauselist_selectivity_ext`, `raw/postgres-18/src/include/catalog/pg_statistic.h`.

Extended statistics metadata comes from `pg_statistic_ext`; built data comes from `pg_statistic_ext_data`; built kinds include ndistinct, dependencies, MCV, and expression statistics. Citations: `raw/postgres-18/src/backend/optimizer/util/plancat.c:get_relation_statistics`, `raw/postgres-18/src/backend/optimizer/util/plancat.c:get_relation_statistics_worker`, `raw/postgres-18/src/include/catalog/pg_statistic_ext.h`, `raw/postgres-18/src/include/catalog/pg_statistic_ext_data.h`.

Collect statistics freshness and churn:

```sql
SELECT relid::regclass, seq_scan, idx_scan, n_live_tup, n_dead_tup,
       n_mod_since_analyze, n_ins_since_vacuum,
       last_vacuum, last_autovacuum, last_analyze, last_autoanalyze,
       vacuum_count, autovacuum_count, analyze_count, autoanalyze_count
FROM pg_stat_all_tables
WHERE relid = ANY ($1::regclass[]);
```

Freshness matters because relation size estimates come from current blocks plus previous density and `pg_class` tuple/page/all-visible counts; stale statistics can therefore explain row-estimate errors and index-only-scan optimism or pessimism. Citations: `raw/postgres-18/src/backend/optimizer/util/plancat.c:estimate_rel_size`, `raw/postgres-18/src/include/catalog/pg_class.h`, `raw/postgres-18/src/backend/catalog/system_views.sql:pg_stat_all_tables`.

## Access History And Production Impact

To estimate production impact, collect frequency, latency distribution, rows, buffer use, temporary I/O, and WAL by normalized statement when `pg_stat_statements` is installed:

```sql
SELECT userid::regrole, dbid, queryid, plans, total_plan_time,
       calls, total_exec_time, rows,
       shared_blks_hit, shared_blks_read, shared_blks_dirtied, shared_blks_written,
       local_blks_hit, local_blks_read, temp_blks_read, temp_blks_written,
       wal_records, wal_fpi, wal_bytes,
       query
FROM pg_stat_statements
WHERE queryid = $queryid;
```

`pg_stat_statements` records planning and execution calls, total times, rows, shared/local/temp block counters, and WAL counters when configured to track the relevant data. Citations: `raw/postgres-18/contrib/pg_stat_statements/pg_stat_statements.c:pgssEntry`, `raw/postgres-18/contrib/pg_stat_statements/pg_stat_statements.c:pgss_store`, `raw/postgres-18/contrib/pg_stat_statements/pg_stat_statements--1.11--1.12.sql`.

Collect object-level access history:

```sql
SELECT relid::regclass, indexrelid::regclass, idx_scan, last_idx_scan,
       idx_tup_read, idx_tup_fetch
FROM pg_stat_all_indexes
WHERE relid = ANY ($1::regclass[])
ORDER BY relid::regclass::text, indexrelid::regclass::text;
```

This does not explain the current plan by itself, but it shows whether a proposed index or chosen index is used in production and whether table access patterns are mostly sequential or index-driven. The view is backed by per-relation and per-index scan counters. Citation: `raw/postgres-18/src/backend/catalog/system_views.sql:pg_stat_all_indexes`.

Collect relation sizes to put costs and buffer counts into storage scale:

```sql
SELECT c.oid::regclass AS rel,
       pg_table_size(c.oid) AS table_bytes,
       pg_indexes_size(c.oid) AS indexes_bytes,
       pg_total_relation_size(c.oid) AS total_bytes
FROM pg_class c
WHERE c.oid = ANY ($1::regclass[]);
```

The planner estimates from page counts and costs, while production risk is often expressed in bytes, cache residency, temp files, and WAL volume. `pg_table_size`, `pg_indexes_size`, and `pg_total_relation_size` are the built-in size functions for this translation. Citations: `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_seqscan`, `raw/postgres-18/src/backend/utils/adt/dbsize.c:pg_table_size`, `raw/postgres-18/src/backend/utils/adt/dbsize.c:pg_indexes_size`, `raw/postgres-18/src/backend/utils/adt/dbsize.c:pg_total_relation_size`.

For live-production impact, collect blockers and active waits near the time of execution:

```sql
SELECT pid, usename, application_name, state, wait_event_type, wait_event,
       backend_xid, backend_xmin, query_id, query_start, xact_start,
       pg_blocking_pids(pid) AS blocking_pids
FROM pg_stat_activity
WHERE datname = current_database();

SELECT *
FROM pg_locks
WHERE NOT granted OR pid = ANY ($1::int[]);
```

This is outside the planner's cost model, but it is essential for production interpretation: a good plan can still hurt if it waits on locks, holds old snapshots, writes WAL at a high rate, or competes with critical workload. `pg_stat_activity` exposes wait events and transaction horizons, `pg_locks` exposes lock state, and `pg_blocking_pids` identifies blockers. Citations: `raw/postgres-18/src/backend/catalog/system_views.sql:pg_stat_activity`, `raw/postgres-18/src/backend/catalog/system_views.sql:pg_locks`, `raw/postgres-18/src/backend/utils/adt/lockfuncs.c:pg_blocking_pids`.

## Row Security, Views, And Policy Context

Collect RLS and security-barrier context when a referenced relation is a table with policies or a view:

```sql
SELECT c.oid::regclass AS rel, c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c
WHERE c.oid = ANY ($1::regclass[]);

SELECT polrelid::regclass AS rel, polname, polcmd, polpermissive,
       polroles, pg_get_expr(polqual, polrelid) AS using_expr,
       pg_get_expr(polwithcheck, polrelid) AS check_expr
FROM pg_policy
WHERE polrelid = ANY ($1::regclass[]);
```

RLS policies and security-barrier views are rewritten into `securityQuals`, and those quals are later processed by the planner. They can change both visible rows and which predicates may be pushed down or reordered. Citations: `raw/postgres-18/src/backend/rewrite/rowsecurity.c:get_row_security_policies`, `raw/postgres-18/src/backend/rewrite/rewriteHandler.c:fireRIRrules`, `raw/postgres-18/src/backend/optimizer/plan/initsplan.c:process_security_barrier_quals`, `raw/postgres-18/src/include/nodes/parsenodes.h:RangeTblEntry`.

## DML-Specific Impact

For `INSERT`, `UPDATE`, `DELETE`, and `MERGE`, also collect:

- target table indexes, because they add write maintenance even when they are not scan paths;
- triggers and foreign keys, because `EXPLAIN ANALYZE` can report trigger timing and foreign-key checks are implemented through RI triggers;
- WAL counters from `EXPLAIN (ANALYZE, WAL)` or `pg_stat_statements`;
- table churn and dead tuple counters from `pg_stat_all_tables`.

The executor instrumentation has per-query WAL counters, and `ExplainOnePlan` enables WAL instrumentation when requested. Trigger timing is printed after execution when `ANALYZE` is active. Foreign-key check and action triggers are created through the table DDL path and executed through the RI trigger functions. Citations: `raw/postgres-18/src/include/executor/instrument.h:WalUsage`, `raw/postgres-18/src/backend/commands/explain.c:ExplainOnePlan`, `raw/postgres-18/src/backend/commands/explain.c:ExplainPrintTriggers`, `raw/postgres-18/src/backend/commands/tablecmds.c:CreateFKCheckTrigger`, `raw/postgres-18/src/backend/commands/tablecmds.c:createForeignKeyActionTriggers`, `raw/postgres-18/src/backend/utils/adt/ri_triggers.c:RI_FKey_check`.

## Production Capture

When running `EXPLAIN ANALYZE` manually would be risky or unrepresentative, use production telemetry:

- `pg_stat_statements` for cumulative frequency, latency, rows, I/O, and WAL.
- `auto_explain` for sampled or thresholded real plans, including parameters, query text, settings, buffers, WAL, and nested statements when configured.
- application-side sampling for exact bind values and execution context.

`auto_explain` logs after executor end when duration exceeds `auto_explain.log_min_duration`; it can include `ANALYZE`, `VERBOSE`, `BUFFERS`, `WAL`, `SETTINGS`, query text, parameters, triggers, and JIT summary depending on its GUCs. Citations: `raw/postgres-18/contrib/auto_explain/auto_explain.c`, `raw/postgres-18/contrib/auto_explain/auto_explain.c:explain_ExecutorEnd`.

## Interpretation Checklist

Use the packet to answer these questions:

1. Are estimated rows wrong? Compare plan rows to actual rows, then inspect `pg_statistic`, extended stats, predicates, correlation, null fractions, MCVs, histograms, and freshness.
2. Was an access path unavailable? Check index validity, partial predicate implication, opclass/collation/operator compatibility, expression matching, partition pruning, RLS/security quals, and disabled `enable_*` GUCs.
3. Was a cheaper-looking path rejected because costs differ? Check page-cost settings, tablespace overrides, `effective_cache_size`, correlation, all-visible fraction, `work_mem`, hash memory, and parallel/JIT thresholds.
4. Did generic planning hide parameter selectivity? Compare `plan_cache_mode`, `EXPLAIN EXECUTE`, bind values, custom/generic plan counters, and `pg_stat_statements` distribution.
5. Is production impact high even if the plan is reasonable? Check calls per interval, p95/p99 outside the database if available, shared reads, temp I/O, WAL bytes, locks/waits, table churn, and maintenance windows.

## Source References

- `raw/postgres-18/src/backend/commands/explain_state.c:ParseExplainOptionList`
- `raw/postgres-18/src/backend/commands/explain.c:standard_ExplainOneQuery`
- `raw/postgres-18/src/backend/commands/explain.c:ExplainOnePlan`
- `raw/postgres-18/src/backend/commands/explain.c:ExplainPrintPlan`
- `raw/postgres-18/src/backend/commands/explain.c:ExplainPrintSettings`
- `raw/postgres-18/src/backend/commands/explain.c:ExplainPrintTriggers`
- `raw/postgres-18/src/backend/commands/explain.c:ExplainPrintJITSummary`
- `raw/postgres-18/src/backend/commands/explain.c:show_buffer_usage`
- `raw/postgres-18/src/backend/commands/explain.c:show_wal_usage`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:BuildCachedPlan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:choose_custom_plan`
- `raw/postgres-18/src/include/utils/plancache.h:CachedPlanSource`
- `raw/postgres-18/src/backend/optimizer/plan/planner.c:standard_planner`
- `raw/postgres-18/src/backend/optimizer/plan/planmain.c:query_planner`
- `raw/postgres-18/src/backend/optimizer/path/allpaths.c:make_one_rel`
- `raw/postgres-18/src/backend/optimizer/path/allpaths.c:set_rel_size`
- `raw/postgres-18/src/backend/optimizer/util/plancat.c:get_relation_info`
- `raw/postgres-18/src/backend/optimizer/util/plancat.c:estimate_rel_size`
- `raw/postgres-18/src/backend/optimizer/util/plancat.c:relation_excluded_by_constraints`
- `raw/postgres-18/src/backend/optimizer/util/plancat.c:function_selectivity`
- `raw/postgres-18/src/backend/optimizer/util/plancat.c:add_function_cost`
- `raw/postgres-18/src/backend/optimizer/util/plancat.c:get_function_rows`
- `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_seqscan`
- `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_index`
- `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_tuplesort`
- `raw/postgres-18/src/backend/optimizer/path/costsize.c:initial_cost_hashjoin`
- `raw/postgres-18/src/backend/optimizer/path/costsize.c:cost_bitmap_heap_scan`
- `raw/postgres-18/src/backend/optimizer/path/clausesel.c:clauselist_selectivity_ext`
- `raw/postgres-18/src/backend/utils/adt/selfuncs.c:examine_variable`
- `raw/postgres-18/src/backend/utils/adt/selfuncs.c:examine_simple_variable`
- `raw/postgres-18/src/backend/utils/adt/selfuncs.c:get_variable_numdistinct`
- `raw/postgres-18/src/backend/rewrite/rowsecurity.c:get_row_security_policies`
- `raw/postgres-18/src/backend/rewrite/rewriteHandler.c:fireRIRrules`
- `raw/postgres-18/src/backend/optimizer/plan/initsplan.c:process_security_barrier_quals`
- `raw/postgres-18/src/include/catalog/pg_class.h`
- `raw/postgres-18/src/include/catalog/pg_attribute.h`
- `raw/postgres-18/src/include/catalog/pg_index.h`
- `raw/postgres-18/src/include/catalog/pg_proc.h`
- `raw/postgres-18/src/include/catalog/pg_statistic.h`
- `raw/postgres-18/src/include/catalog/pg_statistic_ext.h`
- `raw/postgres-18/src/include/catalog/pg_statistic_ext_data.h`
- `raw/postgres-18/src/backend/catalog/system_views.sql:pg_stat_all_tables`
- `raw/postgres-18/src/backend/catalog/system_views.sql:pg_stat_all_indexes`
- `raw/postgres-18/src/backend/catalog/system_views.sql:pg_stat_activity`
- `raw/postgres-18/src/backend/catalog/system_views.sql:pg_locks`
- `raw/postgres-18/src/backend/utils/adt/dbsize.c:pg_table_size`
- `raw/postgres-18/src/backend/utils/adt/dbsize.c:pg_indexes_size`
- `raw/postgres-18/src/backend/utils/adt/dbsize.c:pg_total_relation_size`
- `raw/postgres-18/src/backend/utils/adt/lockfuncs.c:pg_blocking_pids`
- `raw/postgres-18/src/backend/commands/tablecmds.c:CreateFKCheckTrigger`
- `raw/postgres-18/src/backend/commands/tablecmds.c:createForeignKeyActionTriggers`
- `raw/postgres-18/src/backend/utils/adt/ri_triggers.c:RI_FKey_check`
- `raw/postgres-18/contrib/pg_stat_statements/pg_stat_statements.c:pgssEntry`
- `raw/postgres-18/contrib/pg_stat_statements/pg_stat_statements.c:pgss_store`
- `raw/postgres-18/contrib/auto_explain/auto_explain.c:explain_ExecutorEnd`

## Open Questions

- Should this page grow a reusable SQL script that accepts a query ID or relation OID list and emits a complete diagnostic bundle?
- Which PostgreSQL 18 code path should be traced next: `SeqScan` path construction, `IndexPath` construction, or join search?
