# PostgreSQL 12.2

## Source Pin

- Branch: `REL_12_STABLE`
- Commit: `45b88269a353ad93744772791feb6d01bc7e1e42`
- Status: `legacy`
- Source path: `raw/postgres-12/`
- Added: 2026-05-02

## Coverage

Questions filed:

- [[v12/questions/azure-disk-configuration-recommendations|Azure disk configuration recommendations (unverified)]] (PG 12 storage-class tuning guidance for prompt-provided Azure Ultra Disk, Premium SSD v2, Premium SSD, Standard SSD, and Standard HDD options, with planner cost, `effective_io_concurrency`, checkpoint/WAL, bgwriter/writeback, temp spill, durability, rollout-scope, and inventory-query coverage)
- [[v12/questions/bgwriter-tuning-recommendations|Bgwriter tuning recommendations]] (agent-reviewed: four bgwriter GUCs with defaults/ranges/reload semantics, source-grounded direction-of-change matrix per scenario, verified `pg_stat_bgwriter` counter wiring, and practical backend-write-share threshold bands for iterative tuning)
- [[v12/questions/checkpoint-monitoring-optimization-scenarios|Checkpoint monitoring and optimization scenarios]] (agent-reviewed: PG 12 checkpoint monitoring and tuning workflow using `pg_stat_bgwriter`, `log_checkpoints`, a `pg_settings` checkpoint-configuration inventory query, checkpoint/WAL GUC reload semantics, and deployment scenarios for fast local disks and cloud block storage)
- [[v12/questions/disk-io-before-after-query-plan-execution|Disk I/O before/after query planning and execution]] (agent-reviewed query-lifecycle I/O map covering catalog and relcache access, planner relation-size probes, shared-buffer hits versus storage reads, DML writes, hint bits, temp spills, WAL flushes, bgwriter/checkpointer writes, DDL/maintenance file operations, and the exact `track_io_timing` boundary around `smgrread` / `smgrwrite`)
- [[v12/questions/enable-io-timing-measurements-production|Enable I/O timing measurements on production]] (agent-reviewed procedure for enabling `track_io_timing` on production, with host timing preflight, reload/session semantics, tagged SQL sampling, `pg_stat_database`, optional `pg_stat_statements`, and plan-level drill-down)
- [[v12/questions/inheritance-partition-no-pruning-overhead|Inheritance partition query overhead when no pruning is possible]] (agent-reviewed matrix of PG 12 tunables that reduce or add overhead when a traditional-inheritance query must visit roughly 300 child tables because constraint exclusion cannot prune them, including when `force_generic_plan` can reduce planning overhead and why it cannot reduce executor child visits)
- [[v12/questions/planning-metrics-generic-custom-replans|Planning metrics and generic/custom replanning visibility (unverified)]] (PG 12 planning-metric inventory and practical visibility guide for generic versus custom prepared-plan choice, covering `EXPLAIN EXECUTE`, `pg_prepared_statements`, `pg_stat_statements`, `log_planner_stats`, `auto_explain`, plan-cache invalidation, and why exact generic/custom transition counts are not exposed by built-in SQL views)
- [[v12/questions/plan-cache-mode-production-impact|Plan cache mode production impact (unverified)]] (source-grounded analysis of `plan_cache_mode` in PG 12 production use, covering `auto`, `force_custom_plan`, `force_generic_plan`, `CheckCachedPlan()` generic-plan validation, prepared-statement and PL/pgSQL/SPI boundaries, pros/cons by scenario, and slow random I/O storage)
- [[v12/questions/wal-separate-disk-full-replication-slots|WAL on a separate full disk and replication slots]] (agent-reviewed analysis of full `pg_wal` filesystem PANIC behavior, replication-slot WAL retention and persistence, separate-WAL-disk corruption risk, and a production-safe retained-WAL diagnostic query)
- [[v12/questions/wal-high-throughput-low-latency-disk-improvements|WAL directory on high throughput, low latency disk improvements (unverified)]] (source-grounded analysis of how fast WAL storage improves transaction commit latency, checkpoint performance, background WAL writing, and WAL segment switches)

Source navigation is graph-first. Raw source queries should use `scripts/source_graph_query --version 12 ...`.

## Graphify Source Graph

- Graph path: `.wiki-runtime/graph/postgres-12/`
- Status: AST-only graph generated with `scripts/source_graph --version 12 --refresh`; generated on demand by graph query commands when `graph.json` is absent.
- Use graph output only as navigation context; behavioral claims still need citations under `raw/postgres-12/`.
