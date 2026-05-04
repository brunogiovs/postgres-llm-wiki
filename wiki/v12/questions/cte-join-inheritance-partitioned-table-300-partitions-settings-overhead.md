---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: cline 2026-05-04T19:23:00Z
---

## Question

In PostgreSQL 12, for a query that uses a CTE to join a table to a table partitioned by inheritance that has 300 partitions, what are the settings and configuration that help or add overhead to this SELECT query?

## Answer

The query involves a Common Table Expression (CTE) joining to an inheritance-partitioned table with 300 partitions. Key settings affecting performance include those controlling partition pruning, join planning, memory usage, and query optimization strategies.

### Settings That Help Performance

- **constraint_exclusion = 'partition'** (default): Enables pruning of inheritance partitions based on constraints, reducing the number of partitions scanned from 300 to potentially just a few matching the join conditions. This significantly lowers planning time and execution overhead by avoiding consideration of irrelevant partitions [[raw/postgres-12/src/backend/utils/misc/guc_tables.c#5048|constraint_exclusion GUC definition]]. Requires no restart or reload; takes effect per-session.

- **work_mem**: Sufficient memory for join operations (e.g., hash tables in hash joins). For large CTE results joining to partitioned data, increasing work_mem can prevent disk spills, improving join speed [[raw/postgres-12/src/backend/utils/misc/guc_tables.c#2197|work_mem GUC definition]]. Session-scoped; no restart needed.

- **enable_hashjoin = on** (default): Allows hash joins, often efficient for CTE-to-partition joins with large datasets [[raw/postgres-12/src/backend/utils/misc/guc_tables.c#2197|enable_hashjoin GUC definition]]. Session-scoped.

- **geqo_threshold > 300**: If constraint_exclusion fails to prune effectively, the planner treats the partitioned table as ~300 relations, triggering genetic query optimization (GEQO) for join ordering. Raising geqo_threshold avoids GEQO's slower planning, but only if pruning works [[raw/postgres-12/src/backend/utils/misc/guc_tables.c#2197|geqo_threshold GUC definition]]. Session-scoped.

### Settings That Add Overhead

- **constraint_exclusion = 'off'**: Disables partition pruning, forcing the planner to consider all 300 partitions, leading to exponential planning time growth and potential GEQO activation, adding significant overhead [[raw/postgres-12/src/backend/optimizer/util/plancat.c#1655|constraint_exclusion logic in plancat.c]]. Session-scoped.

- **constraint_exclusion = 'on'**: Enables pruning for all inheritance hierarchies, but may prune too aggressively or incorrectly if constraints are misdefined, potentially missing data or adding re-planning overhead [[raw/postgres-12/src/backend/optimizer/util/plancat.c#1655|constraint_exclusion logic]].

- **work_mem** (too low): Insufficient memory causes hash joins to spill to disk, slowing the query [[raw/postgres-12/src/backend/utils/misc/guc_tables.c#2197|work_mem]].

- **enable_hashjoin = off**: Forces alternative joins like nested loops or sorts, which may be slower for large CTE-partition joins [[raw/postgres-12/src/backend/utils/misc/guc_tables.c#2197|enable_hashjoin]].

- **geqo_threshold ≤ 300**: With many partitions, GEQO activates, using genetic algorithms for join ordering, which is slower than dynamic programming but may find better plans [[raw/postgres-12/src/backend/utils/misc/guc_tables.c#2197|geqo_threshold]].

- **plan_cache_mode = 'force_custom_plan'**: For prepared statements, forces re-planning per execution, adding overhead if the CTE or partition constraints vary [[raw/postgres-12/src/backend/utils/cache/plancache.c#1176|plan_cache_mode logic]]. Session-scoped.

CTE materialization (if the CTE is complex) adds temp table overhead, but no direct GUC controls this in PostgreSQL 12; it's planner-driven.

## Open Questions

- Does the number of partitions (300) reliably trigger GEQO without pruning?
- Impact of from_collapse_limit on CTE inlining vs. materialization for partitioned joins.