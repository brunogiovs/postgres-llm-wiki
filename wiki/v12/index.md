# PostgreSQL 12.2

## Source Pin

- Branch: `REL_12_STABLE`
- Commit: `45b88269a353ad93744772791feb6d01bc7e1e42`
- Status: `legacy`
- Source path: `raw/postgres-12/`
- Added: 2026-05-02

## Coverage

Questions: [[v12/questions/can-non-prepared-statements-use-generic-plans]], [[v12/questions/data-checksums-implementation]], [[v12/questions/genetic-query-optimizer]], [[v12/questions/key-metrics-usage-operational-status]], [[v12/questions/pg-test-timing-track-io-timing-overhead]], [[v12/questions/query-disk-io-with-warm-cache]], [[v12/questions/plan-cache-mode-production-impact]], [[v12/questions/detect-slow-random-io-disk-metrics]], [[v12/questions/track-io-timing-blk-write-time-dirty-victim-select]], [[v12/questions/dirty-victim-select-mitigation]], [[v12/questions/bgwriter-tuning-scenarios]], [[v12/questions/production-io-overhead-measurement-protocol-track-io-timing]], [[v12/questions/cte-join-inheritance-partitioned-table-300-partitions-settings-overhead]], [[v12/questions/partition-planner-settings]].

## Subsystems

No PostgreSQL 12-specific subsystem pages have been created yet.

## Files

No source file map pages have been created yet.

## Diagrams
- [[diagrams/source-code-tree-overview]] - Source code tree overview diagram.

## Questions

- [[v12/questions/can-non-prepared-statements-use-generic-plans]] - Do non-prepared SELECT statements use generic plans in PostgreSQL 12?

- [[v12/questions/data-checksums-implementation]] - PG 12 data checksums implementation, overhead, storage, and pg_checksums --enable operation.

- [[v12/questions/key-metrics-usage-operational-status]] - Key metrics for categorizing database usage and operational status in PostgreSQL 12.

- [[v12/questions/pg-test-timing-track-io-timing-overhead]] - What does pg_test_timing do, and what is the overhead of track_io_timing on modern hardware and virtual systems like AWS/Azure?

- [[v12/questions/query-disk-io-with-warm-cache]] - PG 12 pre-execution and execution disk I/O paths and how slow random I/O hurts even with warm shared buffers and OS page cache.

- [[v12/questions/plan-cache-mode-production-impact]] - Production impacts of plan_cache_mode modes, best per scenario, pros/cons, slow random I/O disk effects.

- [[v12/questions/detect-slow-random-io-disk-metrics]] - PG 12 detecting slow random disk I/O using database metrics (pg_stat_database blk_read_time, pg_stat_statements, IO waits).

- [[v12/questions/track-io-timing-blk-write-time-dirty-victim-select]] - Does `track_io_timing=on` `blk_write_time` capture synchronous dirty victim flush time during SELECT execution.

- [[v12/questions/dirty-victim-select-mitigation]] - How to mitigate "dirty victim" synchronous writes during SELECT queries in PostgreSQL 12?

- [[v12/questions/bgwriter-tuning-scenarios]] - Recommended bgwriter settings for various tuning scenarios in PostgreSQL 12.

- [[v12/questions/production-io-overhead-measurement-protocol-track-io-timing]] - Protocol to measure I/O overhead on production database using track_io_timing in PostgreSQL 12.

- [[v12/questions/cte-join-inheritance-partitioned-table-300-partitions-settings-overhead]] - Settings and configurations that help or add overhead to a SELECT query using CTE to join to an inheritance-partitioned table with 300 partitions in PostgreSQL 12.

- [[v12/questions/partition-planner-settings]] - PostgreSQL 12 query planner settings for partition tables, summarized by inheritance and declarative partitioning.


## Open Questions
