---
type: question
verified: false
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# `plan_cache_mode` Production Impact

## Question

In PostgreSQL 18, how do the different `plan_cache_mode` values impact a
production workload, and which mode is the right choice for which scenario?
Pros and cons per mode.

## Short Answer

Assume PostgreSQL 18, the primary version in [[versions]]. `plan_cache_mode`
only steers one specific decision: for a parameterized cached plan source
(`PrepareQuery`, extended-protocol `Parse`, PL/pgSQL implicit prepared
statements, SPI plans), should the next execution use a freshly built
**custom plan** for those parameter values, or a reusable **generic plan**
that ignores them. It does not turn the plan cache on or off, and it does
not affect parameterless statements, one-shot plans, utility statements, or
statements whose `StmtPlanRequiresRevalidation` returns false. Citations:
`raw/postgres-18/src/backend/utils/cache/plancache.c:choose_custom_plan`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:GetCachedPlan`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:StmtPlanRequiresRevalidation`,
`raw/postgres-18/src/include/utils/plancache.h:PlanCacheMode`,
`raw/postgres-18/src/backend/utils/misc/guc_tables.c:plan_cache_mode_options`.

The three values from `PlanCacheMode` are `auto` (default),
`force_generic_plan`, and `force_custom_plan`. The GUC is `PGC_USERSET`,
so it can be set per session, per user, per database, or per transaction.
In production the practical question is: does the *shape* of the best plan
depend strongly on the bound parameter values? If yes, prefer
`force_custom_plan` (skewed columns, `IN`-lists with variable cardinality,
range predicates against very non-uniform data, partition pruning that
needs the literal). If no, prefer `force_generic_plan` (high-frequency
OLTP point lookups on uniform PK/unique indexes where planning cost is the
bottleneck). For everything else, `auto` is the right default. Citations:
`raw/postgres-18/src/include/utils/plancache.h:PlanCacheMode`,
`raw/postgres-18/src/backend/utils/misc/guc_tables.c:5372`,
`raw/postgres-18/doc/src/sgml/config.sgml:6540`,
`raw/postgres-18/doc/src/sgml/ref/prepare.sgml:127`.

## Where The Setting Is Read

`plan_cache_mode` is the GUC `int plan_cache_mode = PLAN_CACHE_MODE_AUTO`
in `plancache.c`. It is read in exactly one place during plan selection:
`choose_custom_plan`, called from `GetCachedPlan` on every execution that
goes through the plan cache. Citations:
`raw/postgres-18/src/backend/utils/cache/plancache.c:138`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:1174`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:1176`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:1280`.

The decision tree inside `choose_custom_plan` runs in this order
(`plancache.c:1157-1205`):

1. `is_oneshot` → custom (oneshot plans are always custom and skip the
   cache machinery).
2. `boundParams == NULL` → generic ("never any point in a custom plan if
   there's no parameters").
3. `!StmtPlanRequiresRevalidation(plansource)` → generic (utility, `SET`,
   transaction control, empty statements).
4. `plan_cache_mode == FORCE_GENERIC_PLAN` → generic.
5. `plan_cache_mode == FORCE_CUSTOM_PLAN` → custom.
6. `cursor_options & CURSOR_OPT_GENERIC_PLAN` → generic.
7. `cursor_options & CURSOR_OPT_CUSTOM_PLAN` → custom.
8. `num_custom_plans < 5` → custom (first five executions are always
   custom so the planner can collect a baseline cost).
9. Compare `plansource->generic_cost` against
   `plansource->total_custom_cost / plansource->num_custom_plans`; pick
   generic if it is cheaper, otherwise custom.

Two consequences of that ordering matter in production:

- Modes 4 and 5 (`force_generic_plan`, `force_custom_plan`) are a hard
  override of the heuristic, but only for cached plans that are
  *parameterized and require revalidation*. They cannot, for example,
  promote a `SET` statement plan, or force a custom plan for a `PREPARE`
  with no `$N` parameters.
- Steps 6-7 let SPI/PL/pgSQL pin a specific plan kind per statement at
  parse time using `CURSOR_OPT_GENERIC_PLAN` / `CURSOR_OPT_CUSTOM_PLAN`,
  and the GUC checks come before those flags - so a session-level
  `force_generic_plan` overrides a function that asked for a custom plan.

Citations:
`raw/postgres-18/src/backend/utils/cache/plancache.c:1157-1205`,
`raw/postgres-18/src/include/nodes/parsenodes.h:3388-3389`,
`raw/postgres-18/doc/src/spi.sgml:1107-1108`.

After building a brand-new generic plan, `GetCachedPlan` re-runs
`choose_custom_plan` with the now-known `generic_cost`. If that second
check picks custom, the just-built generic plan is discarded and a
custom plan is built instead - this is the "wart" comment in the source
and is worth knowing because under `force_custom_plan` it cannot fire
(force_custom always returns true at step 5), and under
`force_generic_plan` the second check is also short-circuited at step 4.
Citations: `raw/postgres-18/src/backend/utils/cache/plancache.c:1330-1352`.

## What `auto` Actually Costs

`auto` charges custom plans for planning effort but charges generic
plans only for execution. `cached_plan_cost` adds
`1000 * cpu_operator_cost * (nrelations + 1)` per `PlannedStmt` when
`include_planner` is true - which is true for the per-execution
`total_custom_cost` accumulator and false for `generic_cost`. So a
generic plan only has to be cheaper than the *execution + planning* cost
of an average custom plan to win. For trivial OLTP statements with a
single rangetable entry the planning charge is small but still tilts the
comparison toward generic; for larger joins it tilts more strongly.
Citations:
`raw/postgres-18/src/backend/utils/cache/plancache.c:1214-1259`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:1356-1361`.

`auto` is also locked into "first five executions are custom, then
maybe-switch". Sources of a *single* plan source that flip back and
forth between fast and slow parameter values will not reset the counter
on a bad switch - once `num_custom_plans >= 5` the comparison is the
only gate. Workloads where the first five values happen to be
non-representative will get a misleading baseline. Citations:
`raw/postgres-18/src/backend/utils/cache/plancache.c:1185-1204`.

## Mode-by-Mode Production Analysis

### `auto` (default, `PLAN_CACHE_MODE_AUTO`)

How it behaves: first five executions of a parameterized prepared
statement build custom plans, then PostgreSQL builds a generic plan and
keeps using it as long as its estimated cost stays under the average
custom cost. Generic plan stays cached until invalidated by
sinval/DDL/statistics or `DISCARD PLANS`. Citations:
`raw/postgres-18/src/backend/utils/cache/plancache.c:choose_custom_plan`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:GetCachedPlan`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:cached_plan_cost`,
`raw/postgres-18/doc/src/sgml/ref/prepare.sgml:142-153`.

Pros:

- Workload-agnostic default: small statements amortize planning, large
  statements that benefit from parameter-aware estimates keep getting
  custom plans because the heuristic compares costs.
- Self-correcting: a query whose generic-cost estimate looks fine but
  custom plans look much cheaper stays on custom; the comparison gate
  is per-statement, not global.
- Plans are still revalidated and replanned on DDL / statistics /
  search_path changes (see [[v18/questions/prepared-statement-replanning]]).

Cons:

- Behavior changes after the fifth execution. A statement that ran fast
  in dev (custom for the first five) can switch to a worse generic plan
  in production once it has been hit enough times.
- Generic plan costs are estimates. When the planner under-estimates
  the cost of the generic plan (e.g. selectivity collapses to default
  guesses because a parameter cannot be folded into stats), `auto` can
  pick generic and execution time blows up - this is the classic
  "prepared statement got slow after a few runs" symptom.
- The first-five-custom rule means even read-only OLTP workloads that
  reconnect frequently pay full planning cost on the first five
  executions per backend before generic kicks in.

Best for: most workloads where statement shapes are mixed and the DBA
cannot reason per-query about plan stability. Keep it as the cluster
default and override per session/role/transaction for the few problem
queries.

### `force_generic_plan` (`PLAN_CACHE_MODE_FORCE_GENERIC_PLAN`)

How it behaves: at step 4 of `choose_custom_plan`, return generic. The
plan source builds one generic plan on first use and keeps reusing it
across all parameter values until invalidation. Citations:
`raw/postgres-18/src/backend/utils/cache/plancache.c:1174-1175`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:GetCachedPlan`.

Pros:

- Highest possible parse/plan amortization. Hot OLTP statements
  (single-row PK/unique lookups, fixed-shape inserts/updates by id) pay
  planning cost once per session, not five times then maybe-once-more.
- Predictable plan: the same plan is used for every parameter value.
  Easier to reason about latency tails and to capture in
  `pg_stat_statements`. No surprise switch from custom to generic
  after the fifth execution.
- Useful in connection-pooled, very high-QPS, low-cardinality-decision
  paths where the planner's choices are obvious anyway (PK fetch,
  unique-index UPSERT, single-row update).

Cons:

- Catastrophic on parameter-sensitive statements. If selectivity
  changes from 0.001 to 0.5 across parameter values, the generic plan
  is wrong half the time - and unlike `auto`, there is no comparison
  gate to fall back to custom. Skewed columns, `LIKE 'prefix%'`,
  `BETWEEN`, `IN (...)` with variable cardinality, and partition keys
  are common offenders.
- Disables partition pruning that depends on literal values (the plan
  cannot prune to a single partition when it does not know the literal
  at plan time; runtime "Subplan Removal" pruning can still help, but
  not all plan shapes get it).
- Discards the "wart" safety check at `plancache.c:1330-1352`: even if
  the generic plan turns out to look more expensive than the average
  custom, it is still used.

Best for: per-statement / per-session overrides on workloads where the
plan shape is genuinely parameter-independent and planning latency
matters. Set in `SET LOCAL plan_cache_mode = 'force_generic_plan';`
inside a function or session that runs known-stable statements; avoid
as a cluster default.

### `force_custom_plan` (`PLAN_CACHE_MODE_FORCE_CUSTOM_PLAN`)

How it behaves: at step 5 of `choose_custom_plan`, return custom. Every
execution rebuilds the plan with the current parameter values; the
generic plan is never installed and the statistics-based comparison
never runs. Plan cache still amortizes parse/analyze (the rewritten
query tree is reused) but not planning. Citations:
`raw/postgres-18/src/backend/utils/cache/plancache.c:1176-1177`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:BuildCachedPlan`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:RevalidateCachedQuery`.

Pros:

- Always uses the best plan the planner can produce for the *actual*
  parameter values. No risk of a stale generic plan being chosen for a
  selectivity it was not built for.
- Effectively turns prepared statements into "parse-once, plan-each"
  with the ergonomic benefits of `PREPARE`/extended-protocol `Bind`
  (no SQL injection risk from string concatenation, server-side binds,
  pg_stat_statements normalization stays clean) without the plan
  stability footgun.
- Easiest knob to reach for when an existing prepared statement has
  started returning a bad plan in production - a per-session
  `SET plan_cache_mode = 'force_custom_plan'` immediately reverts to
  literal-aware planning while a longer-term fix is found.

Cons:

- Pays the full planning cost on every execution. For a high-QPS
  primary-key fetch this can dominate end-to-end latency, especially
  for plans with many joins where planner cost grows non-linearly.
- Defeats one of the main reasons applications use prepared statements
  in the first place. If your motivation for `PREPARE` was planning
  amortization, this mode reads as "give up on that".
- Plan cache memory savings disappear on the generic-plan side: each
  execution allocates and frees a `CachedPlan` (saved plansources still
  live, but `gplan` stays NULL).

Best for: targeted use on parameter-skewed statements (per-query via
`SET LOCAL`, per-function via `SET plan_cache_mode = ...` in the
function definition, or per-role for an analytic role that runs
parameter-skewed reporting). Almost never the right cluster default.

## Scenario Picker

The decision is per-query, not per-cluster. The only safe cluster-wide
default is `auto`. Override locally in these patterns:

| Workload trait | Pick | Why |
|---|---|---|
| OLTP point lookups, PK / unique-index, fixed shape, very high QPS | `force_generic_plan` (per-session/role) | Planning cost dominates, plan shape never depends on the literal. |
| Reporting / analytic queries with parameter-driven selectivity, `IN`-lists, ranges, partitioned tables | `force_custom_plan` (per-statement / per-function via `SET LOCAL`) | A wrong generic plan is much more expensive than replanning. |
| Mixed OLTP with a small set of skewed offenders | `auto` cluster-wide; per-statement `force_custom_plan` for the offenders | Default heuristic is fine for the rest; override only the queries that misbehave. |
| PL/pgSQL functions where one statement is sensitive and another is not | `SET LOCAL plan_cache_mode = ...` per block, or `CURSOR_OPT_GENERIC_PLAN` / `CURSOR_OPT_CUSTOM_PLAN` per SPI plan | GUC overrides the cursor flag (steps 4-5 run before steps 6-7), so a function-level `SET LOCAL` is the strongest local override. |
| One-shot ad-hoc SQL through `PQexec` / simple Query protocol | Setting has no effect | Goes through one-shot plans, which `choose_custom_plan` returns custom for at step 1 unconditionally. |
| Prepared statement with no parameters (`PREPARE x AS SELECT now();`) | Setting has no effect | Step 2 returns generic regardless of GUC. |

Citations:
`raw/postgres-18/src/backend/utils/cache/plancache.c:choose_custom_plan`,
`raw/postgres-18/src/backend/utils/cache/plancache.c:CreateOneShotCachedPlan`,
`raw/postgres-18/src/include/nodes/parsenodes.h:3388-3389`,
`raw/postgres-18/doc/src/sgml/spi.sgml:1107-1108`.

## Operational Notes

- The GUC is `PGC_USERSET`, so it can be changed at runtime by any role.
  Changes affect only *future* `GetCachedPlan` calls - there is no
  invalidation when the GUC changes, so an already-installed generic
  plan will keep being returned by `CheckCachedPlan` if it is still
  valid, even after switching to `force_custom_plan`. To force
  immediate replanning in the current session, follow the `SET` with
  `DISCARD PLANS;` (`ResetPlanCache`). Citations:
  `raw/postgres-18/src/backend/utils/misc/guc_tables.c:5372`,
  `raw/postgres-18/src/backend/utils/cache/plancache.c:CheckCachedPlan`,
  `raw/postgres-18/src/backend/commands/discard.c:DiscardCommand`.
- `EXPLAIN EXECUTE name(...)` shows whether the current decision came
  out as generic (`$1` parameter symbols visible) or custom (literal
  values substituted). This is the simplest way to confirm what
  `plan_cache_mode` actually did. Citations:
  `raw/postgres-18/doc/src/sgml/ref/prepare.sgml:166-174`.
- `pg_prepared_statements` exposes the prepared statement set per
  session, but does not currently expose "is the cached generic plan
  installed" or "how many custom vs generic executions so far"
  (`num_custom_plans` / `num_generic_plans` are in `CachedPlanSource`
  but not surfaced through a system view). Use `auto_explain` with
  `auto_explain.log_nested_statements` for production-side diagnostics.
  Citations:
  `raw/postgres-18/src/include/utils/plancache.h:CachedPlanSource`,
  `raw/postgres-18/doc/src/sgml/ref/prepare.sgml:206-210`.
- Replanning behavior on DDL / index / statistics changes is unchanged
  by `plan_cache_mode`; see [[v18/questions/prepared-statement-replanning]].

## Source References

- `raw/postgres-18/src/include/utils/plancache.h:PlanCacheMode`
- `raw/postgres-18/src/include/utils/plancache.h:CachedPlanSource`
- `raw/postgres-18/src/include/nodes/parsenodes.h:CURSOR_OPT_GENERIC_PLAN`
- `raw/postgres-18/src/include/nodes/parsenodes.h:CURSOR_OPT_CUSTOM_PLAN`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:plan_cache_mode`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:choose_custom_plan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:cached_plan_cost`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:GetCachedPlan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:BuildCachedPlan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:CheckCachedPlan`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:RevalidateCachedQuery`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:StmtPlanRequiresRevalidation`
- `raw/postgres-18/src/backend/utils/cache/plancache.c:CreateOneShotCachedPlan`
- `raw/postgres-18/src/backend/utils/misc/guc_tables.c:plan_cache_mode_options`
- `raw/postgres-18/src/backend/utils/misc/guc_tables.c:5372`
- `raw/postgres-18/src/backend/commands/discard.c:DiscardCommand`
- `raw/postgres-18/doc/src/sgml/config.sgml:6540`
- `raw/postgres-18/doc/src/sgml/ref/prepare.sgml:127`
- `raw/postgres-18/doc/src/sgml/spi.sgml:1107`

## Open Questions

- The "first five executions are custom" threshold is a hard-coded `5`
  at `plancache.c:1186`. There is no GUC to raise it; on workloads
  whose first five parameter values are non-representative, the only
  workarounds are `force_custom_plan` or `DISCARD PLANS` after a
  warm-up window.
- `pg_prepared_statements` does not surface `num_custom_plans` /
  `num_generic_plans` / `generic_cost`. Adding a diagnostic view (or
  exposing these through `pg_stat_statements`) would make the
  per-statement choice observable in production without `auto_explain`.
