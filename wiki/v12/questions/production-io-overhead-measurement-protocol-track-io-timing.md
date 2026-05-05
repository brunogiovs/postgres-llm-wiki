---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: claude-opus-4-7 2026-05-05T00:00:00Z
---

# Protocol to Measure I/O Overhead on Production Database Using track_io_timing in PostgreSQL 12

## Question

In PostgreSQL 12, propose a protocol to measure I/O overhead on a production database using `track_io_timing`.

## Short Answer

Enable `track_io_timing = on` temporarily during a representative workload window, collect I/O timing metrics from `pg_stat_statements` and `pg_stat_database`, then analyze per-operation I/O latency and total overhead. Disable after measurement to avoid production impact. Protocol includes baseline measurement, controlled enablement, data collection, and post-analysis cleanup.

## Detailed Answer

### Background: track_io_timing in PostgreSQL 12

`track_io_timing` (`boolean` GUC, default `off`, [[raw/postgres-12/src/backend/utils/misc/guc.c#track_io_timing|guc.c#track_io_timing]]:1402) enables wall-clock timing of buffer I/O operations via [[raw/postgres-12/src/backend/storage/smgr/smgr.c#smgrread|smgr.c#smgrread]]/[[raw/postgres-12/src/backend/storage/smgr/smgr.c#smgrwrite|smgr.c#smgrwrite]] in `FlushBuffer` and `ReadBuffer_common` ([[raw/postgres-12/src/backend/storage/buffer/bufmgr.c|bufmgr.c]]). When enabled:

- **Read timing**: [[raw/postgres-12/src/include/portability/instr_time.h#INSTR_TIME_SET_CURRENT|instr_time.h#INSTR_TIME_SET_CURRENT]] called before `smgrread`, compute `io_time` after, accumulate in [[raw/postgres-12/src/backend/executor/instrument.c#pgBufferUsage|instrument.c#pgBufferUsage]]`.blk_read_time` ([[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common|bufmgr.c#ReadBuffer_common]]:894-905).
- **Write timing**: Similar for `smgrwrite` in `FlushBuffer`, accumulate in `pgBufferUsage.blk_write_time` ([[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#FlushBuffer|bufmgr.c#FlushBuffer]]:2752-2770).
- **Overhead**: Two `INSTR_TIME_SET_CURRENT` calls per I/O operation; wall-clock cost depends on platform timer resolution — see `## Open Questions`.
- **Metrics exposure**: `pg_stat_statements` captures per-statement I/O time deltas ([[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pgss_store|pg_stat_statements.c#pgss_store]]:1291-1292); `pg_stat_database` aggregates system-wide ([[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_read_time|pgstatfuncs.c#pg_stat_get_db_blk_read_time]]).

### Measurement Protocol

#### Step 1: Pre-Measurement Assessment

- **Estimate baseline overhead**: Run [[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c|pg_test_timing.c]] on production hardware to measure per-call timing overhead before enabling cluster-wide.
- **Identify measurement window**: Choose low-traffic period (e.g., off-peak hours) for 1-4 hour measurement window.
- **Backup current settings**: Record current `pg_stat_statements` configuration and data retention settings.

#### Step 2: Enable I/O Timing

```sql
-- wiki: v12/questions/production-io-overhead-measurement-protocol-track-io-timing — enable I/O timing
-- Session-scoped timeouts protect this control plane statement.
-- Inline /* tag */ survives pg_stat_statements normalization; the -- header may be stripped.
SET /* wiki_enable_track_io_timing */ statement_timeout = '10s';
SET /* wiki_enable_track_io_timing */ lock_timeout = '2s';

ALTER SYSTEM /* wiki_enable_track_io_timing */ SET track_io_timing = on;
SELECT /* wiki_enable_track_io_timing_reload */ pg_reload_conf();

SHOW /* wiki_verify_track_io_timing */ track_io_timing;
```

**Safety notes**:
- `track_io_timing` is `PGC_SUSET` ([[raw/postgres-12/src/backend/utils/misc/guc.c#track_io_timing|guc.c#track_io_timing]]:1402). Per AGENTS.md's `context` mapping (`superuser` → session/transaction scope), a superuser `SET track_io_timing = on` takes effect immediately in the current session with no reload. `ALTER SYSTEM` writes the new default to `postgresql.auto.conf`; `pg_reload_conf()` (SIGHUP) is only needed to push that default into other live sessions. No restart is ever required.
- Overhead per I/O depends on platform timer cost — see `## Open Questions` and run `pg_test_timing` first.
- `SET` statements above are session-scoped; tune them for the workload (read-only diagnostic vs. control-plane DDL).

#### Step 3: Run Representative Workload

- Execute production-like queries during measurement window.
- Include mix of:
  - Read-heavy queries (SELECT with large scans).
  - Write-heavy operations (INSERT/UPDATE/DELETE).
  - Mixed OLTP/OLAP patterns.
- Monitor system load to ensure representative but not overloaded.

#### Step 4: Collect I/O Metrics

**Per-statement I/O timing**:

```sql
-- wiki: v12/questions/production-io-overhead-measurement-protocol-track-io-timing — top I/O-intensive statements
-- Session-scoped timeouts (read-only diagnostic against pg_stat_statements).
SET /* wiki_top_io_statements */ statement_timeout = '30s';
SET /* wiki_top_io_statements */ lock_timeout = '5s';

SELECT /* wiki_top_io_statements */ queryid, query, calls,
       blk_read_time, blk_write_time,
       total_time, mean_time,
       round(blk_read_time::numeric / nullif(calls, 0), 3) AS avg_read_ms_per_call,
       round(blk_write_time::numeric / nullif(calls, 0), 3) AS avg_write_ms_per_call,
       round((blk_read_time + blk_write_time)::numeric / nullif(total_time::numeric, 0) * 100, 2) AS io_percent_of_total
FROM pg_stat_statements
WHERE blk_read_time > 0 OR blk_write_time > 0
ORDER BY (blk_read_time + blk_write_time) DESC
LIMIT 20;
```

**Database-wide I/O summary**:

```sql
-- wiki: v12/questions/production-io-overhead-measurement-protocol-track-io-timing — database-wide I/O summary
-- Session-scoped timeouts (read-only diagnostic against pg_stat_database).
-- Note: pg_stat_database has no blks_written column; avg_read_ms_per_block uses blks_read (disk reads only).
-- For write block counts, join pg_stat_bgwriter (see [[raw/postgres-12/src/backend/catalog/system_views.sql|system_views.sql]]:935).
SET /* wiki_db_io_summary */ statement_timeout = '30s';
SET /* wiki_db_io_summary */ lock_timeout = '5s';

SELECT /* wiki_db_io_summary */ datname,
       blk_read_time, blk_write_time,
       blks_read, blks_hit,
       round(blk_read_time::numeric / nullif(blks_read, 0), 3) AS avg_read_ms_per_block
FROM pg_stat_database
WHERE datname NOT IN ('template0', 'template1')
ORDER BY (blk_read_time + blk_write_time) DESC;
```

**Real-time monitoring** (during measurement):

```sql
-- wiki: v12/questions/production-io-overhead-measurement-protocol-track-io-timing — real-time I/O timing sample (run in loop)
-- Session-scoped timeouts; keep statement_timeout tight so a stuck sample cannot wedge the polling loop.
SET /* wiki_io_realtime_sample */ statement_timeout = '5s';
SET /* wiki_io_realtime_sample */ lock_timeout = '2s';

SELECT /* wiki_io_realtime_sample */ now(),
       sum(blk_read_time) AS total_read_ms,
       sum(blk_write_time) AS total_write_ms,
       sum(calls) AS total_calls
FROM pg_stat_statements
WHERE blk_read_time > 0 OR blk_write_time > 0;
```

#### Step 5: Analyze Results

**Calculate I/O overhead metrics**:

- **Per-operation latency**: `avg_read_ms_per_block` / `avg_write_ms_per_block` from queries above.
- **I/O time as % of query time**: `io_percent_of_total` from statement analysis.
- **Cache efficiency**: `(blks_hit / (blks_read + blks_hit)) * 100` from `pg_stat_database`.
- **Dirty victim pressure**: High `blk_write_time` on SELECT statements indicates synchronous buffer flushing.

**Identify bottlenecks**:
- Queries with high `io_percent_of_total` (>50%) are I/O-bound.
- High `avg_read_ms_per_block` (>10ms) indicates slow random I/O.
- Compare `avg_read_ms_per_block` across databases/tables to identify hot spots.

**Quantify timing overhead**:
- Use `pg_test_timing` output to estimate per-call cost; multiply by `(blks_read + blks_written)` for total overhead.
- Compare query `total_time` with/without timing (approximate by running subset before/after).

#### Step 6: Cleanup and Disable

```sql
-- wiki: v12/questions/production-io-overhead-measurement-protocol-track-io-timing — disable I/O timing
-- Session-scoped timeouts protect this control plane statement.
SET /* wiki_disable_track_io_timing */ statement_timeout = '10s';
SET /* wiki_disable_track_io_timing */ lock_timeout = '2s';

ALTER SYSTEM /* wiki_disable_track_io_timing */ SET track_io_timing = off;
SELECT /* wiki_disable_track_io_timing_reload */ pg_reload_conf();
```

**Optional, destructive — only if you intentionally want to wipe stats**:

The two `_reset()` functions below clear cluster-wide counters that other operators, dashboards, and slow-query reports may be relying on. They are not part of routine cleanup; archive metrics first and confirm no consumer depends on the current counters before running.

```sql
-- wiki: v12/questions/production-io-overhead-measurement-protocol-track-io-timing — DESTRUCTIVE reset of pg_stat_statements counters
SET /* wiki_pgss_reset */ statement_timeout = '10s';
SET /* wiki_pgss_reset */ lock_timeout = '2s';
SELECT /* wiki_pgss_reset */ pg_stat_statements_reset();

-- wiki: v12/questions/production-io-overhead-measurement-protocol-track-io-timing — DESTRUCTIVE reset of all per-database stats
SET /* wiki_pg_stat_reset */ statement_timeout = '10s';
SET /* wiki_pg_stat_reset */ lock_timeout = '2s';
SELECT /* wiki_pg_stat_reset */ pg_stat_reset();
```

**Post-measurement analysis**:
- Archive collected metrics for trend analysis before any reset.
- Correlate with OS metrics (`iostat`, `iotop`) for validation.
- Use findings to optimize (e.g., increase `shared_buffers`, tune `bgwriter_*` settings).

### Safety Considerations

- **Production impact**: Enable only during controlled windows; overhead scales with I/O rate.
- **Monitoring**: Watch for increased CPU usage during measurement.
- **Data retention**: `pg_stat_statements` retains data until reset; plan for storage impact.
- **Alternatives**: For continuous monitoring, consider sampling (enable/disable periodically) rather than always-on.

### Example Output Analysis

```
queryid | query | calls | blk_read_time | blk_write_time | avg_read_ms_per_call | avg_write_ms_per_call | io_percent_of_total
--------+-------+-------+---------------+----------------+----------------------+----------------------+-------------------
 12345  | SELECT * FROM large_table | 100 | 5000 | 200 | 50.0 | 2.0 | 75.2
```

**Interpretation**: This SELECT spends 75% of execution time on I/O (50ms read + 2ms write per call), indicating I/O bottleneck.

## Cross-Links

- [[v12/questions/pg-test-timing-track-io-timing-overhead]] - track_io_timing overhead measurement.
- [[v12/questions/detect-slow-random-io-disk-metrics]] - I/O metrics and slow disk detection.
- [[v12/questions/track-io-timing-blk-write-time-dirty-victim-select]] - blk_write_time behavior.
- [[v12/index]]

## Source References

- [[raw/postgres-12/src/backend/utils/misc/guc.c#track_io_timing]] — GUC definition, `PGC_SUSET`, line 1402.
- [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common]] — read I/O timing block, lines 894-905.
- [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#FlushBuffer]] — write I/O timing block, lines 2752-2770.
- [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pgss_store]] — per-statement `blk_read_time`/`blk_write_time` accumulation, lines 1291-1292.
- [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_read_time]] — database-wide read I/O time exposure, lines 1568-1582.
- [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_write_time]] — database-wide write I/O time exposure, lines 1584-1598.
- [[raw/postgres-12/src/backend/catalog/system_views.sql]] — `pg_stat_database` view definition (lines 856-882) shows `blks_read`/`blks_hit` but no `blks_written` column; `pg_stat_bgwriter` view at line 935.
- [[raw/postgres-12/src/include/portability/instr_time.h#INSTR_TIME_SET_CURRENT]] — `INSTR_TIME_SET_CURRENT` macro, platform-specific definitions at lines 92 (`clock_gettime`), 156 (`gettimeofday`), 220 (`QueryPerformanceCounter`).
- [[raw/postgres-12/src/backend/storage/smgr/smgr.c#smgrread]] — storage manager read entry point, line 587.
- [[raw/postgres-12/src/backend/storage/smgr/smgr.c#smgrwrite]] — storage manager write entry point, line 609.
- [[raw/postgres-12/src/backend/executor/instrument.c#pgBufferUsage]] — global `BufferUsage` accumulator, line 20.
- [[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c]] — standalone tool that measures per-call `INSTR_TIME_SET_CURRENT` overhead.

## Open Questions

- Optimal measurement window duration for different workload types?
- Impact of track_io_timing on WAL I/O timing?
- Correlation with OS-level I/O metrics for validation?
- Exact per-call overhead of `INSTR_TIME_SET_CURRENT` on bare metal vs. VM (depends on `clock_gettime` syscall cost; `pg_test_timing` measures this but no authoritative range is documented in source).