---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: claude-opus-4-7 2026-05-08T16:52:54Z
---

# Enable I/O timing measurements on production

## Question

In PostgreSQL 12, recommend a production procedure to enable I/O timing measurements, and explain in depth what is measured, how to collect the data, how to interpret it, and what restart/reload/session semantics apply.

## Answer

Assumption: "PostgreSQL 12" means the local source checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`.

The short recommendation is: enable `track_io_timing` for a bounded production observation window, do it with `ALTER SYSTEM` plus a configuration reload when you need cluster-wide measurements, sample deltas from `pg_stat_database`, use `pg_stat_statements` only if it is already loaded, and use `EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)` only for vetted statements. `track_io_timing` is off by default and is a `PGC_SUSET` boolean, so it does not require a restart; a reload is required only when applying a configuration-file or `ALTER SYSTEM` default, while a superuser can enable it in one session with `SET` [[raw/postgres-12/src/backend/utils/misc/guc.c#track_io_timing|guc.c#track_io_timing]], [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#view-pg-settings]].

PostgreSQL 12 documents the reason for caution: enabling `track_io_timing` repeatedly asks the operating system for the current time, and that can be expensive on some platforms. The same documentation points at `pg_test_timing` for host qualification and states that I/O timing is displayed in `pg_stat_database`, `EXPLAIN` with `BUFFERS`, and `pg_stat_statements` [[raw/postgres-12/doc/src/sgml/config.sgml#guc-track-io-timing|config.sgml#guc-track-io-timing]], [[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml#pgtesttiming|pgtesttiming.sgml#pgtesttiming]].

## Procedure

### 1. Choose the observation window

Use a representative but bounded window, usually long enough to smooth stats-collector delay and short enough to roll back quickly if overhead is visible. PostgreSQL 12 rate-limits normal stats reports with `PGSTAT_STAT_INTERVAL = 500` ms, and `pgstat_report_stat()` skips non-forced sends until that interval has elapsed, so sub-second sampling is the wrong shape for this data [[raw/postgres-12/src/backend/postmaster/pgstat.c#PGSTAT_STAT_INTERVAL|pgstat.c#PGSTAT_STAT_INTERVAL]], [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_report_stat|pgstat.c#pgstat_report_stat]].

Do not reset production statistics just to create a baseline. `pg_stat_reset()` zeros all counters for the current database, and that disrupts other monitoring; record start and end samples and compute deltas instead [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg_stat_reset|monitoring.sgml#pg_stat_reset]].

### 2. Preflight host timing overhead

Run `pg_test_timing` from the same PostgreSQL 12 binary package on the same host class before enabling cluster-wide timing:

```sh
pg_test_timing -d 10
```

`pg_test_timing` measures timing-call overhead and checks for backward clock movement; the PG12 docs say longer durations improve accuracy and are more likely to detect clock problems [[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml#pgtesttiming|pgtesttiming.sgml#pgtesttiming]].

### 3. Precheck configuration and take a baseline

Run the precheck as a superuser or an operations role with the needed catalog visibility. The timeouts below are session-scoped `SET` changes; both `statement_timeout` and `lock_timeout` are `PGC_USERSET`, so they do not require reload or restart. Adjust the values for the workload and tooling path [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout|guc.c#statement_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout|guc.c#lock_timeout]], [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]].

```sql
SET /* wiki_io_timing_statement_timeout */ statement_timeout = '30s';
SET /* wiki_io_timing_lock_timeout */ lock_timeout = '5s';

SELECT /* wiki_io_timing_guc_precheck */
       name,
       setting,
       context,
       source,
       pending_restart
FROM pg_settings
WHERE name IN ('track_io_timing', 'track_counts', 'shared_preload_libraries')
ORDER BY name;

SELECT /* wiki_io_timing_file_precheck */
       sourcefile,
       sourceline,
       name,
       setting,
       applied,
       error
FROM pg_file_settings
WHERE name IN ('track_io_timing', 'track_counts')
   OR error IS NOT NULL
ORDER BY sourcefile, sourceline;

SELECT /* wiki_io_timing_database_baseline */
       CURRENT_TIMESTAMP AS sample_ts,
       datid,
       datname,
       blks_read,
       blks_hit,
       blk_read_time,
       blk_write_time,
       temp_files,
       temp_bytes,
       stats_reset
FROM pg_stat_database
ORDER BY datid;
```

`pg_settings` exposes each parameter's current value, context, source, and `pending_restart`; `pg_file_settings` shows configuration-file entries and whether they can be applied, but it reports current file contents rather than the last applied runtime value [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_settings|system_views.sql#pg_settings]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#view-pg-settings]], [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_file_settings|system_views.sql#pg_file_settings]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-file-settings|catalogs.sgml#view-pg-file-settings]].

Keep `track_counts` on. PG12 defines `track_counts` as the switch that collects database activity statistics and defaults it to on because autovacuum needs the collected information [[raw/postgres-12/src/backend/utils/misc/guc.c#track_counts|guc.c#track_counts]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-track-counts|config.sgml#guc-track-counts]].

### 4. Enable cluster-wide timing

For a production-wide observation window, use `ALTER SYSTEM` and reload:

```sql
ALTER /* wiki_io_timing_enable */ SYSTEM SET track_io_timing = on;
SELECT /* wiki_io_timing_reload */ pg_reload_conf();
SHOW /* wiki_io_timing_show */ track_io_timing;

SELECT /* wiki_io_timing_verify */
       name,
       setting,
       context,
       source,
       pending_restart
FROM pg_settings
WHERE name = 'track_io_timing';
```

`ALTER SYSTEM` writes to `postgresql.auto.conf`; its changes take effect after configuration reload unless the target parameter is postmaster-only. It requires superuser privileges and is not allowed inside a transaction block [[raw/postgres-12/doc/src/sgml/ref/alter_system.sgml#ALTER-SYSTEM|alter_system.sgml#ALTER-SYSTEM]], [[raw/postgres-12/src/backend/utils/misc/guc.c#AlterSystemSetConfigFile|guc.c#AlterSystemSetConfigFile]]. `pg_reload_conf()` sends `SIGHUP` to the postmaster [[raw/postgres-12/src/backend/storage/ipc/signalfuncs.c#pg_reload_conf|signalfuncs.c#pg_reload_conf]].

For a single controlled backend, such as a superuser session running a targeted plan probe, use session scope instead:

```sql
SET /* wiki_io_timing_session_enable */ track_io_timing = on;
SHOW /* wiki_io_timing_session_show */ track_io_timing;
RESET /* wiki_io_timing_session_reset */ track_io_timing;
```

That session-level path does not reload the server. Because `track_io_timing` has `PGC_SUSET` context, only superusers can change it with `SET`; configuration-file changes affect existing sessions only when those sessions have not established a session-local value [[raw/postgres-12/src/backend/utils/misc/guc.c#track_io_timing|guc.c#track_io_timing]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#view-pg-settings]].

### 5. Collect database-level deltas

At the end of the window, run the `wiki_io_timing_database_baseline` query again and subtract the start sample from the end sample for each `datid`. `pg_stat_database.blk_read_time` and `blk_write_time` are exposed in milliseconds; the SQL functions divide the stats collector's microsecond counters by `1000.0` before returning `float8` [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_read_time|pgstatfuncs.c#pg_stat_get_db_blk_read_time]], [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_write_time|pgstatfuncs.c#pg_stat_get_db_blk_write_time]]. The `pg_stat_database` view wires those functions into the `blk_read_time` and `blk_write_time` columns [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_database|system_views.sql#pg_stat_database]].

Interpret deltas together:

- `delta_blk_read_time / delta_blks_read` is the observed milliseconds per database block read call that reached PostgreSQL's measured buffer read path. A high value means time was spent waiting inside measured read calls; it is not proof by itself that the physical device, rather than OS cache or filesystem behavior, was the only cause, because PG12 measures elapsed time around PostgreSQL storage-manager read calls [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common|bufmgr.c#ReadBuffer_common]].
- `delta_blk_write_time` cannot be normalized to time-per-write at `pg_stat_database` scope because the view exposes write time but no `blks_written` column in PG12. Pair the delta with write-call counts from `EXPLAIN ... BUFFERS`, `pg_stat_statements`, or `pg_stat_bgwriter` (`buffers_clean`, `buffers_backend`, `buffers_checkpoint`) to attribute the time [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_database|system_views.sql#pg_stat_database]], [[raw/postgres-12/doc/src/sgml/ref/explain.sgml#SQL-EXPLAIN|explain.sgml#SQL-EXPLAIN]].
- `temp_files` and `temp_bytes` identify temporary-file pressure at database scope, but PG12's database view exposes temp volume separately from `blk_read_time` and `blk_write_time` [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_database|system_views.sql#pg_stat_database]], [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg-stat-database-view|monitoring.sgml#pg-stat-database-view]].

### 6. Add query-level evidence when available

If `pg_stat_statements` is already installed and loaded, use it for query-level I/O timing:

```sql
SELECT /* wiki_io_timing_pgss_installed */
       extname,
       extversion
FROM pg_extension
WHERE extname = 'pg_stat_statements';

SELECT /* wiki_io_timing_top_statements */
       userid,
       dbid,
       queryid,
       calls,
       total_time,
       blk_read_time,
       blk_write_time,
       shared_blks_read,
       shared_blks_written,
       local_blks_read,
       local_blks_written,
       temp_blks_read,
       temp_blks_written,
       query
FROM pg_stat_statements
WHERE blk_read_time <> 0 OR blk_write_time <> 0
ORDER BY (blk_read_time + blk_write_time) DESC
LIMIT 20;
```

Only run the second query when the first query returns `pg_stat_statements` and the earlier `shared_preload_libraries` precheck shows that the module is loaded at server start. The PG12 control file pins `default_version = '1.7'`, so a fresh `CREATE EXTENSION pg_stat_statements` typically reports `extversion = 1.7`; the `blk_read_time` and `blk_write_time` columns have been part of the view since the 1.4 base file, applied through the 1.4 → 1.5 → 1.6 → 1.7 incremental scripts, so the same query works regardless of installed version [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.control|pg_stat_statements.control]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements--1.4.sql#pg_stat_statements|pg_stat_statements--1.4.sql#pg_stat_statements]]. The C code accumulates statement-level buffer-usage deltas into those columns in milliseconds [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pgss_store|pg_stat_statements.c#pgss_store]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pg_stat_statements_internal|pg_stat_statements.c#pg_stat_statements_internal]]. The PG12 docs state those statement I/O timing columns are zero when `track_io_timing` is not enabled [[raw/postgres-12/doc/src/sgml/pgstatstatements.sgml#pgstatstatements|pgstatstatements.sgml#pgstatstatements]].

Do not make `pg_stat_statements` a surprise dependency of this procedure. The module's `_PG_init()` only hooks into the system when loaded through `shared_preload_libraries`, and `shared_preload_libraries` is `PGC_POSTMASTER`, so adding it requires a server restart and should be planned as a separate change [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#_PG_init|pg_stat_statements.c#_PG_init]], [[raw/postgres-12/src/backend/utils/misc/guc.c#shared_preload_libraries|guc.c#shared_preload_libraries]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-shared-preload-libraries|config.sgml#guc-shared-preload-libraries]].

For an individual statement, use `EXPLAIN /* wiki_io_timing_plan_probe */ (ANALYZE, BUFFERS, TIMING OFF)` around an already-approved statement. `ANALYZE` executes the statement, so use this only for safe `SELECT`s or within a rollback wrapper for write statements; `BUFFERS` is what requests buffer usage, and `TIMING OFF` disables per-plan-node runtime timing while preserving whole-statement timing behavior [[raw/postgres-12/doc/src/sgml/ref/explain.sgml#SQL-EXPLAIN|explain.sgml#SQL-EXPLAIN]], [[raw/postgres-12/src/backend/commands/explain.c#ExplainOnePlan|explain.c#ExplainOnePlan]], [[raw/postgres-12/src/backend/commands/explain.c#show_buffer_usage|explain.c#show_buffer_usage]].

### 7. Disable or restore the previous default

If `track_io_timing` was off before the observation window, remove the `ALTER SYSTEM` override and reload:

```sql
ALTER /* wiki_io_timing_reset */ SYSTEM RESET track_io_timing;
SELECT /* wiki_io_timing_reload_after_reset */ pg_reload_conf();
SHOW /* wiki_io_timing_show_after_reset */ track_io_timing;
```

Use `ALTER SYSTEM RESET` rather than blindly setting `off` when you want to restore the underlying `postgresql.conf` or built-in default. `ALTER SYSTEM RESET` removes the entry from `postgresql.auto.conf`, and the next reload applies the remaining configuration source order [[raw/postgres-12/doc/src/sgml/ref/alter_system.sgml#ALTER-SYSTEM|alter_system.sgml#ALTER-SYSTEM]], [[raw/postgres-12/src/backend/utils/misc/guc.c#AlterSystemSetConfigFile|guc.c#AlterSystemSetConfigFile]].

## What PG12 Measures

The source-visible timing sites are in the buffer manager. In `ReadBuffer_common`, when `track_io_timing` is enabled, PostgreSQL records the current time before `smgrread()`, records it again after the read returns, adds the elapsed microseconds to the stats collector counter, and adds the interval to `pgBufferUsage.blk_read_time` [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common|bufmgr.c#ReadBuffer_common]], [[raw/postgres-12/src/include/pgstat.h#pgstat_count_buffer_read_time|pgstat.h#pgstat_count_buffer_read_time]]. In `FlushBuffer`, the same pattern wraps `smgrwrite()` and accumulates write time [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#FlushBuffer|bufmgr.c#FlushBuffer]], [[raw/postgres-12/src/include/pgstat.h#pgstat_count_buffer_write_time|pgstat.h#pgstat_count_buffer_write_time]].

Those two streams feed two surfaces:

- Database-level stats: backend-local `pgStatBlockReadTime` and `pgStatBlockWriteTime` are sent in `PgStat_MsgTabstat`, then the stats collector adds them to `PgStat_StatDBEntry.n_block_read_time` and `n_block_write_time`; `pg_stat_get_db_blk_read_time()` and `pg_stat_get_db_blk_write_time()` expose the values in milliseconds [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_send_tabstat|pgstat.c#pgstat_send_tabstat]], [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_recv_tabstat|pgstat.c#pgstat_recv_tabstat]], [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_read_time|pgstatfuncs.c#pg_stat_get_db_blk_read_time]].
- Per-statement and plan stats: `BufferUsage` carries `blk_read_time` and `blk_write_time`; executor instrumentation and `pg_stat_statements` accumulate deltas from `pgBufferUsage`, and `EXPLAIN` displays "I/O Timings" when buffer usage has non-zero timing values [[raw/postgres-12/src/include/executor/instrument.h#BufferUsage|instrument.h#BufferUsage]], [[raw/postgres-12/src/backend/executor/instrument.c#BufferUsageAdd|instrument.c#BufferUsageAdd]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pgss_store|pg_stat_statements.c#pgss_store]], [[raw/postgres-12/src/backend/commands/explain.c#show_buffer_usage|explain.c#show_buffer_usage]].

The resulting numbers are PostgreSQL block I/O call timings. They are not a full host I/O profiler: they do not directly identify disk model, filesystem queue depth, controller latency, or kernel page-cache residency. Pair them with block counts, wait events, OS storage telemetry, and workload context before making a storage conclusion.

## Restart, Reload, And Session Scope

| Change | PG12 context | Operational effect |
|---|---|---|
| `ALTER SYSTEM SET track_io_timing = on` | `track_io_timing` is `PGC_SUSET` | No restart. Reload applies the new default; existing sessions pick it up unless they have a session-local value. |
| `SET track_io_timing = on` | `PGC_SUSET` | Superuser-only session change. No reload and no restart. |
| `ALTER SYSTEM RESET track_io_timing` | `PGC_SUSET` | No restart. Reload removes the auto-conf override from the active defaults. |
| `SET statement_timeout` / `SET lock_timeout` | both `PGC_USERSET` | Session-scoped timeout guard. No reload and no restart. |
| Adding `pg_stat_statements` to `shared_preload_libraries` | `shared_preload_libraries` is `PGC_POSTMASTER` | Restart required; treat as separate planned maintenance. |

The context mapping comes from the PG12 `GucContext` enum and the documented `pg_settings.context` meanings: `postmaster` requires restart, `sighup` requires reload, and `superuser` / `user` can be set in-session with the documented permission limits [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#view-pg-settings]].

## Context Reviewed

- Navigation and bookkeeping: `wiki/versions.md`, `wiki/index.md`, the last 20 log entries via `scripts/recent_log --limit 20`, and `wiki/v12/index.md`.
- Context pack: `.wiki-runtime/context/postgres-12/manifest.md` confirmed pinned source path `raw/postgres-12`, source HEAD `45b88269a353ad93744772791feb6d01bc7e1e42`, generated compiler database, include dependencies, tree, build config, external dependency inventory, and focused callgraphs.
- Source lookup envelope: `scripts/source_lookup --version 12 --symbol track_io_timing`, `blk_read_time`, `pgstat_count_buffer_read_time`, `pgStatBlockReadTime`, `pgstat_report_stat`, `pg_stat_get_db_blk_write_time`, `pg_settings`, `pg_file_settings`, `shared_preload_libraries`, `statement_timeout`, `lock_timeout`, `pg_reload_conf`, `pg_stat_reset`, `pg_extension`; targeted slices in `guc.c`, `guc.h`, `bufmgr.c`, `pgstat.h`, `pgstat.c`, `pgstatfuncs.c`, `instrument.h`, `instrument.c`, `explain.c`, `system_views.sql`, `pg_proc.dat`, `gram.y`, `pg_extension.h`, `pg_stat_statements.c`, `pg_stat_statements--1.4.sql`, and the SGML docs cited above.
- Context-pack dependency checks: compile units for `src/backend/storage/buffer/bufmgr.c`, `src/backend/commands/explain.c`, `src/backend/utils/misc/guc.c`, `src/backend/postmaster/pgstat.c`, `src/backend/utils/adt/pgstatfuncs.c`, and `contrib/pg_stat_statements/pg_stat_statements.c`; direct includes for `bufmgr.c`, `explain.c`, `guc.c`, and `pg_stat_statements.c`.
- SQL snippet verification: `SET`, `SHOW`, `RESET`, `ALTER SYSTEM`, and `EXPLAIN` syntax checked against `gram.y`; referenced views and catalogs checked against `system_views.sql`, `pg_extension.h`, `pg_proc.dat`, and extension SQL files. Every production-bound SQL statement above carries an inline `/* wiki_... */` tag after the leading verb, and the timeout settings are session-scoped.
- Tests inspected: regression view-definition output confirms `pg_stat_database` exposes `pg_stat_get_db_blk_read_time()` and `pg_stat_get_db_blk_write_time()`; `pg_stat_statements` extension SQL and C sources expose and accumulate statement-level I/O timing columns. No dedicated PG12 regression test was found that toggles `track_io_timing` and asserts non-zero timing output.

## Evidence Map

- GUC default, permission, and scope: `track_io_timing` entry in [[raw/postgres-12/src/backend/utils/misc/guc.c#track_io_timing|guc.c#track_io_timing]], `GucContext` semantics in [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]], and context text in [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#view-pg-settings]].
- Host overhead preflight: `track_io_timing` docs in [[raw/postgres-12/doc/src/sgml/config.sgml#guc-track-io-timing|config.sgml#guc-track-io-timing]] and `pg_test_timing` docs in [[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml#pgtesttiming|pgtesttiming.sgml#pgtesttiming]].
- Read/write timing sites: [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common|bufmgr.c#ReadBuffer_common]], [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#FlushBuffer|bufmgr.c#FlushBuffer]], and macros in [[raw/postgres-12/src/include/pgstat.h#pgstat_count_buffer_read_time|pgstat.h#pgstat_count_buffer_read_time]].
- Database-level exposure: [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_send_tabstat|pgstat.c#pgstat_send_tabstat]], [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_recv_tabstat|pgstat.c#pgstat_recv_tabstat]], [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_db_blk_read_time|pgstatfuncs.c#pg_stat_get_db_blk_read_time]], and [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_database|system_views.sql#pg_stat_database]].
- Query-level exposure: [[raw/postgres-12/src/include/executor/instrument.h#BufferUsage|instrument.h#BufferUsage]], [[raw/postgres-12/src/backend/executor/instrument.c#BufferUsageAdd|instrument.c#BufferUsageAdd]], [[raw/postgres-12/src/backend/commands/explain.c#show_buffer_usage|explain.c#show_buffer_usage]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c#pgss_store|pg_stat_statements.c#pgss_store]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements--1.4.sql#pg_stat_statements|pg_stat_statements--1.4.sql#pg_stat_statements]], and [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.control|pg_stat_statements.control]].
- Production change mechanics: [[raw/postgres-12/doc/src/sgml/ref/alter_system.sgml#ALTER-SYSTEM|alter_system.sgml#ALTER-SYSTEM]], [[raw/postgres-12/src/backend/utils/misc/guc.c#AlterSystemSetConfigFile|guc.c#AlterSystemSetConfigFile]], and [[raw/postgres-12/src/backend/storage/ipc/signalfuncs.c#pg_reload_conf|signalfuncs.c#pg_reload_conf]].

## Open Questions

- The PG12 test tree does not appear to contain a dedicated test that enables `track_io_timing` and asserts non-zero I/O timing output. The page therefore relies on direct source tracing and existing view-definition/extension coverage rather than a behavioral test fixture for this GUC.

## Source References

- Source pin and context pack: [[raw/postgres-12/]], `.wiki-runtime/context/postgres-12/manifest.md`
- GUC and reload mechanics: [[raw/postgres-12/src/backend/utils/misc/guc.c|guc.c]], [[raw/postgres-12/src/include/utils/guc.h|guc.h]], [[raw/postgres-12/src/backend/storage/ipc/signalfuncs.c|signalfuncs.c]]
- Timing collection and stats exposure: [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c|bufmgr.c]], [[raw/postgres-12/src/include/pgstat.h|pgstat.h]], [[raw/postgres-12/src/backend/postmaster/pgstat.c|pgstat.c]], [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c|pgstatfuncs.c]], [[raw/postgres-12/src/backend/catalog/system_views.sql|system_views.sql]]
- Query-level surfaces: [[raw/postgres-12/src/backend/commands/explain.c|explain.c]], [[raw/postgres-12/src/include/executor/instrument.h|instrument.h]], [[raw/postgres-12/src/backend/executor/instrument.c|instrument.c]], [[raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c|pg_stat_statements.c]]
- Documentation: [[raw/postgres-12/doc/src/sgml/config.sgml|config.sgml]], [[raw/postgres-12/doc/src/sgml/monitoring.sgml|monitoring.sgml]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml|catalogs.sgml]], [[raw/postgres-12/doc/src/sgml/ref/alter_system.sgml|alter_system.sgml]], [[raw/postgres-12/doc/src/sgml/ref/explain.sgml|explain.sgml]], [[raw/postgres-12/doc/src/sgml/ref/pgtesttiming.sgml|pgtesttiming.sgml]], [[raw/postgres-12/doc/src/sgml/pgstatstatements.sgml|pgstatstatements.sgml]]
