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

#### Subsystems

- [[v18/subsystems/parser]] - PG 18 raw SQL parser.
- [[v18/subsystems/analyzer]] - PG 18 parse analyzer.
- [[v18/subsystems/rewriter]] - PG 18 query rewriter.
- [[v18/subsystems/planner]] - PG 18 planner/optimizer entry map.
- [[v18/subsystems/executor]] - PG 18 executor entry map.

#### Questions

- [[v18/questions/query-plan-interpretation-inputs]] - PG 18 diagnostic packet for interpreting a query plan and production impact.
- [[v18/questions/prepared-statement-replanning]] - PG 18 prepared statement revalidation and replanning after DDL, added indexes, and statistics changes.
- [[v18/questions/btree-leaf-density-estimate]] - PG 18 catalog-only SQL that approximates `pgstatindex.avg_leaf_density` without scanning the index; handles partial indexes and surfaces deduplication.
- [[v18/questions/avg-leaf-density-vacuum-stat-table]] - PG 18 design for piggybacking `avg_leaf_density` onto every successful (auto)VACUUM of a btree index and persisting it through a new cumulative-statistics kind.
- [[v18/questions/plan-cache-mode-production-impact]] - PG 18 production analysis of `plan_cache_mode` modes (`auto`, `force_generic_plan`, `force_custom_plan`) with pros/cons and a per-scenario picker.
- [[v18/questions/insert-row-disk-writes]] - PG 18 disk writes during row insert txn (WAL sync at commit only, data async).
- [[v18/questions/query-disk-io-with-warm-cache]] - PG 18 pre-execution and execution disk I/O paths and how slow random I/O hurts even with warm shared buffers and OS page cache.

### PostgreSQL 12.2

- [[v12/index]] - Legacy version landing page. Source checkout pinned to `REL_12_STABLE` commit `45b88269a353ad93744772791feb6d01bc7e1e42`; project-context pack generated under `.wiki-runtime/context/postgres-12/`.

#### Questions

- [[v12/questions/can-non-prepared-statements-use-generic-plans]] - Do non-prepared SELECT statements use generic plans in PostgreSQL 12?

- [[v12/questions/data-checksums-implementation]] - PG 12 data checksums implementation, overhead, storage, and pg_checksums --enable operation.
- [[v12/questions/genetic-query-optimizer]] - How does the genetic query optimizer work in PostgreSQL 12, pros/cons, and detecting overhead.
- [[v12/questions/key-metrics-usage-operational-status]] - Key metrics for categorizing database usage and operational status in PostgreSQL 12.
- [[v12/questions/pg-test-timing-track-io-timing-overhead]] - What does pg_test_timing do, and what is the overhead of track_io_timing on modern hardware and virtual systems like AWS/Azure?
- [[v12/questions/plan-cache-mode-production-impact]] - PG 12 production analysis of `plan_cache_mode` modes (`auto`, `force_generic_plan`, `force_custom_plan`) with pros/cons and a per-scenario picker.
- [[v12/questions/track-io-timing-blk-write-time-dirty-victim-select]] - PG 12: Does `track_io_timing=on` `blk_write_time` capture synchronous dirty victim flush time during SELECT (yes).
- [[v12/questions/dirty-victim-select-mitigation]] - PG 12: How to mitigate "dirty victim" synchronous writes during SELECT queries.
- [[v12/questions/bgwriter-tuning-scenarios]] - Recommended bgwriter settings for various tuning scenarios in PostgreSQL 12.

- [[v12/questions/production-io-overhead-measurement-protocol-track-io-timing]] - Protocol to measure I/O overhead on production database using track_io_timing in PostgreSQL 12.

- [[v12/questions/cte-join-inheritance-partitioned-table-300-partitions-settings-overhead]] - Settings and configurations that help or add overhead to a SELECT query using CTE to join to an inheritance-partitioned table with 300 partitions in PostgreSQL 12.

- [[v12/questions/partition-planner-settings]] - PostgreSQL 12 query planner settings for partition tables, summarized by inheritance and declarative partitioning.

#### Diagrams
- [[v12/diagrams/source-code-tree-overview]] - PG 12 source code tree overview diagram.

## Maintenance Tooling

- `scripts/recent_log` - recent wiki activity.
- `scripts/wiki_lint` - wiki health checks.
- `scripts/source_lookup` - project-local PostgreSQL source lookup.
- `scripts/source_context` - regenerate per-version project-context packs under `.wiki-runtime/context/postgres-NN/`.
- `scripts/version_diff` - source path comparison across project-local PostgreSQL checkouts.
- `scripts/llama_server` - start, stop, status, and logs for the local llama.cpp OpenAI-compatible server.
- `scripts/hermes_sessions` - list and clear project-local Hermes session files and database rows.

## Maintenance Notes

- Update this page whenever a wiki page is created or substantially changed.
- Keep version-specific entries tagged with their PostgreSQL major version.
- Prefer links to version landing pages, such as `vNN/index`, once versions exist.
