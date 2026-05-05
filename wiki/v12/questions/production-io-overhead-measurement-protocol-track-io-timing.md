---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: claude-opus-4-7 2026-05-05T01:00:00Z
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

##### Analyzing `pg_test_timing` Output

`pg_test_timing` runs `INSTR_TIME_SET_CURRENT` in a tight loop for the requested duration (`-d`, default 3 s) and prints two artefacts ([[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c#test_timing|pg_test_timing.c#test_timing]]:110-168, [[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c#output|pg_test_timing.c#output]]:170-203):

1. **Per-loop time including overhead** (nanoseconds). Total elapsed wall-clock time divided by the number of loop iterations ([[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c#test_timing|pg_test_timing.c#test_timing]]:164-165). Each iteration makes **one** `INSTR_TIME_SET_CURRENT` call at [[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c#test_timing|pg_test_timing.c#test_timing]]:133 plus a few ns of arithmetic and a histogram increment ([[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c#test_timing|pg_test_timing.c#test_timing]]:127-158), so the per-loop number is essentially the per-call timer cost. Treat it as a tight upper bound on a single `INSTR_TIME_SET_CURRENT`.
2. **Histogram of timing durations**, bucketed by power-of-2 microseconds ([[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c|pg_test_timing.c]]:21,153). The `< us` column is the bucket upper bound — bucket `1` holds diffs of 0 µs (`< 1 us`), bucket `2` holds 1 µs, bucket `4` holds 2-3 µs, bucket `8` holds 4-7 µs, etc. Each sample is the µs gap between two consecutive timer reads. On a fast clocksource the loop body finishes well inside one µs tick so most diffs are 0 (the `1` bucket); on a slow clocksource the loop itself spans a µs tick, pushing samples into the `2` bucket and beyond.

Example output from the upstream documentation on a TSC-backed Intel i7-860 ([[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml|pgtesttiming.sgml]]:97-107):

```
Per loop time including overhead: 35.96 ns
Histogram of timing durations:
  < us   % of total      count
     1     96.40465   80435604
     2      3.59518    2999652
     4      0.00015        126
     8      0.00002         13
    16      0.00000          2
```

**Reading a healthy result**:
- Per-loop time well under 100 ns and >90 % of samples in the `< 1 us` bucket means a fast clocksource (TSC). `track_io_timing` overhead per buffer I/O is then dominated by the two `INSTR_TIME_SET_CURRENT` calls bracketing `smgrread` / `smgrwrite` — i.e. roughly `2 × per-loop-ns`, typically below 100 ns per buffer and swamped by even SSD-class disk latency.
- A near-empty long tail (negligible counts in `≥ 4 us` buckets) signals a stable clocksource with no scheduling jitter spikes during the run.

**Red flags that argue against enabling `track_io_timing` cluster-wide**:
- Per-loop time of several hundred ns or more, with the `2 us` bucket (or larger) dominating, indicates a slow clocksource — the upstream doc shows `acpi_pm` at 722.92 ns/loop with 72 % in the `2 us` bucket ([[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml|pgtesttiming.sgml]]:155-168). At ~2 × 723 ns ≈ 1.45 µs per buffer I/O, the timing overhead can materially inflate `blk_read_time` / `blk_write_time` whenever the underlying I/O is fast (the same doc notes this configuration would inflate `EXPLAIN ANALYZE` totals "significantly", [[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml|pgtesttiming.sgml]]:171-179).
- Non-trivial counts in the `≥ 8 us` buckets indicate scheduling preemption or virtualisation artefacts (common on noisy VMs); per-call overhead becomes high-variance, so the measured `blk_read_time` will be noisier than the mean alone suggests.
- The tool aborts with `Detected clock going backwards in time` if any consecutive pair of reads is non-monotonic ([[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c#test_timing|pg_test_timing.c#test_timing]]:137-143). A backwards-going clock invalidates `track_io_timing` deltas — fix the clocksource (typically by avoiding TSC across cores with skew, or pinning the VM to a stable hypervisor timer) before running this protocol.

**Estimating measurement-window overhead from the output**:

Each timed buffer I/O makes two `INSTR_TIME_SET_CURRENT` calls — one before `smgrread` / `smgrwrite` and one after ([[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common|bufmgr.c#ReadBuffer_common]]:894-905, [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#FlushBuffer|bufmgr.c#FlushBuffer]]:2752-2770). Using the per-loop time as an upper bound for one call:

```
total_overhead_ns ≈ 2 × per_loop_ns × (blks_read + blks_written)
```

Project the I/O block count from a recent `pg_stat_database` / `pg_stat_bgwriter` sample (or extrapolate from a pre-enable baseline). If the projected total overhead exceeds a few percent of the workload's CPU budget over the measurement window, prefer sampling (enable on a single session for representative queries) over cluster-wide enablement.

The upstream doc cross-checks the per-loop number against `EXPLAIN ANALYZE`: a 100k-row `SELECT COUNT(*)` ran in 9.8 ms versus 16.6 ms with `EXPLAIN ANALYZE`, giving 68 ns of timing overhead per row — about 2× the 35.96 ns per-loop number, which lines up with `EXPLAIN ANALYZE` issuing two `INSTR_TIME_SET_CURRENT` calls per row against pg_test_timing's one ([[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml|pgtesttiming.sgml]]:119-143). `track_io_timing` has the same two-call structure per buffer I/O ([[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common|bufmgr.c#ReadBuffer_common]]:894-905), so the `2 × per_loop_ns` factor in the formula above is empirically grounded.

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
- [[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c]] — standalone tool that measures per-call `INSTR_TIME_SET_CURRENT` overhead. Histogram array declared at line 21, increment at line 153.
- [[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c#test_timing]] — measurement loop, lines 110-168. Per-loop printf at lines 164-165; monotonicity check at lines 137-143.
- [[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c#output]] — histogram printer, lines 170-203. Bucket label is the upper bound (`1l << i`).
- [[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml]] — upstream `pg_test_timing` reference page. TSC sample output at lines 97-107; `acpi_pm` slow-clocksource sample at lines 155-168; `acpi_pm` `EXPLAIN ANALYZE` impact note at lines 171-179; TSC `EXPLAIN ANALYZE` cross-check at lines 119-143.

## Open Questions

- Optimal measurement window duration for different workload types?
- Impact of track_io_timing on WAL I/O timing?
- Correlation with OS-level I/O metrics for validation?
- Exact per-call overhead of `INSTR_TIME_SET_CURRENT` on bare metal vs. VM (depends on `clock_gettime` syscall cost; `pg_test_timing` measures this but no authoritative range is documented in source).