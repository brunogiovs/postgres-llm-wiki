---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: claude-opus-4-7 2026-05-08T00:00:00Z
---

# Checkpoint monitoring and optimization scenarios

## Question

In PostgreSQL 12, how should checkpoint behavior be monitored and optimized? Include practical deployment scenarios, including very fast local disks and cloud block storage such as AWS or Azure disks, while grounding PostgreSQL-side claims in the pinned PostgreSQL 12 source. Also include a production-safe SQL query to list all checkpoint-related configuration settings relevant to this investigation.

## Answer

Assumption: "PostgreSQL 12" means the local source checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`.

The useful PostgreSQL-side checkpoint loop is: measure checkpoint rate, measure write and fsync cost, decide whether checkpoints are time-driven or WAL-pressure-driven, then tune `max_wal_size`, `checkpoint_timeout`, `checkpoint_completion_target`, and `checkpoint_flush_after` inside the disk-space and crash-recovery budget. In PG 12, checkpoint counters are exposed through `pg_stat_bgwriter`, and optional checkpoint log lines expose per-checkpoint write/sync/total timings, WAL segment churn, sync file counts, longest sync, average sync, and WAL distance estimates [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_bgwriter|system_views.sql#pg_stat_bgwriter]], [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg-stat-bgwriter-view|monitoring.sgml#pg-stat-bgwriter-view]], [[raw/postgres-12/src/backend/access/transam/xlog.c#LogCheckpointEnd|xlog.c#LogCheckpointEnd]].

### What PG 12 checkpoints do

The checkpointer starts a timed checkpoint when `elapsed_secs >= CheckPointTimeout`, and it counts that in `m_timed_checkpoints` when there was no external checkpoint request already pending [[raw/postgres-12/src/backend/postmaster/checkpointer.c#CheckpointerMain|checkpointer.c#CheckpointerMain]]. WAL pressure takes a different path: when a WAL segment is finished, `XLogWrite` checks `XLogCheckpointNeeded()` and requests a checkpoint with `CHECKPOINT_CAUSE_XLOG` when the segment distance from the redo pointer reaches the configured checkpoint segment threshold [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogWrite|xlog.c#XLogWrite]], [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogCheckpointNeeded|xlog.c#XLogCheckpointNeeded]].

During the checkpoint, `CheckPointGuts()` calls `CheckPointBuffers()`, which timestamps the write phase, runs `BufferSync()`, timestamps the sync phase, and then processes pending sync requests [[raw/postgres-12/src/backend/access/transam/xlog.c#CheckPointGuts|xlog.c#CheckPointGuts]], [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#CheckPointBuffers|bufmgr.c#CheckPointBuffers]]. `BufferSync()` marks dirty shared buffers that need checkpoint writes with `BM_CHECKPOINT_NEEDED`, writes those buffers, and invokes `CheckpointWriteDelay()` after each processed buffer to pace the write rate [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BufferSync|bufmgr.c#BufferSync]]. The pacing function uses `checkpoint_completion_target`, elapsed time, `checkpoint_timeout`, and WAL segment progress to decide whether the checkpointer can sleep or must catch up [[raw/postgres-12/src/backend/postmaster/checkpointer.c#CheckpointWriteDelay|checkpointer.c#CheckpointWriteDelay]], [[raw/postgres-12/src/backend/postmaster/checkpointer.c#IsCheckpointOnSchedule|checkpointer.c#IsCheckpointOnSchedule]].

`max_wal_size` is not a hard storage cap. PG 12 computes `CheckPointSegments` from `max_wal_size` and `checkpoint_completion_target`, and the docs call `max_wal_size` a soft limit that can be exceeded under heavy load, archive failure, or high WAL retention settings [[raw/postgres-12/src/backend/access/transam/xlog.c#CalculateCheckpointSegments|xlog.c#CalculateCheckpointSegments]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-max-wal-size|config.sgml#guc-max-wal-size]]. WAL recycling/removal is also constrained by `min_wal_size`, recent checkpoint-cycle WAL demand, archiving, `wal_keep_segments`, and replication slots [[raw/postgres-12/src/backend/access/transam/xlog.c#XLOGfileslop|xlog.c#XLOGfileslop]], [[raw/postgres-12/src/backend/access/transam/xlog.c#KeepLogSeg|xlog.c#KeepLogSeg]], [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L559-L589]].

### Monitoring checklist

Use `pg_stat_bgwriter` for cluster-level rates and accumulated costs. `checkpoints_timed` shows scheduled checkpoints; `checkpoints_req` shows requested checkpoints; `checkpoint_write_time` and `checkpoint_sync_time` are accumulated milliseconds spent writing and synchronizing checkpoint files; `buffers_checkpoint` is checkpoint-written buffers; `buffers_backend_fsync` shows cases where a backend had to execute its own fsync because the checkpointer request queue could not absorb the work [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg-stat-bgwriter-view|monitoring.sgml#pg-stat-bgwriter-view]], [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_bgwriter_timed_checkpoints|pgstatfuncs.c#pg_stat_get_bgwriter_timed_checkpoints]], [[raw/postgres-12/src/backend/postmaster/checkpointer.c#ForwardSyncRequest|checkpointer.c#ForwardSyncRequest]], [[raw/postgres-12/src/backend/postmaster/checkpointer.c#AbsorbSyncRequests|checkpointer.c#AbsorbSyncRequests]].

```sql
SET /* wiki_checkpoint_monitor_statement_timeout */ statement_timeout = '30s';
SET /* wiki_checkpoint_monitor_lock_timeout */ lock_timeout = '5s';

SELECT /* wiki_checkpoint_bgwriter_sample */
       now() AS sampled_at,
       checkpoints_timed,
       checkpoints_req,
       checkpoints_req::numeric / NULLIF(checkpoints_timed + checkpoints_req, 0) AS requested_checkpoint_fraction,
       checkpoint_write_time,
       checkpoint_sync_time,
       buffers_checkpoint,
       buffers_backend,
       buffers_backend_fsync,
       stats_reset
  FROM pg_stat_bgwriter;
```

Those `SET` timeouts are session-scoped because `statement_timeout` and `lock_timeout` are `PGC_USERSET`; choose values appropriate for the production observation window [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout|guc.c#statement_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout|guc.c#lock_timeout]], [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]]. If you reset the baseline, remember that `pg_stat_reset_shared('bgwriter')` zeros every counter in `pg_stat_bgwriter` for the cluster, so it can disrupt other monitoring [[raw/postgres-12/doc/src/sgml/monitoring.sgml|monitoring.sgml#L3272-L3279]], [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_reset_shared_counters|pgstat.c#pgstat_reset_shared_counters]].

Capture the relevant runtime configuration before changing anything. PG 12 defines `pg_settings` as `SELECT * FROM pg_show_all_settings()` and documents the columns used below: `setting`, `unit`, `context`, `source`, `sourcefile`, `sourceline`, `pending_restart`, `boot_val`, `reset_val`, `min_val`, `max_val`, and `short_desc` [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_settings|system_views.sql#pg_settings]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#view-pg-settings]]. `sourcefile` and `sourceline` can be null when the value did not come from a configuration file or when the querying role lacks the documented visibility privilege [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#view-pg-settings]].

```sql
SET /* wiki_checkpoint_config_statement_timeout */ statement_timeout = '30s';
SET /* wiki_checkpoint_config_lock_timeout */ lock_timeout = '5s';

SELECT /* wiki_checkpoint_config_inventory */
       CASE
         WHEN name IN (
           'checkpoint_timeout',
           'checkpoint_completion_target',
           'checkpoint_flush_after',
           'checkpoint_warning',
           'max_wal_size',
           'min_wal_size',
           'log_checkpoints'
         ) THEN 'direct checkpoint control'
         WHEN name IN (
           'full_page_writes',
           'wal_compression',
           'wal_log_hints'
         ) THEN 'WAL volume after checkpoints'
         WHEN name IN (
           'archive_mode',
           'archive_command',
           'archive_timeout',
           'wal_keep_segments',
           'max_replication_slots'
         ) THEN 'WAL retention or archive pressure'
       END AS investigation_group,
       name,
       setting,
       unit,
       context,
       source,
       sourcefile,
       sourceline,
       pending_restart,
       boot_val,
       reset_val,
       min_val,
       max_val,
       short_desc
  FROM pg_settings
 WHERE name IN (
       'checkpoint_timeout',
       'checkpoint_completion_target',
       'checkpoint_flush_after',
       'checkpoint_warning',
       'max_wal_size',
       'min_wal_size',
       'log_checkpoints',
       'full_page_writes',
       'wal_compression',
       'wal_log_hints',
       'archive_mode',
       'archive_command',
       'archive_timeout',
       'wal_keep_segments',
       'max_replication_slots'
 )
 ORDER BY investigation_group, name;
```

Read `context` before proposing a change: in PG 12, `postmaster` means restart required; `sighup` means reload; `superuser` / `user` can be changed at session scope by roles with the required privilege and may also be set as configuration defaults [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]]. The query intentionally includes adjacent WAL/archive settings because WAL retention and full-page-write volume can make checkpoint symptoms look like checkpoint tuning problems: `full_page_writes` writes full pages after checkpoints, `wal_compression` compresses those full-page writes, `wal_log_hints` is postmaster-only and also writes full pages after checkpoints for hint-bit changes, archiving settings can prevent old WAL removal, and replication slots / `wal_keep_segments` can retain WAL beyond normal checkpoint recycling [[raw/postgres-12/src/backend/utils/misc/guc.c#full_page_writes|guc.c#full_page_writes]], [[raw/postgres-12/src/backend/utils/misc/guc.c#wal_compression|guc.c#wal_compression]], [[raw/postgres-12/src/backend/utils/misc/guc.c#wal_log_hints|guc.c#wal_log_hints]], [[raw/postgres-12/src/backend/utils/misc/guc.c#archive_command|guc.c#archive_command]], [[raw/postgres-12/src/backend/utils/misc/guc.c#archive_mode|guc.c#archive_mode]], [[raw/postgres-12/src/backend/access/transam/xlog.c#KeepLogSeg|xlog.c#KeepLogSeg]], [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L579-L588]].

Enable `log_checkpoints` during tuning when per-checkpoint shape matters. The GUC is `PGC_SIGHUP` and defaults off [[raw/postgres-12/src/backend/utils/misc/guc.c#log_checkpoints|guc.c#log_checkpoints]]. With it enabled, PG 12 logs checkpoint start causes such as `wal` or `time`, and checkpoint completion lines include written buffers, added/removed/recycled WAL files, write/sync/total times, sync file count, longest and average sync, distance, and estimate [[raw/postgres-12/src/backend/access/transam/xlog.c#LogCheckpointStart|xlog.c#LogCheckpointStart]], [[raw/postgres-12/src/backend/access/transam/xlog.c#LogCheckpointEnd|xlog.c#LogCheckpointEnd]]. Apply it with reload, not restart:

```sql
SET /* wiki_checkpoint_guc_statement_timeout */ statement_timeout = '30s';
SET /* wiki_checkpoint_guc_lock_timeout */ lock_timeout = '5s';
ALTER /* wiki_checkpoint_enable_logs */ SYSTEM SET log_checkpoints = on;
SELECT /* wiki_checkpoint_reload_conf */ pg_reload_conf();
```

`ALTER SYSTEM` changes take effect after reload for reloadable settings, and `pg_reload_conf()` sends `SIGHUP` to the postmaster [[raw/postgres-12/doc/src/sgml/ref/alter_system.sgml|alter_system.sgml#L48-L60]], [[raw/postgres-12/src/backend/storage/ipc/signalfuncs.c#pg_reload_conf|signalfuncs.c#pg_reload_conf]].

### Tuning knobs

All checkpoint knobs in this table are `PGC_SIGHUP`, so configuration-file or `ALTER SYSTEM` changes need reload (`pg_reload_conf()`, `pg_ctl reload`, or `SIGHUP`) and do not require a PostgreSQL restart. They are not per-session `SET` tuning levers in the way `PGC_USERSET` settings are [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_timeout|guc.c#checkpoint_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_completion_target|guc.c#checkpoint_completion_target]], [[raw/postgres-12/doc/src/sgml/config.sgml|config.sgml#L170-L183]].

| Knob | PG 12 default and range | Use it when | Trade-off |
|---|---|---|---|
| `max_wal_size` | default `1GB`, minimum `2MB`; soft trigger for WAL-driven checkpoints | `checkpoints_req` is high, checkpoint logs show `wal`, or the log warns that checkpoints are occurring too frequently | More WAL can need more crash recovery time and more `pg_wal` headroom [[raw/postgres-12/src/backend/utils/misc/guc.c#max_wal_size|guc.c#max_wal_size]], [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L489-L519]] |
| `checkpoint_timeout` | default `5min`, range `30s` to `1d` | Timed checkpoints are too frequent for the desired write-amortization window | Longer timeout can increase crash recovery time [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_timeout|guc.c#checkpoint_timeout]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-checkpoint-timeout|config.sgml#guc-checkpoint-timeout]] |
| `checkpoint_completion_target` | default `0.5`, range `0.0` to `1.0` | Checkpoint writes or syncs create latency bursts; especially when normal workload is close to storage throughput | Higher values spread writes but can keep more WAL for recovery; docs advise staying below `1.0`, perhaps `0.9` at most [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_completion_target|guc.c#checkpoint_completion_target]], [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L522-L546]] |
| `checkpoint_flush_after` | default `256kB` on Linux, `0` elsewhere; range `0` to `2MB` in blocks | `checkpoint_sync_time` or checkpoint log `longest` sync shows end-of-checkpoint fsync stalls | Can reduce transaction latency by forcing earlier OS writeback, but may degrade workloads larger than `shared_buffers` and smaller than OS page cache; may have no effect on some platforms [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_flush_after|guc.c#checkpoint_flush_after]], [[raw/postgres-12/src/include/pg_config_manual.h#DEFAULT_CHECKPOINT_FLUSH_AFTER|pg_config_manual.h#DEFAULT_CHECKPOINT_FLUSH_AFTER]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-checkpoint-flush-after|config.sgml#guc-checkpoint-flush-after]] |
| `min_wal_size` | default `80MB`, minimum `2MB` | Repeated WAL file creation/removal churn appears around bursts and enough disk is reserved for recycled WAL | It reserves/recycles WAL for future use below the max limit; it does not itself stop WAL-driven checkpoints [[raw/postgres-12/src/backend/utils/misc/guc.c#min_wal_size|guc.c#min_wal_size]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-min-wal-size|config.sgml#guc-min-wal-size]] |
| `checkpoint_warning` | default `30s`, `0` disables | Keep it enabled as a guardrail while tuning WAL-driven checkpoint frequency | Only warns for WAL-caused checkpoints closer together than the threshold; no warning is generated when `checkpoint_timeout < checkpoint_warning` [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_warning|guc.c#checkpoint_warning]], [[raw/postgres-12/src/backend/postmaster/checkpointer.c#CheckpointerMain|checkpointer.c#CheckpointerMain]] |

### Deployment scenarios

| Scenario | Source-grounded posture |
|---|---|
| Very fast local SSD or NVMe with low sync time | Do not shorten checkpoints just because storage is fast. Frequent checkpoints still increase dirty-page flush frequency and, with `full_page_writes` enabled, can increase WAL volume after each checkpoint; use the fast device to keep `checkpoint_sync_time` low, and size `max_wal_size` / `checkpoint_timeout` around recovery time and WAL space rather than around raw IOPS [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L489-L520]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-max-wal-size|config.sgml#guc-max-wal-size]]. |
| Write-heavy database on fast disks | If checkpoint logs are mostly `wal` and `checkpoints_req` rises quickly, raise `max_wal_size` first so checkpoints are not forced by WAL consumption before the intended interval; then raise `checkpoint_completion_target` toward the documented high end if writes create bursts [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogCheckpointNeeded|xlog.c#XLogCheckpointNeeded]], [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L522-L546]]. |
| Cloud block storage such as AWS EBS or Azure managed disks | Treat the vendor disk as measured storage with possible write/sync variability. PostgreSQL does not contain AWS/Azure-specific checkpoint logic in this source slice; use `log_checkpoints` and `pg_stat_bgwriter` to observe `sync`, `longest`, `average`, `checkpoint_sync_time`, and WAL-caused checkpoint frequency, then prefer smoother write pacing (`checkpoint_completion_target` below `1.0`) and enough `max_wal_size` headroom to avoid rapid requested checkpoints [[raw/postgres-12/src/backend/access/transam/xlog.c#LogCheckpointEnd|xlog.c#LogCheckpointEnd]], [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L522-L546]]. |
| Burst-limited or throughput-limited cloud disk | If `checkpoint_sync_time` or log `longest` sync spikes at checkpoint end, keep `checkpoint_flush_after` nonzero on Linux and validate it on the actual volume class; if the documented regression shape appears, test `checkpoint_flush_after = 0` during a bounded window [[raw/postgres-12/doc/src/sgml/config.sgml#guc-checkpoint-flush-after|config.sgml#guc-checkpoint-flush-after]], [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BufferSync|bufmgr.c#BufferSync]]. |
| Standby or archive-recovery system | Monitor restartpoints similarly, but leave extra WAL headroom: PG 12 docs state that restartpoints can only happen at checkpoint records and `max_wal_size` is often exceeded during recovery by up to one checkpoint cycle's worth of WAL [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L591-L608]], [[raw/postgres-12/src/backend/access/transam/xlog.c#CreateRestartPoint|xlog.c#CreateRestartPoint]]. |
| Bulk load or batch window | Temporarily raising `max_wal_size` and possibly `checkpoint_timeout` can reduce repeated WAL-driven checkpoints during the burst, but reset after the window if the larger recovery/WAL-space budget is not acceptable. `checkpoint_warning` exists specifically to surface too-frequent WAL-caused checkpoints and points at `max_wal_size` when that happens [[raw/postgres-12/src/backend/postmaster/checkpointer.c#CheckpointerMain|checkpointer.c#CheckpointerMain]], [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L504-L519]]. |

### Practical sequence

1. Enable `log_checkpoints` for a bounded window and collect `pg_stat_bgwriter` samples before and after a representative workload interval.
2. If `checkpoints_req` dominates or logs show `checkpoint starting: wal`, increase `max_wal_size` first, provided `pg_wal` disk headroom and recovery objectives allow it.
3. If checkpoint write load is bursty, increase `checkpoint_completion_target` toward `0.7` to `0.9`; keep it below `1.0` because PG 12 docs warn that `1.0` is likely to miss completion on time.
4. If sync time is the pain point on Linux, test `checkpoint_flush_after` rather than only increasing WAL size; if it regresses the documented OS-page-cache-sized workload, test disabling it.
5. Re-sample, compare deltas, and keep the smallest setting changes that move checkpoint rate and sync time in the desired direction.

## Context Reviewed

- Navigation and bookkeeping: `wiki/versions.md`, `wiki/index.md`, `scripts/recent_log --limit 20`, and `wiki/v12/index.md`.
- Context pack: `.wiki-runtime/context/postgres-12/manifest.md` confirmed source path `raw/postgres-12`, pinned commit `45b88269a353ad93744772791feb6d01bc7e1e42`, generated compile database, include dependencies, tree context, and no failed artifacts.
- Context artifacts used: `tree-L4.txt`, `include-deps.txt`, `compile_commands.json`, `scripts/source_deps --version 12 --compile-unit src/backend/postmaster/checkpointer.c --full-command`, direct and transitive include queries for `src/backend/postmaster/checkpointer.c`, and reverse include users of `access/xlog.h`.
- Source search envelope: targeted `scripts/source_lookup --version 12` searches and slices for `checkpoint_timeout`, `checkpoint_completion_target`, `checkpoint_flush_after`, `checkpoint_warning`, `max_wal_size`, `min_wal_size`, `log_checkpoints`, `full_page_writes`, `wal_compression`, `wal_log_hints`, `archive_mode`, `archive_command`, `archive_timeout`, `wal_keep_segments`, `max_replication_slots`, `pg_settings`, `CheckpointerMain`, `CheckpointWriteDelay`, `IsCheckpointOnSchedule`, `RequestCheckpoint`, `ForwardSyncRequest`, `AbsorbSyncRequests`, `CalculateCheckpointSegments`, `XLOGfileslop`, `XLogCheckpointNeeded`, `XLogWrite`, `CreateCheckPoint`, `CreateRestartPoint`, `CheckPointGuts`, `CheckPointBuffers`, `BufferSync`, `LogCheckpointStart`, `LogCheckpointEnd`, `pg_stat_bgwriter`, `pg_stat_reset_shared`, `pg_reload_conf`, `statement_timeout`, and `lock_timeout`.
- SQL syntax checked against PG 12 grammar for `SELECT`, `CASE`, `IN`, and `ORDER BY`; `pg_settings` column availability checked against the v12 view definition and catalog documentation.
- Tests and generated definitions checked: `src/test/regress/expected/rules.out` for the `pg_stat_bgwriter` view shape; recovery and contrib tests containing `CHECKPOINT`, `log_checkpoints`, `checkpoint_timeout`, and `checkpoint_completion_target` were searched. The v12 tree has tests using checkpoints as recovery/logical-decoding fixtures, but no source test that encodes vendor-specific checkpoint tuning recommendations.

## Evidence Map

- Checkpoint trigger causes: timed trigger in [[raw/postgres-12/src/backend/postmaster/checkpointer.c#CheckpointerMain|checkpointer.c#CheckpointerMain]]; WAL segment trigger in [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogWrite|xlog.c#XLogWrite]] and [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogCheckpointNeeded|xlog.c#XLogCheckpointNeeded]].
- Checkpoint work phases: [[raw/postgres-12/src/backend/access/transam/xlog.c#CheckPointGuts|xlog.c#CheckPointGuts]], [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#CheckPointBuffers|bufmgr.c#CheckPointBuffers]], [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BufferSync|bufmgr.c#BufferSync]], [[raw/postgres-12/src/backend/postmaster/checkpointer.c#CheckpointWriteDelay|checkpointer.c#CheckpointWriteDelay]], and [[raw/postgres-12/src/backend/postmaster/checkpointer.c#IsCheckpointOnSchedule|checkpointer.c#IsCheckpointOnSchedule]].
- Monitoring surfaces: view definition in [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_bgwriter|system_views.sql#pg_stat_bgwriter]], docs in [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg-stat-bgwriter-view|monitoring.sgml#pg-stat-bgwriter-view]], SQL functions in [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#pg_stat_get_bgwriter_timed_checkpoints|pgstatfuncs.c#pg_stat_get_bgwriter_timed_checkpoints]], stats message/rollup in [[raw/postgres-12/src/include/pgstat.h#PgStat_MsgBgWriter|pgstat.h#PgStat_MsgBgWriter]] and [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_recv_bgwriter|pgstat.c#pgstat_recv_bgwriter]], and checkpoint logging in [[raw/postgres-12/src/backend/access/transam/xlog.c#LogCheckpointStart|xlog.c#LogCheckpointStart]] / [[raw/postgres-12/src/backend/access/transam/xlog.c#LogCheckpointEnd|xlog.c#LogCheckpointEnd]].
- Tuning knobs and reload semantics: GUC definitions in [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_timeout|guc.c#checkpoint_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_completion_target|guc.c#checkpoint_completion_target]], [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_flush_after|guc.c#checkpoint_flush_after]], [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_warning|guc.c#checkpoint_warning]], [[raw/postgres-12/src/backend/utils/misc/guc.c#max_wal_size|guc.c#max_wal_size]], [[raw/postgres-12/src/backend/utils/misc/guc.c#min_wal_size|guc.c#min_wal_size]], and [[raw/postgres-12/src/backend/utils/misc/guc.c#log_checkpoints|guc.c#log_checkpoints]]; reload behavior in [[raw/postgres-12/doc/src/sgml/config.sgml|config.sgml#L170-L183]], [[raw/postgres-12/doc/src/sgml/ref/alter_system.sgml|alter_system.sgml#L48-L60]], and [[raw/postgres-12/src/backend/storage/ipc/signalfuncs.c#pg_reload_conf|signalfuncs.c#pg_reload_conf]].
- Configuration inventory query: `pg_settings` view shape in [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_settings|system_views.sql#pg_settings]] and column docs in [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#view-pg-settings]]; adjacent WAL/archive GUCs in [[raw/postgres-12/src/backend/utils/misc/guc.c#full_page_writes|guc.c#full_page_writes]], [[raw/postgres-12/src/backend/utils/misc/guc.c#archive_timeout|guc.c#archive_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#wal_keep_segments|guc.c#wal_keep_segments]], [[raw/postgres-12/src/backend/utils/misc/guc.c#max_replication_slots|max_replication_slots]], [[raw/postgres-12/src/backend/utils/misc/guc.c#archive_command|guc.c#archive_command]], and [[raw/postgres-12/src/backend/utils/misc/guc.c#archive_mode|guc.c#archive_mode]].
- WAL retention and checkpoint segment sizing: [[raw/postgres-12/src/backend/access/transam/xlog.c#CalculateCheckpointSegments|xlog.c#CalculateCheckpointSegments]], [[raw/postgres-12/src/backend/access/transam/xlog.c#XLOGfileslop|xlog.c#XLOGfileslop]], [[raw/postgres-12/src/backend/access/transam/xlog.c#KeepLogSeg|xlog.c#KeepLogSeg]], and WAL docs in [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L470-L608]].

## Open Questions

- The pinned PostgreSQL 12 source does not contain AWS- or Azure-specific disk behavior, IOPS limits, burst-credit mechanics, or cloud metric names. The cloud guidance above is therefore framed as PostgreSQL-side tuning by observed `pg_stat_bgwriter` and `log_checkpoints` signals, not as vendor-specific storage sizing advice.
- The source documents direction and constraints, but it does not encode universal numeric targets for `max_wal_size`, `checkpoint_timeout`, or `checkpoint_completion_target`. Final values must be chosen from measured checkpoint interval, WAL generation rate, available `pg_wal` space, acceptable crash recovery time, and observed sync latency.

## Source References

- Source pin and context pack: [[raw/postgres-12/]], `.wiki-runtime/context/postgres-12/manifest.md`
- Checkpointer and checkpoint pacing: [[raw/postgres-12/src/backend/postmaster/checkpointer.c|checkpointer.c]], [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c|bufmgr.c]], [[raw/postgres-12/src/backend/access/transam/xlog.c|xlog.c]]
- WAL/checkpoint headers and generated context: [[raw/postgres-12/src/include/access/xlog.h|xlog.h]], [[raw/postgres-12/src/include/pgstat.h|pgstat.h]], `.wiki-runtime/context/postgres-12/include-deps.txt`, `.wiki-runtime/context/postgres-12/compile_commands.json`
- Checkpoint and WAL GUC definitions: [[raw/postgres-12/src/backend/utils/misc/guc.c|guc.c]], [[raw/postgres-12/src/include/pg_config_manual.h|pg_config_manual.h]], [[raw/postgres-12/doc/src/sgml/config.sgml|config.sgml]], [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml]]
- Monitoring and stats wiring: [[raw/postgres-12/src/backend/catalog/system_views.sql|system_views.sql]], [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c|pgstatfuncs.c]], [[raw/postgres-12/src/backend/postmaster/pgstat.c|pgstat.c]], [[raw/postgres-12/doc/src/sgml/monitoring.sgml|monitoring.sgml]]
- Runtime configuration inventory: [[raw/postgres-12/doc/src/sgml/catalogs.sgml|catalogs.sgml]], [[raw/postgres-12/src/backend/parser/gram.y|gram.y]]
- Reload and production SQL support: [[raw/postgres-12/doc/src/sgml/ref/alter_system.sgml|alter_system.sgml]], [[raw/postgres-12/src/backend/storage/ipc/signalfuncs.c|signalfuncs.c]], [[raw/postgres-12/src/include/utils/guc.h|guc.h]]
- Tests and view-shape checks: [[raw/postgres-12/src/test/regress/expected/rules.out|rules.out]], `raw/postgres-12/src/test/recovery/`, `raw/postgres-12/contrib/test_decoding/`
