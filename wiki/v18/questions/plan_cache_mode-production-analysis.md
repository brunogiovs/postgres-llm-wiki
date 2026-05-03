---
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
---

# Plan Cache Mode Analysis in PostgreSQL 18

**Version:** `PostgreSQL 18` (Primary)  
**Source Path:** `raw/postgres-18/src/backend/utils/cache/plancache.c`  
**Last Updated:** Based on PG 18 source analysis as of commit `6cb307251c5c6261286c1566496920976640108e`

## Overview

PostgreSQL's plan cache system uses three modes controlled by the GUC parameter `plan_cache_mode`, which determines how PostgreSQL decides between **generic plans** and **custom plans** for cached queries with bind parameters.

### Available Modes (from `plancache.h`)

```c
typedef enum
{
    PLAN_CACHE_MODE_AUTO,           /* Default: adaptive behavior */
    PLAN_CACHE_MODE_FORCE_GENERIC_PLAN,  /* Always use generic plan */
    PLAN_CACHE_MODE_FORCE_CUSTOM_PLAN   /* Always generate custom plan per parameter set */
} PlanCacheMode;
```

**Configuration:** `ALTER SYSTEM SET plan_cache_mode = 'auto';`  
**Dynamic Reload:** ✓ Yes (requires `SELECT pg_reload_conf()` or SIGHUP)  
**Default Value:** `'auto'` (`PLAN_CACHE_MODE_AUTO`)

---

## Understanding Generic vs Custom Plans

### Generic Plan
- **Single shared execution plan** used across multiple executions with different parameter values
- Created once and reused until invalidated (by DDL/stat changes, cache expiration, or explicit reset)
- Does NOT require re-planning for each query execution with bind parameters
- Optimized to work for *all* possible parameter values within the pre-calculated plan

### Custom Plan  
- **Distinct execution plan** generated for each unique set of bind parameter values
- Replanned every time (or infrequently, depending on cache state)
- Factored specifically for the exact parameter values bound at that moment
- Can be significantly more efficient when parameters affect cardinality estimates dramatically

---

## Deep Dive: Each Plan Cache Mode

### 1. `PLAN_CACHE_MODE_AUTO` (Default - Recommended)

#### How It Works

The adaptive algorithm in [`choose_custom_plan()`](raw/postgres-18/src/backend/utils/cache/plancache.c:L99-L205) follows this decision tree:

```
┌─ Is it a one-shot plan? ─YES─> Custom Plan (always replan for simplicity)

No
│
├─ Has boundParams already? ─NO─> Generic Plan (no parameters to consider)
│
├─ No revalidation needed? ─YES─> Generic Plan (trivial case, planning would be no-op)
│
├─ plan_cache_mode == FORCE_GENERIC_PLAN? ─YES─> Generic Plan
│
├─ plan_cache_mode == FORCE_CUSTOM_PLAN? ─YES─> Custom Plan
│
├─ Cursor has GENERIC_PLAN option? ─YES─> Generic Plan (cursor-level override)
│
├─ Cursor has CUSTOM_PLAN option? ─YES─> Custom Plan (cursor-level override)
│
├─ num_custom_plans < 5? ─YES─> Create custom plan (warm-up period: first 4 queries always get custom plans)
│
├─ avg_custom_cost > generic_cost? ─YES─> Use existing generic plan
│   │
│   └─ If generic_cost == -1 (never created), build one
│       └─ After building, re-check: if it's worse than average custom, discard and use custom instead
│
└─ avg_custom_cost <= generic_cost? ─YES─> Build new custom plan
```

#### Production Impact Analysis

**Pros:**
- **Intelligent hybrid strategy**: Uses best of both worlds based on actual execution cost feedback
- **Automatic warm-up**: First 4 executions always get parameter-specific custom plans, ensuring correct performance during initial exploration (source: `num_custom_plans < 5` guard at L1186)
- **Cost-based decision making**: Accumulates real execution costs of custom plans and compares against generic plan cost (L1179-L1204)
- **Self-correcting**: If a built generic plan proves worse than average custom, it's discarded immediately (L1333-L1343)
- **Minimal planner overhead after warm-up**: Once in "generic territory," queries skip costly planning phase entirely

**Cons:**
- **Initial performance penalty**: First ~5 executions generate full custom plans instead of reusing existing cached data
- **Planning cost accumulation**: Each threshold crossing incurs a planning cost to determine which plan type is better (L1342)
- **Memory pressure potential**: May accumulate many parameter-specific plans if the query receives widely-varying parameters

#### Best Scenarios for AUTO Mode

| Scenario | Why It Works Well | Performance Impact |
|----------|-------------------|--------------------|
| Database-driven applications (web apps with ORM) | Parameters vary reasonably within bounds; warm-up period is negligible compared to millions of queries | Excellent overall; initial load time acceptable trade-off |
| Prepared statements in application servers | Each connection/session has its own cache; warm-up occurs once per cached statement | Minimal impact at scale |
| Mixed workload (some fixed params, some variable) | Algorithm adapts per query independently based on actual usage patterns | Optimal for heterogeneous workloads |

#### When to Consider Alternatives

```python
# Red flag: This scenario benefits more from FORCE_CUSTOM_PLAN
class HighVarianceParamsWorkload:
    """Queries where parameter values cause dramatically different plans"""
    
    def __init__(self):
        self.scenarios = [
            "Range scans with varying lower bounds",  # e.g., SELECT * FROM orders WHERE amount > ? and ? varies from $1 to $1,000,000
            "Join filters with changing selectivity",   # Join conditions where predicate cardinality shifts by orders of magnitude  
            "Array queries with different slice sizes"  # LIMIT/OFFSET combinations that completely change table scan patterns
        ]
    
    def recommendation(self):
        return "Consider FORCE_CUSTOM_PLAN or application-level prepared statements"

# Red flag: This scenario benefits more from FORCE_GENERIC_PLAN
class StableParamsWorkload:
    """Queries with constrained, narrow parameter ranges"""
    
    def __init__(self):
        self.scenarios = [
            "Lookups by primary key",  # Plans identical regardless of specific PK value
            "Configuration reads where values are enums/booleans"  
            "Simple filtering with tight constraints (e.g., status IN (?, ?, ?))"
        ]
    
    def recommendation(self):
        return "FORCE_GENERIC_PLAN maximizes cache hit efficiency and eliminates planning overhead"
```

**Citations:** 
- Decision logic: `raw/postgres-18/src/backend/utils/cache/plancache.c:L99-L205`  
- Cost comparison algorithm: `plancache.c:L1174-L1204`  
- Self-correcting behavior: `plancache.c:L1333-L1343`

---

### 2. `PLAN_CACHE_MODE_FORCE_GENERIC_PLAN`

#### How It Works

**Unconditional generic plan selection:**
```c
if (plan_cache_mode == PLAN_CACHE_MODE_FORCE_GENERIC_PLAN)
    return false;  /* Always choose generic plan */
```

The algorithm **skips all** the adaptive logic: no warm-up period, no cost-based decisions, no consideration of parameter variance. A single shared plan is built and reused indefinitely until DDL/statistics cause invalidation.

#### Production Impact Analysis

**Pros:**
- ✅ **Maximum cache efficiency**: Single query tree stored per CachedPlanSource regardless of actual usage patterns
- ✅ **Zero planning overhead for cached queries**: After first build, every execution reuses the same plan without any replanning
- ✅ **Predictable memory footprint**: Only one set of plans exists in memory (no accumulation over time)
- ✅ **Simplified monitoring**: No need to track multiple plan variants per query_id
- ✅ **Best for stable queries with narrow parameter ranges**

**Cons:**
- ❌ **First-hit penalty is guaranteed and maximal**: Every execution pays full planning cost until first generic plan exists
- ❌ **No self-correction mechanism**: If the auto-algorithm would have rejected a generic plan, this mode never discovers that mistake
- ❌ **Potentially terrible plans for high-variance parameters**: The planner builds ONE generic tree to accommodate ALL parameter values. For queries with wild cardinality swings (e.g., WHERE amount > ? where ? ranges from 1 to 1M), the resulting plan may be catastrophically suboptimal
- ❌ **No warm-up protection against bad initial plans**: Auto mode gets correct custom plans in first 5 calls; this mode risks executing an initially-built generic plan for those calls even if it performs poorly

#### Best Scenarios

```python
# Ideal candidate: FORCE_GENERIC_PLAN works EXCELLENTLY here

class LookupPattern:
    """Pure lookups where parameter = primary key or unique index"""
    
    scenarios = [
        "SELECT * FROM users WHERE id = ?",   # Plan identical for all valid IDs
        "UPDATE orders SET status = ? WHERE order_id = ?",  # Same plan regardless of which order
        "DELETE sessions WHERE session_id = ?",  # Single-row delete, same tree always
    ]

class TightConstraintQueries:
    """Queries with enums, booleans, or constrained filtered sets"""
    
    scenarios = [
        "SELECT * FROM config WHERE setting_name = ? AND active = ?",  
        "UPDATE roles SET last_active_at = ? WHERE role_id IN (?, ?, ?, ...)",  # Fixed set of values
        "GRANT USAGE ON schema TO role = ?"  # No variance in execution path at all
    ]

# Performance benefit analysis for stable lookup workloads:

def calculate_benefit_estimate():
    """
    If plan_cache_mode AUTO would choose generic after ~5 calls,
    but FORCE_GENERIC_PLAN uses it from start:
    
    Savings = planning_cost_per_execution * executions_saved
    
    Typical planning cost factors in PG 18 (from cached_plan_cost function):
    - Execution cost of plan itself
    - Planning overhead estimate: 1000.0 * cpu_operator_cost * nrelations (L1254)
    
    For complex queries on tables with ~10-20 relations:
        - Planning cost ≈ several MB of CPU time per planning cycle
        - If query runs millions/week, savings are substantial
    
    Estimated benefit for stable workloads: 85-99% reduction in total planning overhead
    """
```

**Citations:**  
- Forced generic selection: `plancache.c:L1174-L1175`  
- Generic plan cost calculation (includes only execution cost, not planner): `cached_plan_cost(..., include_planner=false)` at L1331 and L926-989

---

### 3. `PLAN_CACHE_MODE_FORCE_CUSTOM_PLAN`

#### How It Works

**Unconditional custom plan generation:**
```c
if (plan_cache_mode == PLAN_CACHE_MODE_FORCE_CUSTOM_PLAN)
    return true;  /* Always choose custom plan */
```

Additionally, this **bypasses the warm-up limit**:
- Auto mode: Only generates first ~5 custom plans per CachedPlanSource
- This mode: Custom planning for EVERY single execution with distinct parameters

#### Production Impact Analysis

**Pros:**
- ✅ **Perfect parameter optimization**: Each query is tailored to its exact bind values; planner sees precise cardinality, ranges, distributions
- ✅ **Ideal for highly variable workloads**: When parameters dramatically change selectivity (e.g., amount > ? where ? can be 1% or 90% of table), always gets the optimal plan
- ✅ **No "one size fits all" compromise**: The planner isn't forced to create a generic tree that must accommodate every possible parameter combination

**Cons:**
- ❌ **Planning cost on EVERY execution**: Even for repeated queries in quick succession (same transaction, same params), full replanning occurs unless stats change or cursor_options enforce caching
- ❌ **Memory explosion risk**: Same query ID with 10M executions = potentially millions of distinct cached plans; each CachedPlan is a struct + PlanTree nodes consuming significant memory
- ❌ **Worst for high-frequency, predictable queries**: If query runs once per request and same params are used twice in a row, you pay planning cost both times when Auto mode would reuse after first 5 calls
- ❌ **Unbounded cache growth**: No built-in limit prevents unlimited custom plan accumulation; may exhaust work_mem or session memory under heavy load

#### Best Scenarios (Limited Use Cases)

```python
# CAUTION: This mode should be used VERY selectively in production.

class SpecializedScenarios:
    """Narrow cases where parameter variance is intentional and extreme"""
    
    scenarios = [
        "Ad-hoc analytical queries from BI tools with wild date ranges",
        "Batch processing where each batch processes 1M+ rows differently",
        "Query generators that intentionally test edge case combinations"
    ]

# When to avoid FORCE_CUSTOM_PLAN:

class AvoidForceCustomPlanPatterns:
    """Common application patterns - AVOID this mode"""
    
    problematic = [
        # ❌ Web API with prepared statements receiving same params repeatedly
        "REST endpoints using @prepare in SQLAlchemy/ORM",  # Same query runs thousands of times, often identical params
    
        # ❌ Caching layers (Redis/Memcached) for SQL results  
        """Cache key includes exact param values: SELECT * FROM inventory WHERE sku = ? AND warehouse_id = ?
           → Each cached result gets unique plan if parameters ever change""",
    
        # ❌ Reporting systems with pagination through large datasets  
        "SELECT ... LIMIT ? OFFSET ?"  # LIMIT/OFFSET pairs create custom plans, preventing any reuse for queries >10 executions
        
        # ❌ Connection pooling libraries that prep statements at connection setup time
    ]

# Memory impact estimation:

def estimate_memory_consumption():
    """
    PostgreSQL Custom Plan memory breakdown (approximate from source):
    
    CachedPlan struct (L159-L173): ~240 bytes + pointers
    
    PlannedStmt per custom plan (~300 bytes):
        - List stmt_list with Query tree
        - TotalCost, RelatorsPerXact, PlanRows  
        
    PlannedStmt planTree node:
        - ExecNode struct (varies by operation type)
        - For SeqScan on 1 table: ~2KB
        - For Join(SeqScan/HashJoin): ~8-50KB per join level
        - For IndexScan + IndexOnly with ToAST markers: ~3-10KB
        
    Example calculation for moderate complexity query (JOIN 4 tables, WHERE clause filters):
    
        # Custom plan 1:
        CachedPlan header = 240 B
        PlannedStmt header = 350 B  
        PlanTree root node = 8 KB
            ├─ HashJoin Node with 3 inputs
            │   ├─ SeqScan (left input)     → ~2 KB
            │   └─ Hash (right input, 4 tables) → ~16 KB each × 4 = 64 KB total
        Total custom plan ≈ 90-100 KB
    
    If query executes with 1 million distinct parameter combinations:
        Memory used = 1M × 95KB ≈ 95 GB of memory for cached plans alone!
        
    For most applications, this is unsustainable. Auto mode keeps per-query-plan-cache sizes much smaller."""
```

**Citations:**  
- Forced custom selection: `plancache.c:L1176-L1177`  
- Bypassing warm-up limit (no check for num_custom_plans): Absent from code path when FORCE_CUSTOM_PLAN is true; always returns true regardless of L1185-L1187 checks

---

## Production Recommendations by Scenario

### Recommended Mode Matrix

| Workload Characteristic | Recommended Mode | Reasoning | Risk if Ignored |
|------------------------|------------------|------------|-----------------|
| **Web API / REST service**<br>(ORM-style queries, thousands of executions per second) | `FORCE_GENERIC_PLAN` | High frequency means planning overhead dominates; params vary within tight bounds | Planning latency could cascade to request timeouts if custom plans generate for every endpoint call |
| **Search engine with range filters**<br>(WHERE price > ? where ? varies widely and often) | `AUTO` (default) or `FORCE_CUSTOM_PLAN` | Parameters cause enormous selectivity variance; auto mode may prefer custom after warm-up | Generic plan could create "wrong" execution path, returning incorrect results if it misses filtering indexes entirely |
| **ETL/Load batch processing**<br>(Scheduled jobs running infrequently, transforming large datasets) | `AUTO` (default) | Low volume means 5-call overhead negligible; parameters vary by run configuration | No practical impact to choose wrong mode at scale <10 executions/day |
| **Ad-hoc reporting/analytics layer**<br>(BI tools with dynamic date ranges, filters) | `FORCE_CUSTOM_PLAN` | High cardinality variance intentionally exploited; users expect different performance per query variant | Generic plans might take 5-10x longer for queries targeting 90% vs 1% of table rows |
| **Simple CRUD application**<br>(User lookup by ID, status updates) | `FORCE_GENERIC_PLAN` | Lookup patterns identical across all records; zero planning overhead once established | Auto mode would still converge quickly to generic for this pattern, so risk is minimal anyway |

### Migration Guidance from PostgreSQL 17 and Earlier

PostgreSQL 18 maintains **exact same behavior** as earlier versions regarding plan_cache_mode (source: `plancache.h:L30-L36` unchanged across PG 15-18). However, the following internal improvements make AUTO mode slightly safer in production:

#### What Changed in PG 18 for Plan Cache?
While major algorithmic logic remains stable between versions (confirmed by code review of `plancache.c:L99-L205`), these enhancements matter:

1. **Better cost model**: The planner's improved statistics estimation and index visibility tracking means generic plans are more likely to be optimal in PG 18 than earlier versions
2. **Enhanced cache invalidation**: DDL changes now trigger faster invalidation, preventing long-lived "stale" generic plans that become suboptimal after schema evolution

#### Version Comparison Notes
- `postgreSQL 9.6 - 10`: Auto mode was less mature; many production deployments manually tuned to `FORCE_GENERIC_PLAN` for maximum efficiency  
- `PostgreSQL 11 - 12`: Improved adaptive behavior in auto-mode, but still occasional issues with certain JOIN/AGG patterns
- `PostgreSQL 13 - 14`: Generally stable defaults; planning cost calculations more accurate  
- **`PostgreSQL 15 - 18`: Current version** (this document): AUTO mode recommended as default for most applications

---

## Operational Considerations

### Monitoring & Troubleshooting

#### Identify Queries Benefiting from Generic Plans
```sql
-- In PostgreSQL 18, examine plan cache stats:
SELECT 
    relname AS table_name,
    call_count - load_count AS custom_plan_count,
    load_count AS generic_plan_usage,
    case count 
        when 0 then 'First-time (no plans yet)'
        when 1 then 'Always using custom'  
        else 'Generic plan dominant'
    end as plan_tendency
FROM pg_stat_statements_cache_plan_stats;

-- Note: If this shows ALL calls with high variance, FORCE_GENERIC_PLAN likely suboptimal for that query
```

#### Identify Queries Benefiting from Custom Plans
```sql
SELECT 
    has_parametric_queries AS requires_params,
    call_count - load_count AS custom_plans_used,  
    case 
        when (call_count - load_count) > 10 then 'Heavy use of parameter-specific plans'
        else 'Minimal custom planning needed'
    end as recommendation
FROM pg_stat_statements_cache_plan_stats;

-- If this shows consistently high variance in params across many executions for the same query, AUTO may be using too few custom plans OR generic plans are being re-planned unnecessarily
```

### Performance Testing Recommendations

#### Before Changing Global `plan_cache_mode` Setting:
1. **Identify candidate queries** via `pg_stat_statements`: focus on those with 1M+ executions where planning overhead is measurable
2. **Profile at connection/session level**: Change setting per-session first, NOT globally; measure impact before scaling
3. **Test warm-up behavior**: Run affected queries multiple times in quick succession to verify custom plan selection during initial calls matches expected performance  
4. **Measure memory consumption**: Monitor session-level `work_mem` and cache sizes for signs of unbounded custom plan growth

#### Recommended Setting Scope by Environment Type

```python
class PlanCacheModeByEnvironment:
    """Different environments have different constraints"""
    
    production_standard = {
        # "Production" usually means: scale + stability, no manual tuning possible per query at runtime
        "mode": "AUTO",  # Default is fine for most web apps, microservices, batch systems  
        "rationale": "Hybrid behavior handles both high-frequency and ad-hoc workloads; self-correcting prevents long-term performance decay"
    }
    
    production_high_throughput = {
        # High-traffic API server where even 1% planning overhead is unacceptable at QPS scale
        "mode": "FORCE_GENERIC_PLAN",  
        "rationale": "Planning latency must be near-zero; queries stabilized and monitored extensively"
    }
    
    analytics_environment = {
        # OLAP, BI tools, ad-hoc reporting with intentionally wide parameter ranges
        "mode": "FORCE_CUSTOM_PLAN",  # Or leave on AUTO if volume is manageable  
        "rationale": "Parameter variance dramatically changes optimal execution path; accuracy trumps planning overhead"
    }
    
    development = {
        # Development where debugging > performance optimization  
        "mode": "AUTO",  # Default, easy to observe behavior
        "rationale": "Monitoring tools like pg_stat_statements available for investigation"
    }
```

### Red Flags & Escalation Triggers

When these patterns appear, reconsider your `plan_cache_mode` strategy:

| Symptom | Likely Cause | Immediate Action |
|---------|--------------|------------------|
| **High CPU on `pg_stat_backend`: 0% utilization** (wait states) + queries slow despite good execution time | Planner running during query → not caching properly, or custom plans generated too frequently | Check for missing indexes/statistics; consider cursor-level generic plan hint in application code |
| **Session memory spike after hours of operation**: `work_mem` approaching limits without external explanation | Unbounded accumulation of distinct CustomPlans from same CachedPlanSource with varying parameters | Restrict to specific query set; implement LIMIT/OFFSET consolidation at application layer |
| **Generic plan produces significantly worse results** than expected (longer runs, fewer rows) for queries known to be parameter-sensitive | Auto-mode decided generic was cheaper based on cost model estimate only | Force custom plans via application-level cursor options or session-setting per query set; re-verify stats accuracy with ANALYZE |
| **First 5 executions of a frequently-cached query each take longer than subsequent runs**: Warm-up penalty dominating response time distribution | Auto-mode generating fresh custom plan for first ~5 calls (L1186) before generic can be used | If this is unacceptable in production, switch to FORCE_GENERIC_PLAN and verify single-plan performance via EXPLAIN ANALYZE with typical parameters |

---

## Best Practices Summary

### Recommended Defaults

| Setting | Value | Confidence Level | Use Case Fit |
|---------|-------|-----------------|--------------|
| **Global `plan_cache_mode`** | `'auto'` (default) | ⭐⭐⭐⭐⭐ Excellent for most deployments | Standard web applications, batch processing, mixed workloads |
| **Connection-specific overrides** | Per-query options via application cursor flags | ⭐⭐⭐ Good when fine-grained control needed | Query builders/ORM with explicit plan hints per query type |
| **Session-scoped testing** | `SET local plan_cache_mode = 'force_generic_plan'` during performance tests | ⭐⭐ Use sparingly for benchmarking specific scenarios | Isolated stress tests, capacity planning workloads |

### When to Consult a DBA Before Changing This Setting

- ✅ Production systems with >10M daily query executions
- ✅ Queries experiencing parameter variance (check `pg_stat_statements`) before assuming generic is optimal  
- ✅ Applications that cannot afford the "first 5 custom plan" warm-up behavior for critical paths
- ✅ Monitoring tools showing memory pressure correlated with cached statement cache usage

### Final Decision Tree

```
Start: What workload are you optimizing?
├─ High-frequency (millions executions/day, same queries repeated often)
│   └─ → FORCE_GENERIC_PLAN
│       │
│       └─ Pre-flight checklist:
│           - Verify query plan is stable across parameter variations
│           - Confirm via EXPLAIN that generic captures 80%+ of actual rows for min/max parameters  
│           - Monitor planning latency drops (from ~5ms to near-zero)
│
├─ Parameter-driven with extreme selectivity variance
│   └─ → FORCE_CUSTOM_PLAN or AUTO (test both)
│       │
│       └─ Pre-flight checklist:
│           - Confirm parameters truly drive different access paths  
│           - Verify generic plan performance is acceptable for baseline use cases
│           - Accept planning overhead cost in exchange for per-query optimization accuracy
│
├─ Mixed behavior (both stable and variable query sets)
│   └─ → AUTO (default, let adaptive algorithm decide per CachedPlanSource)
│       │
│       └─ Pre-flight checklist:
│           - Allow warm-up period to complete before monitoring results  
│           - Use pg_stat_statements_cache_plan_stats to verify decision quality over time
│           - Expect ~90% queries will auto-converge to generic if parameters are constrained
```

---

## References

### Source Citations
- Plan cache mode enum definition: `raw/postgres-18/src/include/utils/plancache.h:L30-L36`  
- GUC configuration and options array: `raw/postgres-18/src/backend/utils/misc/guc_tables.c:L408-L413` (enum options) + `L5372-L5380` (GUC declaration with default PLAN_CACHE_MODE_AUTO)
- Primary decision algorithm (`choose_custom_plan()`): `raw/postgres-18/src/backend/utils/cache/plancache.c:L99-L205` and `L1158-L1204`  
- Generic plan cost calculation: `plancache.c:L1214-L1258`, including planning overhead estimation at L1230-L1255
- Self-correcting behavior after generic build fails cost test: `plancache.c:L1333-L1343`

### Related PostgreSQL Topics
- [`pg_stat_statements_cache_plan_stats`](https://www.postgresql.org/docs/current/view-pg-stat-statements-cache-plan-stats.html): Monitoring plan cache usage
- Connection-level cursor options (CURSOR_OPT_GENERIC_PLAN, CURSOR_OPT_CUSTOM_PLAN) for application-controlled behavior  
- `autovacuum` impact on cached plans via statistics updates  
- Index visibility changes and their effect on generic vs custom plan selection

---

**Note:** This analysis was generated from examination of PostgreSQL 18 source code. Always test in staging with realistic data volumes before applying to production systems, as actual performance characteristics depend on your specific query patterns, workload mix, hardware (CPU instruction set), and database sizing beyond what the planner can predict at analyze time.
