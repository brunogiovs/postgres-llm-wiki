# PostgreSQL 12.2

## Source Pin

- Branch: `REL_12_STABLE`
- Commit: `45b88269a353ad93744772791feb6d01bc7e1e42`
- Status: `legacy`
- Source path: `raw/postgres-12/`
- Added: 2026-05-02

## Coverage

Questions: [[v12/questions/can-non-prepared-statements-use-generic-plans]], [[v12/questions/query-disk-io-with-warm-cache]], [[v12/questions/plan-cache-mode-production-impact]], [[v12/questions/detect-slow-random-io-disk-metrics]], [[v12/questions/track-io-timing-blk-write-time-dirty-victim-select]], [[v12/questions/dirty-victim-select-mitigation]].

## Subsystems

No PostgreSQL 12-specific subsystem pages have been created yet.

## Code Paths

No PostgreSQL 12-specific code path pages have been created yet.

## Concepts

No PostgreSQL 12-specific concept pages have been created yet.

### Shared Concepts Verified Against PG12

No shared concept pages verified against PG12 yet.

## Files

No source file map pages have been created yet.

## Diagrams
- [[diagrams/source-code-tree-overview]] - Source code tree overview diagram.

## Questions

- [[v12/questions/can-non-prepared-statements-use-generic-plans]] - Do non-prepared SELECT statements use generic plans in PostgreSQL 12?

- [[v12/questions/query-disk-io-with-warm-cache]] - PG 12 pre-execution and execution disk I/O paths and how slow random I/O hurts even with warm shared buffers and OS page cache.

- [[v12/questions/plan-cache-mode-production-impact]] - Production impacts of plan_cache_mode modes, best per scenario, pros/cons, slow random I/O disk effects.

- [[v12/questions/detect-slow-random-io-disk-metrics]] - PG 12 detecting slow random disk I/O using database metrics (pg_stat_database blk_read_time, pg_stat_statements, IO waits).

- [[v12/questions/track-io-timing-blk-write-time-dirty-victim-select]] - Does `track_io_timing=on` `blk_write_time` capture synchronous dirty victim flush time during SELECT execution.

- [[v12/questions/dirty-victim-select-mitigation]] - How to mitigate "dirty victim" synchronous writes during SELECT queries in PostgreSQL 12?


## Open Questions
