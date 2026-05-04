---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# `plan_cache_mode` Production Impact

## Question

In PostgreSQL 12, how do the different `plan_cache_mode` values impact a production environment, what is the best mode for different scenarios? Pros and cons per mode. Impact of slow random I/O disk.

Detailed for `auto` mode: what is the overhead of checking whether the generic plan needs to be re-calculated, and at what moment in the query execution cycle does that check happen?

## Short Answer

PostgreSQL 12 introduced `plan_cache_mode`, controlling custom vs generic plans for parameterized cached plans (`PREPARE`, extended protocol `Parse`, PL/pgSQL). [[raw/postgres-12/src/backend/utils/cache/plancache.c#choose_custom_plan]], [[raw/postgres-12/src/backend/utils/cache/plancache.c#GetCachedPlan]], [[raw/postgres-12/src/include/utils/plancache.h#PlanCacheMode]].

Modes: `auto` (default), `force_generic_plan`, `force_custom_plan`. PGC_USERSET.

Decision: shape depends on params? Yes → `force_custom_plan` (skew, ranges, partitions). No → `force_generic_plan` (OLTP PK lookups). Else `auto`.

## Where The Setting Is Read

GUC `int plan_cache_mode` in `plancache.c`. Read in `choose_custom_plan` → `GetCachedPlan` every exec. [[raw/postgres-12/src/backend/utils/cache/plancache.c#plan_cache_mode]].

Decision tree (`plancache.c`):

1. `is_oneshot` → custom (`plancache.c:1021`)
2. `boundParams == NULL` → generic (`plancache.c:1025`)
3. `IsTransactionStmtPlan` → generic (transaction control stmts; macro at `plancache.c:82`, check at `plancache.c:1028`)
4. `FORCE_GENERIC_PLAN` → generic (`plancache.c:1032`)
5. `FORCE_CUSTOM_PLAN` → custom (`plancache.c:1034`)
6. `CURSOR_OPT_GENERIC_PLAN` → generic (`plancache.c:1038`)
7. `CURSOR_OPT_CUSTOM_PLAN` → custom (`plancache.c:1040`)
8. `num_custom_plans < 5` → custom (`plancache.c:1044`)
9. `generic_cost < avg_custom_cost` → generic else custom (`plancache.c:1059`)

GUC overrides cursor opts.

After new generic, recheck; if custom, discard generic.

## What `auto` Actually Costs

Custom charged planning + exec, generic only exec. `cached_plan_cost` adds planner overhead for custom. Tilts to generic.

Locked to first 5 custom.

## Auto Mode: Revalidation Overhead And Timing

### When `GetCachedPlan` Runs

Once per execute, before the executor starts. Entry points in PG 12:

- Extended protocol `Bind`: `exec_bind_message` → `GetCachedPlan` ([[raw/postgres-12/src/backend/tcop/postgres.c#1876]]).
- `EXECUTE name(...)`: `ExecuteQuery` → `GetCachedPlan` ([[raw/postgres-12/src/backend/commands/prepare.c#246]]).
- `EXPLAIN EXECUTE`: `ExplainExecuteQuery` → `GetCachedPlan` ([[raw/postgres-12/src/backend/commands/prepare.c#663]]).
- SPI / PL/pgSQL: `_SPI_execute_plan` and friends → `GetCachedPlan` ([[raw/postgres-12/src/backend/executor/spi.c#1389]], [[raw/postgres-12/src/backend/executor/spi.c#1822]], [[raw/postgres-12/src/backend/executor/spi.c#2215]]).

The whole revalidation/recheck dance sits between message dispatch and `ExecutorStart`. None of its cost shows up in `EXPLAIN ANALYZE` exec time; it shows up as Bind / Execute latency on the wire.

### Steady-State Cost Per Execute (Plansource And Plan Both Valid)

`GetCachedPlan` (`plancache.c:1137`) does three things in order. Under `auto`, on the cheap path:

1. **`RevalidateCachedQuery`** (`plancache.c:1153 → plancache.c:552`):
   - `is_oneshot` / `IsTransactionStmtPlan` short-circuit (`plancache.c:571`).
   - `OverrideSearchPathMatchesCurrent` compare (`plancache.c:585`); replan-trigger if the session's `search_path` shifted.
   - RLS recheck if `dependsOnRLS`: compares `rewriteRoleId`/`rewriteRowSecurity` (`plancache.c:598`).
   - **`AcquirePlannerLocks(plansource->query_list, true)`** (`plancache.c:610`, defined at `plancache.c:1615`). One `LockRelationOid` per RTE found by `ScanQueryForLocks` (`plancache.c:1637`). Each lock acquisition drains pending sinval via `AcceptInvalidationMessages`, which is where `PlanCacheRelCallback` / `PlanCacheObjectCallback` / `PlanCacheSysCallback` (`plancache.c:114-116`) flip `is_valid` to false if a relation/syscache the plansource depends on has been touched since the last execute.
   - Race recheck of `plansource->is_valid` (`plancache.c:616`). Pass → return `NIL` (no replan).
2. **`choose_custom_plan`** (`plancache.c:1156 → plancache.c:1015`): the 9-step decision tree, all reads off the in-memory `CachedPlanSource`. O(1) work, no I/O. Step 9 (`generic_cost < avg_custom_cost`) is the actual `auto` heuristic.
3. **`CheckCachedPlan`** on the generic branch (`plancache.c:1160 → plancache.c:792`):
   - role-dependency check (`plancache.c:811`).
   - **`AcquireExecutorLocks(plan->stmt_list, true)`** (`plancache.c:827`, defined at `plancache.c:1560`). Second sweep, this time over the planned statements — which can include partition-expanded relations not present in the original `query_list`.
   - Transient-xmin check: `TransactionIdIsValid(plan->saved_xmin) && !TransactionIdEquals(plan->saved_xmin, TransactionXmin)` (`plancache.c:833`). Forces a replan if the plan was tagged transient (e.g. observed an in-progress xact whose snapshot has now advanced).
   - Race recheck of `plan->is_valid` (`plancache.c:842`).

So the steady-state overhead is **two lock-acquisition sweeps** (planner-lock then executor-lock, each with a sinval drain and a race re-check), one search_path string compare, one RLS compare, and the heuristic walk. Dominant variable cost scales with locked-relation count: rangetable size in `RevalidateCachedQuery`, `stmt_list` lock count in `CheckCachedPlan`. For a single-table point lookup, that is two `LockRelationOid` calls; for a wide partitioned scan, one per locked partition per sweep.

### Cost When Something Has Been Invalidated

`auto` is "self-correcting" because the plansource and the generic plan can be invalidated independently:

- **Plansource invalid** (race recheck at `plancache.c:616` fails): drops `query_list`, releases the generic plan via `ReleaseGenericPlan` (`plancache.c:652`), re-runs parse analysis + rewrite via `pg_analyze_and_rewrite[_params]` (`plancache.c:683-693`), and re-extracts dependencies via `extract_query_dependencies` (`plancache.c:744`). `generic_cost` / `total_custom_cost` / `num_custom_plans` are deliberately **not** reset (`plancache.c:768-775` comment) so the heuristic keeps its history across DDL.
- **Plan invalid** (`CheckCachedPlan` returns false at `plancache.c:842`/`857`): full planner pass via `BuildCachedPlan` → `pg_plan_queries` (`plancache.c:933`). After the new generic plan is installed, `GetCachedPlan` re-runs `choose_custom_plan` (the "wart" recheck at `plancache.c:1200`); under `auto` this is the moment step 9 (`generic_cost < avg_custom_cost`) actually fires for the first time, since `generic_cost` was `-1` until this build. If the recheck flips to custom, the just-built generic plan is discarded and a custom plan is built instead.
- **First generic build after the fifth custom**: same `BuildCachedPlan` cost plus the wart recheck. After this point the comparison gate (step 9) is the only thing keeping `auto` honest — `num_custom_plans` is already `>= 5`, so the "first 5 custom" sample never re-runs.

### Position In The Query Execution Cycle

```
extended Bind message
  └─ exec_bind_message (postgres.c:1876)
       └─ GetCachedPlan                    ← all auto-mode revalidation runs here
            ├─ RevalidateCachedQuery       (planner-lock sweep + sinval drain + race recheck)
            ├─ choose_custom_plan          (9-step heuristic, O(1))
            └─ CheckCachedPlan             (executor-lock sweep + xmin + race recheck)
            └─ [BuildCachedPlan]           (only on invalid / first generic / custom branch)
            └─ [choose_custom_plan again]  (wart recheck after fresh generic)
extended Execute message
  └─ PortalRun → ExecutorStart → ExecutorRun → ExecutorFinish → ExecutorEnd
```

The whole block precedes `ExecutorStart`, so the overhead is invisible to `EXPLAIN ANALYZE` but visible in client-observed Bind/Execute latency and indirectly in `pg_stat_statements.total_time` minus exec time.

## Mode-by-Mode Production Analysis

### `auto` (default)

First 5 custom, then generic if cheaper.

**Pros:**
- Adaptive
- Self-correcting per CPS
- Replans on inval

**Cons:**
- Switch after 5th
- Generic if underestimated
- First 5 plan each

Best: mixed, default.

### `force_generic_plan`

Always generic after first.

**Pros:**
- Max amortization
- Predictable
- High QPS OLTP

**Cons:**
- Bad on skew/ranges/partitions
- No fallback

Best: stable OLTP.

### `force_custom_plan`

Always custom.

**Pros:**
- Optimal per params
- Fixes bad generic

**Cons:**
- Plan every time
- High CPU QPS

Best: skewed params.

## Scenario Picker

| Trait | Mode |
|-------|------|
| OLTP PK high QPS | force_generic_plan |
| Analytic skew/range | force_custom_plan |
| Mixed | auto |

## Impact of Slow Random I/O Disk

Planning: catalog reads (`get_relation_info` pg_class/index/statistic), syscache, relcache rebuilds → random I/O if cold. [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_info]].

Even warm: SLRU (CLOG), dirty victim `FlushBuffer`. See [[v12/questions/query-disk-io-with-warm-cache]].

Cached plans reduce planning freq. `force_generic_plan` best (stable reuse). `force_custom_plan` worst (plan each). `auto` middle.

Slow disk: amplify planning latency → prefer generic reuse.

## Operational Notes

- SET LOCAL, DISCARD PLANS to force.
- EXPLAIN EXECUTE shows $1 vs literal.
- pg_prepared_statements no counters.

## Source References

- [[raw/postgres-12/src/backend/utils/cache/plancache.c#choose_custom_plan]]
- [[raw/postgres-12/src/backend/utils/cache/plancache.c#GetCachedPlan]]
- [[raw/postgres-12/src/backend/utils/cache/plancache.c#cached_plan_cost]]
- [[raw/postgres-12/src/backend/utils/cache/plancache.c#BuildCachedPlan]]
- [[raw/postgres-12/src/backend/utils/cache/plancache.c#RevalidateCachedQuery]]
- [[raw/postgres-12/src/backend/utils/misc/guc.c#plan_cache_mode_options]]
- [[raw/postgres-12/src/include/utils/plancache.h#PlanCacheMode]]
- [[raw/postgres-12/src/include/utils/plancache.h#CachedPlanSource]]
- [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_info]]
- [[raw/postgres-12/doc/src/sgml/ref/prepare.sgml]]

## Open Questions

- First-5 hard-coded.
- No pg_prepared_statements counters.