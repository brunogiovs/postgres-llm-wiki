---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Query planner settings inventory and non-default sampling (unverified)

## Question

For PostgreSQL 12, give a query that retrieves all settings whose values are non-default and that relate to the query planner, including the planner settings for partitioned tables. Then, in a separate section, list every available query-planner setting and explain how each affects the planner.

## Answer

Assumption: "PostgreSQL 12" means the local source checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`.

Every planner GUC in PG 12 lives in one of four `pg_settings.category` strings, defined by `config_group_names[]` at [[raw/postgres-12/src/backend/utils/misc/guc.c#L681-L690|guc.c#L681-L690]]:

- `Query Tuning / Planner Method Configuration`
- `Query Tuning / Planner Cost Constants`
- `Query Tuning / Genetic Query Optimizer`
- `Query Tuning / Other Planner Options`

Filtering on `category LIKE 'Query Tuning%'` covers all four groups, so it captures the partitioned-table-specific GUCs (`enable_partitionwise_join`, `enable_partitionwise_aggregate`, `enable_partition_pruning`, and `constraint_exclusion`) without needing per-name lists.

`pg_settings` is the view over `pg_show_all_settings()` ([[raw/postgres-12/src/backend/catalog/system_views.sql#L512-L513|system_views.sql#L512-L513]]). It exposes the running value (`setting`) and the compiled-in default (`boot_val`) using identical formatting and units, so `setting IS DISTINCT FROM boot_val` is a reliable drift detector. Column shape is documented in `pg_proc` and the regression-test view rule [[raw/postgres-12/src/include/catalog/pg_proc.dat#pg_show_all_settings|pg_proc.dat#pg_show_all_settings]], [[raw/postgres-12/src/test/regress/expected/rules.out#L1711|rules.out#L1711]].

## Non-Default Planner Settings Query

```sql
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout      = '1s';

SELECT /* wiki_query_planner_non_default_settings */
       category,
       name,
       setting          AS current_value,
       unit,
       boot_val         AS compiled_default,
       reset_val        AS session_reset_value,
       source,
       context,
       pending_restart
  FROM pg_catalog.pg_settings
 WHERE category LIKE 'Query Tuning%'
   AND setting IS DISTINCT FROM boot_val
 ORDER BY category, name;
```

Reading the result:

- `current_value` differs from `compiled_default` exactly when something (postgresql.conf, `ALTER SYSTEM`, role/database `ALTER … SET`, env, command-line, or session `SET`) overrode the built-in value.
- `source` shows the override origin (`configuration file`, `session`, `database`, `user`, `override`, …).
- `reset_val` is what `RESET <name>` would restore for this session — usually equal to the postmaster-time value, but can differ from `boot_val` when `postgresql.conf` overrides it.
- Every GUC in the four planner categories is `PGC_USERSET` (see definitions starting at [[raw/postgres-12/src/backend/utils/misc/guc.c#L884|guc.c#L884]]). That means session/transaction-scoped `SET` applies immediately; `postgresql.conf` edits take effect on `SELECT pg_reload_conf();` (or `SIGHUP`); no restart is required for any planner GUC.

## All Available Query-Planner Settings

Defaults and ranges below are taken from `ConfigureNamesBool` / `ConfigureNamesInt` / `ConfigureNamesReal` / `ConfigureNamesEnum` in [[raw/postgres-12/src/backend/utils/misc/guc.c|guc.c]].

### Query Tuning / Planner Method Configuration

These are mostly soft "off" switches. Setting an `enable_*` to `off` does not actually remove the path; it adds `disable_cost = 1.0e10` ([[raw/postgres-12/src/include/optimizer/cost.h#disable_cost|cost.h#disable_cost]]) to that path's cost so the planner avoids it whenever an alternative exists. A path with no alternative is still chosen.

| GUC | Default | Effect on planner |
|---|---|---|
| `enable_seqscan` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_seqscan\|guc.c#L884]]) | `on` | Off penalises sequential scans; planner still picks one when no index path is feasible. |
| `enable_indexscan` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_indexscan\|guc.c#L894]]) | `on` | Off penalises ordered/index-driven scans for B-tree, GiST, SP-GiST, BRIN, etc. |
| `enable_indexonlyscan` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_indexonlyscan\|guc.c#L904]]) | `on` | Off penalises index-only scans (those that skip the heap when the visibility map allows). |
| `enable_bitmapscan` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_bitmapscan\|guc.c#L914]]) | `on` | Off penalises bitmap heap scans and bitmap AND/OR combinations of multiple indexes. |
| `enable_tidscan` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_tidscan\|guc.c#L924]]) | `on` | Off penalises direct `ctid = …` lookups. |
| `enable_sort` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_sort\|guc.c#L934]]) | `on` | Off penalises explicit `Sort` nodes; planner prefers paths that produce ordering naturally (index, merge-join input, etc.). |
| `enable_hashagg` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_hashagg\|guc.c#L944]]) | `on` | Off penalises `HashAggregate`; forces grouped aggregation through sorted `GroupAggregate`. |
| `enable_material` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_material\|guc.c#L954]]) | `on` | Off penalises adding a `Materialize` node (used to cache the inner side of nested-loop joins). Required cases are still inserted. |
| `enable_nestloop` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_nestloop\|guc.c#L964]]) | `on` | Off penalises nested-loop joins — last-resort path when no other join method is feasible. |
| `enable_mergejoin` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_mergejoin\|guc.c#L974]]) | `on` | Off penalises merge joins. |
| `enable_hashjoin` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_hashjoin\|guc.c#L984]]) | `on` | Off penalises hash joins. |
| `enable_gathermerge` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_gathermerge\|guc.c#L994]]) | `on` | Off penalises `Gather Merge` (parallel plan keeping per-worker ordering); planner falls back to plain `Gather`. |
| `enable_partitionwise_join` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_partitionwise_join\|guc.c#L1004]]) | `off` | When on (and partition keys match), the planner joins matching partitions pairwise instead of joining whole tables. Off skips the alternative. The off-by-default reflects extra planning time and memory cost. |
| `enable_partitionwise_aggregate` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_partitionwise_aggregate\|guc.c#L1014]]) | `off` | When on, aggregation can be pushed into each partition and merged afterward; off keeps aggregation above `Append`. |
| `enable_parallel_append` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_parallel_append\|guc.c#L1024]]) | `on` | Off prevents `Parallel Append` (running multiple `Append` children concurrently across workers); `Append` stays serial inside each worker. |
| `enable_parallel_hash` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_parallel_hash\|guc.c#L1034]]) | `on` | Off prevents shared-memory parallel hash builds; parallel hash joins must build a private hash table per worker. |
| `enable_partition_pruning` ([[raw/postgres-12/src/backend/utils/misc/guc.c#enable_partition_pruning\|guc.c#L1044]]) | `on` | Controls plan-time pruning (eliminate partitions during planning) and run-time pruning (eliminate partitions during executor init or per-tuple parameter changes). Off forces visiting every child partition. Applies only to declarative-partition tables; legacy inheritance children rely on `constraint_exclusion`. |
| `optimize_bounded_sort` ([[raw/postgres-12/src/backend/utils/misc/guc.c#L1666\|guc.c#L1666]]) | `on` (only when `DEBUG_BOUNDED_SORT` is compiled in) | Developer-build flag toggling top-N heap sort versus regular sort for bounded sorts. Not present in standard builds (`GUC_NOT_IN_SAMPLE`). |

### Query Tuning / Planner Cost Constants

These knobs change the *shape* of cost estimates. They scale paths against each other — only ratios matter, not absolute values.

| GUC | Default | Effect on planner |
|---|---|---|
| `seq_page_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#seq_page_cost\|guc.c#L3207]]) | `1.0` | Cost of a sequentially read 8-kB page. The reference unit; usually left at 1.0 with other costs tuned relative to it. |
| `random_page_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#random_page_cost\|guc.c#L3218]]) | `4.0` | Cost of a random-access page. Lowering it (e.g. to 1.1 on SSD) makes index scans look cheaper relative to seq scans. |
| `cpu_tuple_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#cpu_tuple_cost\|guc.c#L3229]]) | `0.01` | Cost charged per tuple processed in any plan node. Raising it makes wide / row-heavy scans look more expensive relative to filtered ones. |
| `cpu_index_tuple_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#cpu_index_tuple_cost\|guc.c#L3240]]) | `0.005` | Cost per index entry examined during an index scan. Raising it suppresses wide-range index scans. |
| `cpu_operator_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#cpu_operator_cost\|guc.c#L3251]]) | `0.0025` | Cost per operator/function call evaluated. Influences expression-heavy paths. |
| `parallel_tuple_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#parallel_tuple_cost\|guc.c#L3262]]) | `0.1` | Per-tuple cost of shipping a row from a worker to the leader. Higher values discourage parallel plans whose output is large. |
| `parallel_setup_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#parallel_setup_cost\|guc.c#L3273]]) | `1000.0` | Fixed overhead charged for spinning up workers. Higher values prevent parallelism on small queries. |
| `effective_cache_size` ([[raw/postgres-12/src/backend/utils/misc/guc.c#effective_cache_size\|guc.c#L3108]]) | `4 GB` (`524288` × 8-kB blocks) | Planner's *assumption* about combined OS file cache plus `shared_buffers`. Used in index-scan costing (especially for repeated lookups) — larger values make index scans look cheaper. Allocates no memory. |
| `min_parallel_table_scan_size` ([[raw/postgres-12/src/backend/utils/misc/guc.c#min_parallel_table_scan_size\|guc.c#L3120]]) | `8 MB` (`1024` blocks) | Below this estimated read size, the planner does not consider a parallel sequential scan. |
| `min_parallel_index_scan_size` ([[raw/postgres-12/src/backend/utils/misc/guc.c#min_parallel_index_scan_size\|guc.c#L3131]]) | `512 kB` (`64` blocks) | Same idea for parallel index scans. |
| `jit_above_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#jit_above_cost\|guc.c#L3285]]) | `100000` | Total estimated query cost beyond which JIT is enabled. `-1` disables JIT entirely (tighter than `jit = off` because it short-circuits before code generation). |
| `jit_optimize_above_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#jit_optimize_above_cost\|guc.c#L3296]]) | `500000` | Threshold for additional LLVM optimisation passes once JIT is active. `-1` disables. |
| `jit_inline_above_cost` ([[raw/postgres-12/src/backend/utils/misc/guc.c#jit_inline_above_cost\|guc.c#L3307]]) | `500000` | Threshold for inlining function bodies into JITed code. `-1` disables. |

### Query Tuning / Genetic Query Optimizer

GEQO replaces the deterministic dynamic-programming join search with a genetic algorithm when the FROM list is large, trading optimality for planning time.

| GUC | Default | Effect on planner |
|---|---|---|
| `geqo` ([[raw/postgres-12/src/backend/utils/misc/guc.c#geqo\|guc.c#L1056]]) | `on` | Master switch. Off forces exhaustive search regardless of `geqo_threshold`, which can become very expensive for big joins. |
| `geqo_threshold` ([[raw/postgres-12/src/backend/utils/misc/guc.c#geqo_threshold\|guc.c#L2022]]) | `12` | Minimum FROM-list size at which GEQO replaces exhaustive search. Raise to delay handing off to GEQO. |
| `geqo_effort` ([[raw/postgres-12/src/backend/utils/misc/guc.c#geqo_effort\|guc.c#L2032]]) | `5` (1–10) | Convenience knob that derives defaults for `geqo_pool_size` and `geqo_generations`. Higher = better plans, more planning time. |
| `geqo_pool_size` ([[raw/postgres-12/src/backend/utils/misc/guc.c#geqo_pool_size\|guc.c#L2042]]) | `0` (auto from `geqo_effort`) | Population size of the genetic algorithm. |
| `geqo_generations` ([[raw/postgres-12/src/backend/utils/misc/guc.c#geqo_generations\|guc.c#L2052]]) | `0` (auto from `geqo_effort`) | Number of generations the GA runs. |
| `geqo_selection_bias` ([[raw/postgres-12/src/backend/utils/misc/guc.c#geqo_selection_bias\|guc.c#L3330]]) | `2.0` (1.5–2.0) | Selective pressure within the population. Higher = faster convergence with more variance. |
| `geqo_seed` ([[raw/postgres-12/src/backend/utils/misc/guc.c#geqo_seed\|guc.c#L3341]]) | `0.0` | Seed for GEQO's RNG. Set deterministically to make GEQO plan choices reproducible. |

### Query Tuning / Other Planner Options

| GUC | Default | Effect on planner |
|---|---|---|
| `default_statistics_target` ([[raw/postgres-12/src/backend/utils/misc/guc.c#default_statistics_target\|guc.c#L1986]]) | `100` | Default histogram/MCV resolution for `ANALYZE` on columns without an explicit `ALTER TABLE … SET STATISTICS`. Higher values give finer selectivity estimates at the cost of bigger `pg_statistic` rows and slower `ANALYZE`/planning. Affects the planner indirectly via the statistics costing functions read. |
| `from_collapse_limit` ([[raw/postgres-12/src/backend/utils/misc/guc.c#from_collapse_limit\|guc.c#L1996]]) | `8` | Max FROM-list size at which sub-queries get pulled up into the parent query. Lower values keep sub-queries opaque (fewer join orderings considered). Indirectly bounds the join-search size. |
| `join_collapse_limit` ([[raw/postgres-12/src/backend/utils/misc/guc.c#join_collapse_limit\|guc.c#L2009]]) | `8` | Max FROM-list size at which explicit `JOIN` clauses get flattened into a single FROM list. Setting to `1` forces the planner to honour the user's join order verbatim. |
| `cursor_tuple_fraction` ([[raw/postgres-12/src/backend/utils/misc/guc.c#cursor_tuple_fraction\|guc.c#L3318]]) | `0.1` | Fraction of a `DECLARE CURSOR` result the planner assumes will actually be fetched. Lower values bias plans toward fast-start (e.g. NestLoop with index) over fast-total (HashJoin). |
| `constraint_exclusion` ([[raw/postgres-12/src/backend/utils/misc/guc.c#constraint_exclusion\|guc.c#L4243]]) | `partition` | Allowed values defined at [[raw/postgres-12/src/backend/utils/misc/guc.c#L367-L378\|guc.c#L367-L378]]. `on` always evaluates `CHECK` constraints to prove a child can be pruned (most expensive at plan time); `partition` only does so for legacy inheritance children and `UNION ALL` subqueries; `off` disables constraint-based exclusion entirely. Declarative partitioning uses `enable_partition_pruning`, not this GUC. |
| `force_parallel_mode` ([[raw/postgres-12/src/backend/utils/misc/guc.c#force_parallel_mode\|guc.c#L4481]]) | `off` | Allowed values at [[raw/postgres-12/src/backend/utils/misc/guc.c#L416-L427\|guc.c#L416-L427]]. `on` makes the planner add a `Gather` over the top of any parallel-safe plan even when costs say otherwise — a testing/debugging knob, not a performance feature. `regress` is for the regression suite. Does not lift any parallel-restriction rules. |
| `plan_cache_mode` ([[raw/postgres-12/src/backend/utils/misc/guc.c#plan_cache_mode\|guc.c#L4504]]) | `auto` | Allowed values at [[raw/postgres-12/src/backend/utils/misc/guc.c#L429-L433\|guc.c#L429-L433]]. Controls custom-vs-generic plan choice for parameterised prepared statements. `force_custom_plan` re-plans every execution with the supplied parameter values; `force_generic_plan` keeps a single parameter-agnostic plan. Production trade-offs are covered in [[v12/questions/plan-cache-mode-production-impact]]. |
| `jit` ([[raw/postgres-12/src/backend/utils/misc/guc.c#jit\|guc.c#L1869]]) | `on` | Master enable for LLVM JIT compilation. With `on`, JIT activates only when total estimated query cost crosses `jit_above_cost`. Off skips JIT entirely; `jit_above_cost = -1` is functionally equivalent for runtime queries. |

## Reload Semantics

All planner GUCs above are `PGC_USERSET`, visible from the third field of every `{...}` entry in [[raw/postgres-12/src/backend/utils/misc/guc.c|guc.c]] starting at [[raw/postgres-12/src/backend/utils/misc/guc.c#L884|L884]]. The mapping documented in `AGENTS.md` for context values applies:

- `postmaster` -> restart required.
- `sighup` -> reload required.
- `superuser` / `user` / `backend` -> session/transaction scope, no restart, no reload beyond changing defaults.

Because every entry above uses `PGC_USERSET`, no planner GUC requires a restart; `postgresql.conf` changes take effect on `SELECT pg_reload_conf();`, and session/transaction `SET` (or `SET LOCAL`) applies immediately.

## Context Reviewed

- `wiki/versions.md` confirmed v12 pin `45b88269a353ad93744772791feb6d01bc7e1e42`.
- `wiki/v12/index.md` reviewed for adjacent question pages and naming conventions.
- `scripts/source_graph_query --version 12 symbol 'QUERY_TUNING' --regex` enumerated every `QUERY_TUNING_*` GUC entry in [[raw/postgres-12/src/backend/utils/misc/guc.c|guc.c]].
- `scripts/source_graph_query --version 12 file src/backend/utils/misc/guc.c` reads (lines 880-1060, 1660-1680, 1860-1890, 1980-2070, 3100-3360, 4240-4520) inspected to confirm category, default, and short description for each planner GUC.
- `scripts/source_graph_query --version 12 file src/backend/catalog/system_views.sql` lines 510-540 confirmed `pg_settings` is a view over `pg_show_all_settings()`.
- `scripts/source_graph_query --version 12 symbol 'pg_show_all_settings'` confirmed the column list via `pg_proc.dat` and `rules.out`.
- Existing v12 question page [[v12/questions/plan-cache-mode-production-impact]] reviewed for the established structure and citation style.

## Evidence Map

| Claim | Source |
|---|---|
| Four planner category strings (`Query Tuning / *`) | [[raw/postgres-12/src/backend/utils/misc/guc.c#L681-L690\|guc.c#L681-L690]] |
| `pg_settings` is a view over `pg_show_all_settings()` | [[raw/postgres-12/src/backend/catalog/system_views.sql#L512-L513\|system_views.sql#L512-L513]] |
| `pg_settings` columns | [[raw/postgres-12/src/include/catalog/pg_proc.dat#pg_show_all_settings\|pg_proc.dat]], [[raw/postgres-12/src/test/regress/expected/rules.out#L1711\|rules.out#L1711]] |
| `enable_*` GUCs add `disable_cost = 1.0e10` rather than removing paths | [[raw/postgres-12/src/include/optimizer/cost.h#disable_cost\|cost.h#disable_cost]] |
| Each `enable_*` GUC | individual entries in [[raw/postgres-12/src/backend/utils/misc/guc.c#L884-L1054\|guc.c#L884-L1054]] |
| `optimize_bounded_sort` is `DEBUG_BOUNDED_SORT`-only and `GUC_NOT_IN_SAMPLE` | [[raw/postgres-12/src/backend/utils/misc/guc.c#L1662-L1675\|guc.c#L1662-L1675]] |
| `jit` GUC default and category | [[raw/postgres-12/src/backend/utils/misc/guc.c#L1869-L1876\|guc.c#L1869-L1876]] |
| Cost constants with defaults | [[raw/postgres-12/src/backend/utils/misc/guc.c#L3107-L3315\|guc.c#L3107-L3315]] |
| GEQO ints / reals | [[raw/postgres-12/src/backend/utils/misc/guc.c#L2022-L2059\|guc.c#L2022-L2059]], [[raw/postgres-12/src/backend/utils/misc/guc.c#L3330-L3348\|guc.c#L3330-L3348]] |
| `default_statistics_target`, `from_collapse_limit`, `join_collapse_limit`, `cursor_tuple_fraction` | [[raw/postgres-12/src/backend/utils/misc/guc.c#L1986-L2019\|guc.c#L1986-L2019]], [[raw/postgres-12/src/backend/utils/misc/guc.c#L3318-L3326\|guc.c#L3318-L3326]] |
| `constraint_exclusion` enum + default | [[raw/postgres-12/src/backend/utils/misc/guc.c#L4243-L4252\|guc.c#L4243-L4252]], [[raw/postgres-12/src/backend/utils/misc/guc.c#L367-L378\|guc.c#L367-L378]] |
| `force_parallel_mode` enum + default | [[raw/postgres-12/src/backend/utils/misc/guc.c#L4481-L4489\|guc.c#L4481-L4489]], [[raw/postgres-12/src/backend/utils/misc/guc.c#L416-L427\|guc.c#L416-L427]] |
| `plan_cache_mode` enum + default | [[raw/postgres-12/src/backend/utils/misc/guc.c#L4504-L4514\|guc.c#L4504-L4514]], [[raw/postgres-12/src/backend/utils/misc/guc.c#L429-L433\|guc.c#L429-L433]] |
| All planner GUCs are `PGC_USERSET` | every `{` block under the `QUERY_TUNING_*` category in [[raw/postgres-12/src/backend/utils/misc/guc.c\|guc.c]] |

## Open Questions

- The page lists `disable_cost = 1.0e10` based on the C macro definition, but does not separately verify that every `enable_*` path uses it through `add_path()` / cost accumulation. A targeted source pass through `costsize.c` and `pathnode.c` for each disable site would tighten the "soft switch" claim per path type.
- Default values for `geqo_effort`, `geqo_selection_bias`, and `geqo_pool_size` come from macros in `optimizer/geqo.h` not directly read here. The page reports the values produced by `pg_settings` at runtime; the macro values themselves should be confirmed in [[raw/postgres-12/src/include/optimizer/geqo.h|geqo.h]] before any verification stamp.
