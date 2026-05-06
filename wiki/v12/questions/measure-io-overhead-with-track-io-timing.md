---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: Cline 2026-05-05T22:10:00Z
---

# Question

Propose a procedure to measure I/O overhead on a production PostgreSQL 12 database using `track_io_timing`.

The procedure should cover both interpretations of "I/O overhead":

1. The runtime overhead of enabling `track_io_timing` itself (the per-buffer clock-reading cost), so it can be turned on safely in production.
2. The time the workload actually spends in physical block I/O once the GUC is on, sampled cluster-wide and per-statement without disturbing the live system.

## Short Answer

1. Qualify the host first with `pg_test_timing`. `track_io_timing` brackets every shared-buffer read and every shared-buffer flush with two `INSTR_TIME_SET_CURRENT` calls in [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common|bufmgr.c lines 891-905]] and [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#FlushBuffer|bufmgr.c lines 2752-2770]], so the production cost of enabling it is set by the host clock source. If `pg_test_timing` reports nanosecond-class median ticks (TSC-backed `clock_gettime`), the overhead is acceptable; if it reports microsecond-class ticks, do not enable cluster-wide.
2. Enable cluster-wide via `ALTER SYSTEM SET track_io_timing = on` plus `SELECT pg_reload_conf()` — `track_io_timing` is `PGC_SUSET` ([[raw/postgres-12/src/backend/utils/misc/guc.c#L1402|guc.c#L1402]]), which per [[raw/postgres-12/src/include/utils/guc.h#L63|guc.h#L63]] takes effect on SIGHUP reload and does not require a restart.
3. Sample deltas of `blk_read_time` / `blk_write_time` from [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_database|pg_stat_database]] for cluster-wide totals, and from `pg_stat_statements` ([[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#L1652|pg_stat_statements.c#L1652]]) for per-statement attribution. Use `EXPLAIN (ANALYZE, BUFFERS)` for per-plan attribution gated by [[raw/postgres-12/src/backend/commands/explain.c#L2975|explain.c#L2975]].
4. Disable cluster-wide with `ALTER SYSTEM RESET track_io_timing` plus `SELECT pg_reload_conf()` once you have your sample window.

## Detailed Answer

### What `track_io_timing` actually measures in v12

`track_io_timing` is a single boolean GUC declared at [[raw/postgres-12/src/backend/utils/misc/guc.c#L1402|guc.c#L1402]] with backing variable `track_io_timing` defined at [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#L112|bufmgr.c#L112]]. When on, it adds two `INSTR_TIME_SET_CURRENT` calls around two specific operations:

- Shared-buffer reads in `ReadBuffer_common`, around the `smgrread` of a missing block. The delta is fed into `pgstat_count_buffer_read_time` and accumulated into `pgBufferUsage.blk_read_time`. See [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#L891-L905|bufmgr.c lines 891-905]].
- Shared-buffer writes in `FlushBuffer`, around the `smgrwrite` of a dirty buffer. The delta is fed into `pgstat_count_buffer_write_time` and accumulated into `pgBufferUsage.blk_write_time`. See [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#L2752-L2770|bufmgr.c lines 2752-2770]].

What `track_io_timing` does **not** cover in v12:

- Local-buffer (temporary-table) I/O. [[raw/postgres-12/src/backend/storage/buffer/localbuf.c#L217|localbuf.c#L217]] calls `smgrwrite` directly with no `track_io_timing` gate, and the file has no other references to it.
- Temp-file I/O for sort/hash spills, WAL writes/fsyncs, archiver/walsender I/O, and similar non-buffer-manager paths.

So "I/O overhead" measured here is specifically **shared-buffer-manager block read time and dirty-buffer flush time**, in microseconds per call, accumulated and reported as milliseconds.

### Where the timings are exposed

- Per database, cluster-wide totals: `pg_stat_database.blk_read_time` and `pg_stat_database.blk_write_time` (milliseconds), defined in [[raw/postgres-12/src/backend/catalog/system_views.sql#L880-L881|system_views.sql lines 880-881]] and computed from `n_block_read_time` / `n_block_write_time` (microseconds) in [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_read_time|pgstatfuncs.c#L1568]] and [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_write_time|pgstatfuncs.c#L1584]].
- Per normalized statement, when `pg_stat_statements` is loaded: `blk_read_time` / `blk_write_time` columns, populated at [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#L1291-L1292|pg_stat_statements.c lines 1291-1292]] from the per-statement `BufferUsage` delta and exported at [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#L1652-L1653|lines 1652-1653]].
- Per query plan, when `EXPLAIN (ANALYZE, BUFFERS)` is used: `I/O Read Time` and `I/O Write Time`, gated on `track_io_timing` at [[raw/postgres-12/src/backend/commands/explain.c#L2975|explain.c#L2975]].

### GUC change semantics

`track_io_timing` is `PGC_SUSET` ([[raw/postgres-12/src/backend/utils/misc/guc.c#L1402|guc.c#L1402]]). The semantics of `PGC_SUSET` from [[raw/postgres-12/src/include/utils/guc.h#L63|guc.h#L63]]: "SUSET options can be set at postmaster startup, with the SIGHUP mechanism, or from the startup packet or SQL if you're a superuser."

Concretely, in PostgreSQL 12:

- A superuser session can `SET track_io_timing = on;` for itself only (no restart, no reload).
- `ALTER SYSTEM SET track_io_timing = on;` followed by `SELECT pg_reload_conf();` enables it cluster-wide for new and existing backends after they reread the file. **No restart required.**
- A change in `postgresql.conf` plus `pg_reload_conf()` has the same effect.

For production-wide measurement, use `ALTER SYSTEM` + `pg_reload_conf()`, because per-session `SET` does not affect other backends and therefore does not populate `pg_stat_database`-wide totals from the rest of the workload.

### Procedure

#### Step 0 — Decide whether enabling is safe (clock-source qualification)

Run `pg_test_timing` on the production host (or an identically-provisioned host) for at least the duration of the longest expected sample window. The tool source is at [[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c]] and the manual entry is at [[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml]]. Per [[raw/postgres-12/doc/src/sgml/config.sgml#L6862-L6866|config.sgml lines 6862-6866]], the GUC defaults to off because every shared-buffer read and every dirty-buffer flush adds two clock reads.

Decision rule:

- Median tick ≤ ~100 ns and ≥99% of ticks in that bucket → safe to enable cluster-wide on a busy OLTP workload.
- Median tick in microseconds, or a long tail of slow ticks → do **not** enable cluster-wide; restrict to a per-session `SET` on a representative sampling backend, or to `EXPLAIN (ANALYZE, BUFFERS)` on the suspect query.

`pg_test_timing` does not require the database to be running; it can be run against the same kernel/CPU/clocksource as production without touching the cluster.

#### Step 1 — Pre-conditions

- Confirm `pg_stat_statements` is in `shared_preload_libraries` (this requires a restart to add, so do not add it for this procedure unless it is already there).
- Confirm the role you will use is a superuser (required by `PGC_SUSET`).
- Pick a sample window long enough to cover at least one full workload cycle (typically 5-30 minutes for OLTP).

#### Step 2 — Snapshot the "before" baseline

Run as a superuser, before enabling the GUC. Record into a side schema so the snapshot survives the session.

```sql
SET statement_timeout = '30s';
SET lock_timeout      = '5s';

CREATE SCHEMA IF NOT EXISTS /* wiki_io_overhead_schema */ wiki_io_overhead;

CREATE TABLE IF NOT EXISTS /* wiki_io_overhead_snapshot_table */
  wiki_io_overhead.db_snapshot (
    label        text        NOT NULL,
    captured_at  timestamptz NOT NULL DEFAULT clock_timestamp(),
    datname      name        NOT NULL,
    blks_read    bigint      NOT NULL,
    blks_hit     bigint      NOT NULL,
    blk_read_time double precision NOT NULL,
    blk_write_time double precision NOT NULL,
    PRIMARY KEY (label, datname)
  );

INSERT INTO /* wiki_io_overhead_snapshot_before */
  wiki_io_overhead.db_snapshot
    (label, datname, blks_read, blks_hit, blk_read_time, blk_write_time)
SELECT 'before', datname, blks_read, blks_hit, blk_read_time, blk_write_time
FROM   pg_stat_database
WHERE  datname IS NOT NULL;
```

Note: `blk_read_time` / `blk_write_time` are cumulative since the last `pg_stat_reset()` for the database. The procedure samples deltas, so do not call `pg_stat_reset()` — that would discard counters other tools rely on.

#### Step 3 — Enable `track_io_timing` cluster-wide

```sql
SET statement_timeout = '30s';
SET lock_timeout      = '5s';

ALTER /* wiki_io_overhead_enable */ SYSTEM SET track_io_timing = on;
SELECT /* wiki_io_overhead_reload_on */ pg_reload_conf();

-- Confirm it landed.
SELECT /* wiki_io_overhead_verify_on */ name, setting, context, source
FROM   pg_settings
WHERE  name = 'track_io_timing';
```

`context` should report `superuser` (the user-facing label for `PGC_SUSET`) and `setting` should be `on`. Existing backends pick up the new value at the next SIGHUP reread, which is essentially immediate.

#### Step 4 — Let the workload run for the chosen window

Do nothing for the agreed sample duration. Optionally, capture per-query attribution from `pg_stat_statements`:

```sql
SET statement_timeout = '30s';

CREATE TABLE IF NOT EXISTS /* wiki_io_overhead_pgss_table */
  wiki_io_overhead.pgss_snapshot (
    label        text        NOT NULL,
    captured_at  timestamptz NOT NULL DEFAULT clock_timestamp(),
    queryid      bigint      NOT NULL,
    dbid         oid         NOT NULL,
    userid       oid         NOT NULL,
    calls        bigint      NOT NULL,
    total_time   double precision NOT NULL,
    blk_read_time  double precision NOT NULL,
    blk_write_time double precision NOT NULL,
    PRIMARY KEY (label, queryid, dbid, userid)
  );

INSERT INTO /* wiki_io_overhead_pgss_before */
  wiki_io_overhead.pgss_snapshot
    (label, queryid, dbid, userid, calls, total_time, blk_read_time, blk_write_time)
SELECT 'before', queryid, dbid, userid, calls, total_time, blk_read_time, blk_write_time
FROM   pg_stat_statements;
```

Run the same `INSERT` again with `'after'` at the end of the window.

#### Step 5 — Snapshot the "after" baseline and compute deltas

```sql
SET statement_timeout = '30s';
SET lock_timeout      = '5s';

INSERT INTO /* wiki_io_overhead_snapshot_after */
  wiki_io_overhead.db_snapshot
    (label, datname, blks_read, blks_hit, blk_read_time, blk_write_time)
SELECT 'after', datname, blks_read, blks_hit, blk_read_time, blk_write_time
FROM   pg_stat_database
WHERE  datname IS NOT NULL;

SELECT /* wiki_io_overhead_compute_delta */
       a.datname,
       (a.blks_read    - b.blks_read)      AS d_blks_read,
       (a.blks_hit     - b.blks_hit)       AS d_blks_hit,
       round((a.blk_read_time  - b.blk_read_time)::numeric,  3) AS d_blk_read_time_ms,
       round((a.blk_write_time - b.blk_write_time)::numeric, 3) AS d_blk_write_time_ms,
       round(EXTRACT(EPOCH FROM (a.captured_at - b.captured_at))::numeric, 3) AS window_seconds
FROM   wiki_io_overhead.db_snapshot a
JOIN   wiki_io_overhead.db_snapshot b
       ON a.datname = b.datname AND a.label = 'after' AND b.label = 'before'
ORDER  BY d_blk_read_time_ms DESC;
```

Interpretation:

- `d_blk_read_time_ms` / `window_seconds * 1000` = average parallel backends busy doing shared-buffer reads. If this is comparable to the number of active backends, I/O is the dominant cost.
- `d_blk_read_time_ms / NULLIF(d_blks_read, 0)` = average per-block read time in ms. Compare to the host's expected storage latency.
- `d_blk_write_time_ms` reflects time spent in `FlushBuffer`, which is usually dominated by checkpointer and bgwriter activity unless backends are forced to evict dirty pages themselves.

For per-statement attribution, join the two `pg_stat_statements` snapshots in the same shape.

#### Step 6 — Disable `track_io_timing`

```sql
SET statement_timeout = '30s';
SET lock_timeout      = '5s';

ALTER /* wiki_io_overhead_disable */ SYSTEM RESET track_io_timing;
SELECT /* wiki_io_overhead_reload_off */ pg_reload_conf();

SELECT /* wiki_io_overhead_verify_off */ name, setting
FROM   pg_settings
WHERE  name = 'track_io_timing';
```

`ALTER SYSTEM RESET` removes the override in `postgresql.auto.conf` so the default (`off` per [[raw/postgres-12/src/backend/utils/misc/guc.c#L1407|guc.c#L1407]]) takes effect on reload. If `track_io_timing` was previously set in `postgresql.conf`, this step will not turn it off — adjust the file accordingly instead.

#### Step 7 — Optional per-plan drill-down

If a particular query is suspected, a superuser can keep `track_io_timing` off cluster-wide and enable it for one session:

```sql
SET /* wiki_io_overhead_session_only */ track_io_timing = on;
SET statement_timeout = '60s';

EXPLAIN /* wiki_io_overhead_explain */ (ANALYZE, BUFFERS, VERBOSE)
SELECT ...; -- the suspect query

RESET track_io_timing;
```

`I/O Read Time` and `I/O Write Time` lines appear per node, gated on the GUC at [[raw/postgres-12/src/backend/commands/explain.c#L2975|explain.c#L2975]]. This bypasses the cluster-wide cost entirely and is the right tool when `pg_test_timing` reported a slow clock source.

### Caveats

- Counters in `pg_stat_database` are cumulative and only updated by the stats collector; deltas are reliable, absolute "since boot" comparisons are not.
- A standby has its own counters; run the procedure on each node you care about.
- `track_io_timing` does not capture WAL fsync, temp-file I/O, or local-buffer I/O in v12, so it is not a full picture of disk overhead — only the shared-buffer-manager component.
- Enabling cluster-wide on a host with a microsecond-class clock source can itself become the dominant cost. Step 0 is not optional.

## Evidence

- GUC declaration and `PGC_SUSET` context: [[raw/postgres-12/src/backend/utils/misc/guc.c#L1401-L1409|guc.c lines 1401-1409]]
- `PGC_SUSET` semantics: [[raw/postgres-12/src/include/utils/guc.h#L63-L66|guc.h lines 63-66]]
- Backing variable and default: [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#L112|bufmgr.c#L112]]
- Read-side instrumentation: [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#L891-L905|bufmgr.c lines 891-905]]
- Write-side instrumentation: [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#L2752-L2770|bufmgr.c lines 2752-2770]]
- Local-buffer writes are NOT instrumented: [[raw/postgres-12/src/backend/storage/buffer/localbuf.c#L217|localbuf.c#L217]]
- DB-level accumulator functions: [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_read_time|pgstatfuncs.c#L1568-L1582]], [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_write_time|pgstatfuncs.c#L1584-L1598]]
- `pg_stat_database` view definition: [[raw/postgres-12/src/backend/catalog/system_views.sql#L880-L881|system_views.sql lines 880-881]]
- Per-statement timing in `pg_stat_statements`: [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#L1049-L1052|pg_stat_statements.c lines 1049-1052]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#L1291-L1292|lines 1291-1292]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#L1652-L1653|lines 1652-1653]]
- `EXPLAIN (BUFFERS)` gating on `track_io_timing`: [[raw/postgres-12/src/backend/commands/explain.c#L2975-L2983|explain.c lines 2975-2983]]
- Documented purpose and overhead warning: [[raw/postgres-12/doc/src/sgml/config.sgml#L6854-L6873|config.sgml lines 6854-6873]]
- `pg_test_timing` tool: [[raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c]], [[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml]]

## Related Pages

- [[v12/index]]
- [[versions]]

## Follow-Up Questions

- How does `track_io_timing` interact with PostgreSQL 12's stats collector latency? Counters are accumulated per backend and forwarded to the stats collector; the lag between a buffer read and its appearance in `pg_stat_database` is bounded by `PGSTAT_STAT_INTERVAL` and worth tracing.
- What is the actual per-call overhead of `INSTR_TIME_SET_CURRENT` on common Linux kernels with the TSC clocksource versus the HPET fallback, in numbers, on the workloads we care about?
- Is there a way to attribute `blk_write_time` between backend evictions, the bgwriter, and the checkpointer in v12 without code patches? `pg_stat_bgwriter` does not expose write-time directly in this version.
