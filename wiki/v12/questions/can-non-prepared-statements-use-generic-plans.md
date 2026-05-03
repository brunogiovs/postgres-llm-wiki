---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: Cline 2026-05-03T14:06:00Z
---

# Question

In PostgreSQL 12, do non-prepared statement SQL queries like SELECT statements use generic plans?

## Short Answer

Yes, non-prepared SELECT statements can use generic plans. Generic plans in PostgreSQL's plan cache are cached query execution plans that are independent of parameter values, and they are used for both prepared and non-prepared statements when appropriate.

## Detailed Answer

PostgreSQL 12's plan cache system supports both generic and custom plans:

- **Generic plans**: Cached plans that don't depend on specific parameter values. These are stored in `CachedPlanSource->gplan` and reused when the same query is executed again.
- **Custom plans**: Plans created for specific parameter values when the generic plan would be inefficient.

For non-prepared statements (simple queries processed through the simple query protocol):

1. A `CachedPlanSource` is created for the query
2. When `GetCachedPlan()` is called, `boundParams` is `NULL` (no parameters)
3. `choose_custom_plan()` returns `false` because `boundParams == NULL`, indicating no custom plan is needed
4. The system attempts to use or create a generic plan

For prepared statements, the same mechanism applies, but `choose_custom_plan()` can decide between generic and custom plans based on parameter values and cost estimates.

## Evidence

The plan cache logic is implemented in [[raw/postgres-12/src/backend/utils/cache/plancache.c|plancache.c]]:

- [[raw/postgres-12/src/backend/utils/cache/plancache.c#choose_custom_plan|plancache.c#choose_custom_plan]] at lines 1016-1063 determines plan type selection
- For queries with no parameters (`boundParams == NULL`), it always prefers generic plans (line 1025-1026)
- [[raw/postgres-12/src/backend/utils/cache/plancache.c#GetCachedPlan|plancache.c#GetCachedPlan]] at lines 1138-1245 orchestrates plan retrieval or creation
- Generic plans are stored in `CachedPlanSource->gplan` and reused when valid

Simple queries are processed in [[raw/postgres-12/src/backend/tcop/postgres.c#exec_simple_query|postgres.c#exec_simple_query]], which calls [[raw/postgres-12/src/backend/utils/cache/plancache.c#GetCachedPlan|plancache.c#GetCachedPlan]] at line 1876, where `params` is typically `NULL` for non-prepared queries.

## Related Pages

- [[v12/questions/plan-cache-mode-production-impact]] - Analysis of plan_cache_mode settings and their impact on generic vs custom plan usage
- [[shared/concepts/planned-statement]] - Overview of planner output structures

## Follow-Up Questions

- How does PostgreSQL decide when to invalidate a cached generic plan?
- What are the performance implications of generic plans for complex queries?