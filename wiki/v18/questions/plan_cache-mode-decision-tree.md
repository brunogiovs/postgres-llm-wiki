---
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
---

# Plan Cache Mode Decision Tree - PostgreSQL 18 Quick Reference

**Version:** PostgreSQL 18 (Primary)  
**Source:** `raw/postgres-18/src/backend/utils/cache/plancache.c` and `plancache.h`

## TL;DR: What Should You Set?

| Your Workload | Recommended Mode | Why |
|---------------|------------------|-----|
| Standard web app, API service (thousands of queries/sec) | **AUTO** (default) or **FORCE_GENERIC_PLAN** | High volume makes planning overhead critical; parameters usually constrained enough for generic plans to work well |
| Search engine with wide range filters (WHERE price > ? from 1% to 90% table size) | **AUTO** (often converges to custom) or test **FORCE_CUSTOM_PLAN** | Parameters drive enormous selectivity variance; accuracy matters more than planning cost |
| Simple CRUD / pure lookups (SELECT * FROM users WHERE id = ?) | **FORCE_GENERIC_PLAN** | Plan identical for all parameter values; eliminates all planning overhead after first use |
| Ad-hoc analytics with wildly varying parameters | **FORCE_CUSTOM_PLAN** or **AUTO** | Parameter variance intentionally exploited by queries; each variant needs its optimal plan |

---

## All Three Modes: One-Liner Pros/Cons

### 1. `plan_cache_mode = 'auto'` (Default)

**Best for:** Mixed workloads, high-frequency API services, most production databases

| ✅ Pro | ❌ Con |
|--------|-------|
| Intelligent hybrid: uses best plan type based on actual execution cost | First ~5 executions generate full custom plans (warm-up period) |
| Self-corrects: if generic proves worse than average custom, switches to custom | Planning overhead when deciding which mode is better |
| Adaptive per-query based on real workload patterns | Unbounded memory potential for queries with extreme parameter variance |

**How it works:** Builds 4-5 parameter-specific custom plans first, then compares their accumulated execution cost against a generic plan. Chooses whichever is cheaper overall. Re-checks if generic becomes worse than average custom.

---

### 2. `plan_cache_mode = 'force_generic_plan'`

**Best for:** High-throughput services with predictable parameters (CRUD apps, simple lookups)

| ✅ Pro | ❌ Con |
|--------|-------|
| Maximum cache efficiency: single shared plan regardless of params | No self-correction - stuck with whatever generic plan was first built |
| Zero planning overhead for cached queries after initial build | First execution pays full planning cost, then stuck with potentially suboptimal generic plan |
| Minimal memory footprint per query | Potentially terrible plans when parameters dramatically affect selectivity (e.g., WHERE amount > ? where ? varies 100x) |

**How it works:** Always builds ONE generic plan. Ignores parameter values entirely after first execution. Never re-evaluates whether custom would be better.

---

### 3. `plan_cache_mode = 'force_custom_plan'`

**Best for:** Ad-hoc analytics, BI tools where parameters dramatically change optimal access paths (narrow use case)

| ✅ Pro | ❌ Con |
|--------|-------|
| Perfect parameter tuning: plan optimized for exact bind values each time | **Planning cost on EVERY execution**, even repeated queries with same params |
| Ideal when selectivity varies by orders of magnitude | Can cause memory explosion (millions of custom plans possible) |
| Never compromises accuracy to save planning cost | Generally not suitable for high-frequency applications |

**How it works:** Builds a fresh plan for every single query execution. No warm-up limit, no caching after first execution unless cursor options override. Unbounded growth potential.

---

## Decision Flowchart

```
┌─────────────────────────────────────────┐
│  What's your workload pattern?         │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┐
    ↓                     ↓
HIGH FREQ (>10K calls)   AD-HOC / BI
(e.g., API service,      (e.g., reports with
 web app backend)        date ranges, filters)
    │                         │
    ├─── Stable params       ├────── Parameter varies widely?
    └──────────────────────>│
                            │ YES → FORCE_CUSTOM_PLAN or AUTO
    ┌──────────┐            └────── NO → FORCE_GENERIC_PLAN
    ↓           ↓              (generic plan works, zero planning overhead)
Parameters     Parameters      ──────────────────────────────────
constrained    unconstrained   │        AUTO is typically best
(lookups by PK,  here          ▼        (self-adapts to reality; 
 enums, status)    only if      no warm-up penalty matters with  
                   selectivity  high variance)     low-frequency queries)       ┌──────────┐            ├─────────────┤
                  varies        │                                   ↓               │   AUTO is default│               ▼              │  (safe for most   
                 significantly                                            │         High FREQ workloads →    deployments that don't  
                    ─────────────────────────> TEST BOTH                FORCE_CUSTOM_PLAN or use  have parameter-driven             
                            with real queries                         AUTO                                    selectivity issues)       
```

---

## Quick Performance Impact Estimates

| Mode | Planning Overhead (after warm-up, if applicable) | Memory per Query Cached Source | When to Use |
|------|--------------------------------------------------|--------------------------------|-------------|
| `AUTO` | First ~5 calls: full planning; thereafter 0% or cost-to-switch | Generic plan only + avg custom plans tracked | Mixed workloads; let algorithm decide |
| `FORCE_GENERIC_PLAN` | Only on first call ever (then cached forever) | Single generic plan tree (~2-16KB for typical queries) | High-frequency lookups, stable constraints |
| `FORCE_CUSTOM_PLAN` | **Every execution** (re-plans always unless cursor hints override) | Potentially unbounded (# distinct params × ~95KB per custom plan) | Analytics with extreme parameter variance |

---

## Red Flags: When to Reconsider

### Change from AUTO → FORCE_GENERIC_PLAN if you see:
- High CPU utilization on database server despite efficient individual query performance
- Query caching statistics showing 1M+ executions but only ~90% generic plan selection rate when params are predictable
- Memory usage normal but response times suggesting repeated planning overhead

### Change to FORCE_CUSTOM_PLAN (or from AUTO) if you see:
- Queries running dramatically slower than expected with parameterized values  
- Generic plans that produce poor cardinality estimates for certain parameter combinations
- `WHERE amount > ?` queries where different parameters return drastically different row counts with wildly varying execution times

---

## Testing Checklist Before Changing Setting

Before modifying `plan_cache_mode` in production:

1. ✅ **Identify affected queries**: Use `pg_stat_statements` to find high-volume parameterized statements
2. ✅ **Check current plan selection**: Look at `call_count - load_count = custom_plan_executions` for those queries
3. ✅ **Verify parameters are stable** (if considering FORCE_GENERIC_PLAN): Test with MIN/MAX values in EXPLAIN ANALYZE to confirm generic plan performs well across the range
4. ✅ **Test warm-up behavior**: Run affected query 6-10 times rapidly and verify auto-mode picks up cached generic plan after first ~5 calls  
5. ✅ **Monitor memory impact** (if considering FORCE_CUSTOM_PLAN): Check that session doesn't accumulate thousands of distinct plans

---

## Version Notes: PostgreSQL 18 Specifics

PostgreSQL 18's `plan_cache_mode` behavior is identical to versions 13-17 for the algorithmic logic. However, PG 18 includes:

- Enhanced statistics collection that makes generic plans more likely to be optimal
- Faster cache invalidation on DDL changes preventing stale plan accumulation
- Improved planning cost estimation model in `cached_plan_cost()` (source: `plancache.c:L1254`) for better AUTO mode decisions

**Bottom line:** Default `AUTO` is safer and smarter in PG 18 than earlier versions. Consider manual tuning only if you have strong evidence of specific workload issues.

---

## Sources & Further Reading

- Plan cache algorithm: [`plancache.c:L99-L205`](https://raw.githubusercontent.com/postgres/postgres/REL_18_STABLE/src/backend/utils/cache/plancache.c#L99-L205) and [`L1174-L1204`](https://raw.githubusercontent.com/postgres/postgres/REL_18_STABLE/src/backend/utils/cache/plancache.c#L1174-L1204)
- Generic vs custom plan cost model: [`plancache.c:L1214-L1258`](https://raw.githubusercontent.com/postgres/postgres/REL_18_STABLE/src/backend/utils/cache/plancache.c#L1214-L1258)
- GUC declaration and options: [`guc_tables.c:L408-L413, L5372-L5380`](https://raw.githubusercontent.com/postgres/postgres/REL_18_STABLE/src/backend/utils/misc/guc_tables.c#L408-L413)

---

**Disclaimer:** Always test in staging with representative data before applying changes to production. Actual performance depends on your specific workload characteristics, index strategies, and database sizing beyond what the planner can predict at ANALYZE time.
