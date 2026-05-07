# Wiki Index

This is the global catalog for the PostgreSQL engine wiki.

## Entry Points

- [[versions]] - PostgreSQL version index and source pin manifest.
- [[overview]] - Cross-version architecture overview.
- [[log]] - Chronological activity log.
- [[operations/agent]] - Project-local Hermes install and start/stop runbook for the wiki maintainer agent.

## Version-Specific Pages

### PostgreSQL 18

- [[v18/index]] - Primary version landing page. Source checkout pinned to `REL_18_STABLE` commit `6cb307251c5c6261286c1566496920976640108e`; project-context pack generated under `.wiki-runtime/context/postgres-18/`.



### PostgreSQL 12.2

- [[v12/index]] - Legacy version landing page. Source checkout pinned to `REL_12_STABLE` commit `45b88269a353ad93744772791feb6d01bc7e1e42`; project-context pack generated under `.wiki-runtime/context/postgres-12/` with an appended contrib compile capture.
- [[v12/questions/azure-disk-configuration-recommendations|Azure disk configuration recommendations (unverified)]] - Source-grounded PG 12 configuration recommendations for Ultra Disk, Premium SSD v2, Premium SSD, Standard SSD, and Standard HDD storage classes, covering planner storage costs, `effective_io_concurrency`, checkpoints/WAL, bgwriter/writeback, temp spill placement, durability settings, rollout scope, and production-safe inventory queries.
- [[v12/questions/bgwriter-tuning-recommendations|Bgwriter tuning recommendations (unverified)]] - Source-grounded direction-of-change matrix for the four PG 12 bgwriter GUCs (`bgwriter_delay`, `bgwriter_lru_maxpages`, `bgwriter_lru_multiplier`, `bgwriter_flush_after`) across the main tuning scenarios, with verified `pg_stat_bgwriter` counter wiring and practical backend-write-share threshold bands for iterative tuning.
- [[v12/questions/checkpoint-monitoring-optimization-scenarios|Checkpoint monitoring and optimization scenarios (unverified)]] - Source-grounded PG 12 checkpoint monitoring and tuning workflow using `pg_stat_bgwriter`, `log_checkpoints`, a `pg_settings` checkpoint-configuration inventory query, checkpoint/WAL GUC reload semantics, and deployment scenarios for fast local disks and cloud block storage.
- [[v12/questions/disk-io-before-after-query-plan-execution|Disk I/O before/after query planning and execution]] - Agent-reviewed PG 12 query-lifecycle I/O map covering catalog and relcache access, planner relation-size probes, shared-buffer hits versus storage reads, DML writes, hint bits, temp spills, WAL flushes, bgwriter/checkpointer writes, DDL/maintenance file operations, and the exact `track_io_timing` boundary around `smgrread` / `smgrwrite`.
- [[v12/questions/enable-io-timing-measurements-production|Enable I/O timing measurements on production]] - Production procedure for enabling PG 12 `track_io_timing`, including host timing preflight, reload/session semantics, tagged SQL sampling, `pg_stat_database`, optional `pg_stat_statements`, and `EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)` interpretation.
- [[v12/questions/inheritance-partition-no-pruning-overhead|Inheritance partition query overhead when no pruning is possible]] - Source-grounded overhead matrix for PG 12 traditional inheritance partitioning when no child tables can be pruned, covering `constraint_exclusion`, generic/custom plans, indexes/stats, planner cost knobs, parallel append, JIT, and instrumentation overhead.
- [[v12/questions/wal-separate-disk-full-replication-slots|WAL on a separate full disk and replication slots]] - Agent-reviewed PG 12 answer covering full `pg_wal` filesystem PANIC behavior, replication-slot WAL retention, slot persistence, separate-WAL-disk corruption risk, and a production-safe slot-retention diagnostic query.
- [[v12/questions/wal-high-throughput-low-latency-disk-improvements|WAL directory on high throughput, low latency disk improvements (unverified)]] - Source-grounded analysis of how fast WAL storage improves transaction commit latency, checkpoint performance, background WAL writing, and WAL segment switches.



## Maintenance Tooling

- `scripts/recent_log` - recent wiki activity.
- `scripts/wiki_lint` - wiki health checks.
- `scripts/source_lookup` - project-local PostgreSQL source lookup; requires `--version NN`.
- `scripts/source_deps` - context-pack include/dependency lookup for direct includes, reverse include users, transitive include edges, and compile-unit flags; requires `--version NN`.
- `scripts/source_context` - regenerate per-version project-context packs under `.wiki-runtime/context/postgres-NN/`; requires `--version NN` or explicit `--all`.
- `scripts/source_context_check` - raw-source-rooted sanity checker for context packs; walks raw C/header include dependencies, cross-checks the pack, and exercises source navigation commands.
- `scripts/test_source_tools` - end-to-end synthetic fixture tests for `scripts/source_lookup`, `scripts/source_deps`, `scripts/source_context`, and `scripts/source_context_check`.
- `scripts/version_diff` - source path comparison across project-local PostgreSQL checkouts.
- `scripts/llama_server` - start, stop, status, and logs for the local llama.cpp OpenAI-compatible server.
- `scripts/hermes_sessions` - list and clear project-local Hermes session files and database rows.

## Maintenance Notes

- Update this page whenever a wiki page is created or substantially changed.
- Keep version-specific entries tagged with their PostgreSQL major version.
- Prefer links to version landing pages, such as `vNN/index`, once versions exist.
