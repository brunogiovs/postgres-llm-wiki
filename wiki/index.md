# Wiki Index

This is the global catalog for the PostgreSQL engine wiki.

## Entry Points

- [[versions]] - PostgreSQL version index and source pin manifest.
- [[overview]] - Cross-version architecture overview.
- [[log]] - Chronological activity log.
- [[operations/agent]] - Project-local Hermes install and start/stop runbook for the wiki maintainer agent.

## Version-Specific Pages

### PostgreSQL 18

- [[v18/index]] - Primary version landing page. Source checkout pinned to `REL_18_STABLE` commit `6cb307251c5c6261286c1566496920976640108e`; Graphify graph artifacts live under `.wiki-runtime/graph/postgres-18/`.



### PostgreSQL 12.2

- [[v12/index]] - Legacy version landing page. Source checkout pinned to `REL_12_STABLE` commit `45b88269a353ad93744772791feb6d01bc7e1e42`; Graphify graph artifacts live under `.wiki-runtime/graph/postgres-12/`.
- [[v12/questions/azure-disk-configuration-recommendations|Azure disk configuration recommendations (unverified)]] - Source-grounded PG 12 configuration recommendations for Ultra Disk, Premium SSD v2, Premium SSD, Standard SSD, and Standard HDD storage classes, covering planner storage costs, `effective_io_concurrency`, checkpoints/WAL, bgwriter/writeback, temp spill placement, durability settings, rollout scope, and production-safe inventory queries.
- [[v12/questions/bgwriter-tuning-recommendations|Bgwriter tuning recommendations]] - Agent-reviewed PG 12 direction-of-change matrix for the four bgwriter GUCs (`bgwriter_delay`, `bgwriter_lru_maxpages`, `bgwriter_lru_multiplier`, `bgwriter_flush_after`) across the main tuning scenarios, with verified `pg_stat_bgwriter` counter wiring and practical backend-write-share threshold bands for iterative tuning.
- [[v12/questions/checkpoint-monitoring-optimization-scenarios|Checkpoint monitoring and optimization scenarios]] - Agent-reviewed PG 12 checkpoint monitoring and tuning workflow using `pg_stat_bgwriter`, `log_checkpoints`, a `pg_settings` checkpoint-configuration inventory query, checkpoint/WAL GUC reload semantics, and deployment scenarios for fast local disks and cloud block storage.
- [[v12/questions/disk-io-before-after-query-plan-execution|Disk I/O before/after query planning and execution]] - Agent-reviewed PG 12 query-lifecycle I/O map covering catalog and relcache access, planner relation-size probes, shared-buffer hits versus storage reads, DML writes, hint bits, temp spills, WAL flushes, bgwriter/checkpointer writes, DDL/maintenance file operations, and the exact `track_io_timing` boundary around `smgrread` / `smgrwrite`.
- [[v12/questions/enable-io-timing-measurements-production|Enable I/O timing measurements on production]] - Production procedure for enabling PG 12 `track_io_timing`, including host timing preflight, reload/session semantics, tagged SQL sampling, `pg_stat_database`, optional `pg_stat_statements`, and `EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)` interpretation.
- [[v12/questions/inheritance-partition-no-pruning-overhead|Inheritance partition query overhead when no pruning is possible]] - Source-grounded overhead matrix for PG 12 traditional inheritance partitioning when no child tables can be pruned, covering `constraint_exclusion`, `force_generic_plan` planning-versus-execution impact, generic/custom plans, indexes/stats, planner cost knobs, parallel append, JIT, and instrumentation overhead.
- [[v12/questions/planning-metrics-generic-custom-replans|Planning metrics and generic/custom replanning visibility (unverified)]] - Source-grounded PG 12 inventory of planning visibility surfaces, covering `EXPLAIN EXECUTE`, `pg_prepared_statements`, `pg_stat_statements`, `log_planner_stats`, `auto_explain`, plan-cache invalidation, and why exact generic/custom transition counts are not exposed by built-in SQL views.
- [[v12/questions/plan-cache-mode-production-impact|Plan cache mode production impact (unverified)]] - Source-grounded PG 12 analysis of `plan_cache_mode` in production, covering `auto`, `force_custom_plan`, `force_generic_plan`, `CheckCachedPlan()` generic-plan validation, prepared-statement and PL/pgSQL/SPI boundaries, pros/cons by scenario, and slow random I/O storage.
- [[v12/questions/query-planner-settings-non-default-and-inventory|Query planner settings inventory and non-default sampling (unverified)]] - Production-safe `pg_settings` query for non-default planner GUCs across all four `Query Tuning / *` categories (including partitioned-table GUCs) plus a per-GUC inventory with defaults, ranges, enum options, and planner effects.
- [[v12/questions/wal-separate-disk-full-replication-slots|WAL on a separate full disk and replication slots]] - Agent-reviewed PG 12 answer covering full `pg_wal` filesystem PANIC behavior, replication-slot WAL retention, slot persistence, separate-WAL-disk corruption risk, and a production-safe slot-retention diagnostic query.
- [[v12/questions/wal-high-throughput-low-latency-disk-improvements|WAL directory on high throughput, low latency disk improvements (unverified)]] - Source-grounded analysis of how fast WAL storage improves transaction commit latency, checkpoint performance, background WAL writing, and WAL segment switches.



## Maintenance Tooling

- `scripts/recent_log` - recent wiki activity.
- `scripts/wiki_lint` - wiki health checks.
- `scripts/source_graph` - generate per-version Graphify source graphs under `.wiki-runtime/graph/postgres-NN/`; requires `--version NN` or explicit `--all`.
- `scripts/source_graph_query` - query version-pinned raw source and Graphify graphs; graph subcommands force graph generation when `graph.json` is absent.
- `scripts/source_graph_check` - validate Graphify graph manifests, pins, JSON parseability, wrong-version references, and optional query probes.
- `scripts/test_source_tools` - end-to-end synthetic fixture tests for raw graph-script queries and Graphify wrappers.
- `scripts/version_diff` - source path comparison across project-local PostgreSQL checkouts.
- `scripts/llama_server` - start, stop, status, and logs for the local llama.cpp OpenAI-compatible server.
- `scripts/hermes_sessions` - list and clear project-local Hermes session files and database rows.

## Maintenance Notes

- Update this page whenever a wiki page is created or substantially changed.
- Keep version-specific entries tagged with their PostgreSQL major version.
- Prefer links to version landing pages, such as `vNN/index`, once versions exist.
