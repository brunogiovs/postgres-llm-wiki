---
type: question
verified: false
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
verified_by_agent: claude-opus-4-7 2026-05-03T10:11:32Z
---

# Prepared Statement Replanning

## Question

In PostgreSQL 18, is there any mechanism to automatically re-prepare a prepared statement? What happens if the schema changes, an index is added, or planner statistics change dramatically?

## Short Answer

Assume PostgreSQL 18, the primary version in [[versions]]. Yes, but the mechanism is better described as automatic revalidation and replanning on next use, not as a background `PREPARE` command being run again. SQL `PREPARE` and extended-protocol `Parse` create a `CachedPlanSource`; `EXECUTE`, `EXPLAIN EXECUTE`, and protocol `Bind` obtain a plan through `GetCachedPlan`. `GetCachedPlan` calls `RevalidateCachedQuery`, then either reuses a still-valid generic `CachedPlan` or builds a new generic or custom plan. Citations: `raw/postgres-18/src/backend/commands/prepare.c:PrepareQuery`, `raw/postgres-18/src/backend/commands/prepare.c:ExecuteQuery`, `raw/postgres-18/src/backend/tcop/postgres.c:exec_parse_message`, `raw/postgres-18/src/backend/tcop/postgres.c:exec_bind_message`, `raw/postgres-18/src/backend/utils/cache/plancache.c:GetCachedPlan`, `raw/postgres-18/src/backend/utils/cache/plancache.c:RevalidateCachedQuery`.

The prepared statement name/session object survives invalidation. The saved query is re-analyzed/re-written when needed, and planning then runs normally. If the statement no longer parses/analyzes, execution errors. If the result row descriptor changes for SQL/protocol prepared statements, PostgreSQL raises `cached plan must not change result type` because those paths create fixed-result cached plans. Citations: `raw/postgres-18/src/backend/utils/cache/plancache.c:RevalidateCachedQuery`, `raw/postgres-18/src/backend/commands/prepare.c:PrepareQuery`, `raw/postgres-18/src/backend/tcop/postgres.c:exec_parse_message`, `raw/postgres-18/src/test/regress/expected/plancache.out`.

## What Is Cached

`PrepareQuery` creates the `CachedPlanSource` before parse analysis, analyzes and rewrites the contained statement, completes the cache entry with `fixed_result = true`, and stores it in the prepared-statement hash table. The extended query protocol follows the same pattern in `exec_parse_message`, using `CompleteCachedPlan(..., true)` and storing named prepared statements through `StorePreparedStatement`. Citations: `raw/postgres-18/src/backend/commands/prepare.c:PrepareQuery`, `raw/postgres-18/src/backend/tcop/postgres.c:exec_parse_message`, `raw/postgres-18/src/backend/commands/prepare.c:StorePreparedStatement`, `raw/postgres-18/src/backend/utils/cache/plancache.c:CompleteCachedPlan`.

The cache entry records the analyzed/re-written query tree, result descriptor, relation dependencies, non-relation invalidation items, and the search path used for parsing/planning. `CompleteCachedPlan` and revalidation both call `extract_query_dependencies`; `CachedPlanSource` stores `relationOids`, `invalItems`, `search_path`, `resultDesc`, and a generic-plan pointer if one exists. Citations: `raw/postgres-18/src/include/utils/plancache.h:CachedPlanSource`, `raw/postgres-18/src/backend/utils/cache/plancache.c:CompleteCachedPlan`, `raw/postgres-18/src/backend/optimizer/plan/setrefs.c:extract_query_dependencies`.

## Revalidation Path

The plan cache is driven by shared invalidation events. `InitPlanCache` registers relation-cache callbacks, specific syscache callbacks for functions and types, and broader callbacks for selected catalogs whose changes invalidate all plans. `PlanCacheRelCallback` invalidates saved plans whose query-tree relation dependencies mention the changed relation, and separately invalidates a generic plan if the planned statement has additional relation dependencies. `PlanCacheObjectCallback` does the same for `PlanInvalItem` dependencies such as user-defined functions and domains. Citations: `raw/postgres-18/src/backend/utils/cache/plancache.c:InitPlanCache`, `raw/postgres-18/src/backend/utils/cache/plancache.c:PlanCacheRelCallback`, `raw/postgres-18/src/backend/utils/cache/plancache.c:PlanCacheObjectCallback`, `raw/postgres-18/src/backend/utils/cache/plancache.c:PlanCacheSysCallback`, `raw/postgres-18/src/include/nodes/plannodes.h:PlanInvalItem`.

On the next `GetCachedPlan`, `RevalidateCachedQuery` checks search path and row-security context, reacquires locks, reacts to any invalidation that arrived during the lock race window, discards the old query tree and generic plan if needed, and reruns parse analysis/rewrite. It then recomputes dependencies and marks the query valid again. Citations: `raw/postgres-18/src/backend/utils/cache/plancache.c:RevalidateCachedQuery`, `raw/postgres-18/src/backend/utils/cache/plancache.c:AcquirePlannerLocks`, `raw/postgres-18/src/backend/utils/cache/plancache.c:ReleaseGenericPlan`.

## Schema Changes

Schema changes reach the plan cache through catalog and relcache invalidation. Catalog tuple changes in `pg_class`, `pg_attribute`, `pg_index`, and foreign-key `pg_constraint` rows register relcache invalidations for the affected relation. When such an invalidation matches a saved prepared statement dependency, the next execution revalidates and replans. Citations: `raw/postgres-18/src/backend/utils/cache/inval.c:CacheInvalidateHeapTupleCommon`, `raw/postgres-18/src/backend/utils/cache/inval.c:CacheInvalidateRelcache`, `raw/postgres-18/src/backend/utils/cache/plancache.c:PlanCacheRelCallback`.

The outcome depends on the schema change. Dropping a referenced table or column can make parse analysis fail on the next execution. Adding a column to a `SELECT *` prepared statement can change the output tuple descriptor, and fixed-result prepared statements then error with `cached plan must not change result type`. If the change does not break analysis and does not change the fixed result descriptor, the statement can execute with a newly built plan. Citations: `raw/postgres-18/src/backend/utils/cache/plancache.c:RevalidateCachedQuery`, `raw/postgres-18/src/test/regress/expected/plancache.out`.

## Added Indexes

Adding an index is a concrete case where PostgreSQL intentionally invalidates cached plans for the parent table. Normal index creation registers relcache invalidation on the heap relation to keep its index list consistent. `CREATE INDEX CONCURRENTLY` explicitly sends a relcache invalidation on the parent table so existing sessions refresh cached plans that could use the new index. Citations: `raw/postgres-18/src/backend/catalog/index.c:index_create`, `raw/postgres-18/src/backend/commands/indexcmds.c:DefineIndex`, `raw/postgres-18/src/backend/utils/cache/inval.c:CacheInvalidateRelcacheByRelid`.

After that invalidation, the next plan build can consider the new index. During planning, `get_relation_info` opens the relation, obtains `RelationGetIndexList`, filters out invalid or not-yet-usable indexes, and builds `IndexOptInfo` entries for valid indexes. A replan therefore may choose the new index, but only if the planner estimates it as preferable for the statement and parameter values. Citations: `raw/postgres-18/src/backend/optimizer/util/plancat.c:get_relation_info`, `raw/postgres-18/src/backend/utils/cache/plancache.c:BuildCachedPlan`.

## Statistics Changes

PostgreSQL 18 documentation for `PREPARE` states that PostgreSQL forces re-analysis and re-planning before use when database objects used by the statement have DDL changes or when their planner statistics have been updated since the previous use. The plancache source describes the runtime mechanism as sinval-driven invalidation followed by parse analysis/rewrite and normal planning on the next demand; `RevalidateCachedQuery` also notes the case of an invalidation prompted by DDL or statistics changes. Citations: `raw/postgres-18/doc/src/sgml/ref/prepare.sgml`, `raw/postgres-18/src/backend/utils/cache/plancache.c:RevalidateCachedQuery`.

The plan cache does not contain a "dramatic enough" threshold and does not replan because a previous execution was slow. It responds to invalidation and to execution-time policy. `ANALYZE` writes column statistics, extended statistics, and relation/index `pg_class` statistics; `vac_update_relstats` updates `relpages`, `reltuples`, visibility counts, and some lazily maintained flags for heap and index relations. Data distribution changes before statistics are updated are therefore not themselves a plan-cache trigger. Citations: `raw/postgres-18/src/backend/commands/analyze.c:do_analyze_rel`, `raw/postgres-18/src/backend/commands/analyze.c:update_attstats`, `raw/postgres-18/src/backend/commands/vacuum.c:vac_update_relstats`, `raw/postgres-18/src/backend/utils/cache/plancache.c:PlanCacheRelCallback`.

## Generic Versus Custom Plans

For parameterized prepared statements, PostgreSQL may build custom plans using the actual bound parameter values or a reusable generic plan. In the default `plan_cache_mode = auto` policy, `choose_custom_plan` uses custom plans for the first five parameterized executions, then compares the estimated generic plan cost against the average custom-plan cost. A statement without parameters has no benefit from custom planning and uses a generic plan. Citations: `raw/postgres-18/src/backend/utils/cache/plancache.c:choose_custom_plan`, `raw/postgres-18/src/backend/utils/cache/plancache.c:BuildCachedPlan`, `raw/postgres-18/doc/src/sgml/ref/prepare.sgml`.

A custom plan is built for that execution, so it naturally sees the current planner inputs at planning time. A valid generic plan is reused until invalidated or discarded. `DISCARD PLANS` is the manual session-local escape hatch: it calls `ResetPlanCache`, causing cached query plans to be rebuilt on later use. Citations: `raw/postgres-18/src/backend/utils/cache/plancache.c:GetCachedPlan`, `raw/postgres-18/src/backend/utils/cache/plancache.c:CheckCachedPlan`, `raw/postgres-18/src/backend/commands/discard.c:DiscardCommand`, `raw/postgres-18/doc/src/sgml/ref/discard.sgml`.

## Source References

- `raw/postgres-18/src/backend/commands/prepare.c:PrepareQuery`
- `raw/postgres-18/src/backend/commands/prepare.c:ExecuteQuery`
- `raw/postgres-18/src/backend/commands/prepare.c:StorePreparedStatement`
- `raw/postgres-18/src/backend/commands/discard.c:DiscardCommand`
- `raw/postgres-18/src/backend/tcop/postgres.c:exec_parse_message`
- `raw/postgres-18/src/backend/tcop/postgres.c:exec_bind_message`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:CompleteCachedPlan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:GetCachedPlan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:RevalidateCachedQuery`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:CheckCachedPlan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:BuildCachedPlan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:choose_custom_plan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:InitPlanCache`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:PlanCacheRelCallback`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:PlanCacheObjectCallback`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:PlanCacheSysCallback`
- `raw/postgres-18/src/backend/utils/cache/inval.c:CacheInvalidateHeapTupleCommon`
- `raw/postgres-18/src/backend/utils/cache/inval.c:CacheInvalidateRelcache`
- `raw/postgres-18/src/backend/utils/cache/inval.c:CacheInvalidateRelcacheByRelid`
- `raw/postgres-18/src/backend/catalog/index.c:index_create`
- `raw/postgres-18/src/backend/commands/indexcmds.c:DefineIndex`
- `raw/postgres-18/src/backend/optimizer/util/plancat.c:get_relation_info`
- `raw/postgres-18/src/backend/optimizer/plan/setrefs.c:extract_query_dependencies`
- `raw/postgres-18/src/backend/commands/analyze.c:do_analyze_rel`
- `raw/postgres-18/src/backend/commands/analyze.c:update_attstats`
- `raw/postgres-18/src/backend/commands/vacuum.c:vac_update_relstats`
- `raw/postgres-18/src/include/utils/plancache.h:CachedPlanSource`
- `raw/postgres-18/src/include/nodes/plannodes.h:PlanInvalItem`
- `raw/postgres-18/doc/src/sgml/ref/prepare.sgml`
- `raw/postgres-18/doc/src/sgml/ref/discard.sgml`
- `raw/postgres-18/src/test/regress/expected/plancache.out`

## Open Questions

- The high-level rule for planner-statistics updates is documented in `PREPARE`, and the plancache comments refer to statistics-driven invalidation. This page traces the confirmed `ANALYZE` and relstats paths, but does not yet distinguish every `pg_statistic`-only update path from `pg_class` relstats invalidation. A narrower follow-up trace should inspect `STATRELATTINH` syscache invalidation and plan-cache callback coverage if that granularity matters.
