---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Azure disk configuration recommendations (unverified)

## Question

In PostgreSQL 12, give configuration and setting recommendations for a database using these prompt-provided Azure cloud disk options:

| Azure disk type | Prompt-provided shape |
|---|---|
| Ultra Disk (SSD) | Extreme I/O-intensive workloads; maximum 64 TiB, 400000 IOPS, 10000 MB/s; not usable as OS disk; sub-millisecond latency; configurable IOPS and throughput without rebooting. |
| Premium SSD v2 | High-performance production apps; maximum 64 TiB, 80000 IOPS, 2000 MB/s; not usable as OS disk; granular provisioning. |
| Premium SSD | Mission-critical production workloads; maximum 32 TiB, 20000 IOPS, 900 MB/s; usable as OS disk; supports bursting. |
| Standard SSD | Web servers, lightly used apps, development and test; maximum 32 TiB, 6000 IOPS, 750 MB/s; usable as OS disk. |
| Standard HDD | Cheapest option for backups, cold storage, and sequential/low-IOPS data; maximum 32 TiB; usable as OS disk until September 2028. |

Ground PostgreSQL-side configuration claims in the pinned PostgreSQL 12 source and source-context pack. Treat Azure disk characteristics as inputs from the prompt, not as PostgreSQL source facts.

## Answer

Assumption: "PostgreSQL 12" means the local checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`. The PostgreSQL 12 source contains no Azure-specific storage-class logic, so the recommendations below map the prompt-provided disk shapes onto PG 12 settings whose behavior is source-visible.

The practical posture is:

1. Keep durability settings conservative: `fsync = on` and `full_page_writes = on` for any production database. PG 12 documents that disabling `fsync` can cause unrecoverable corruption after power or OS failure, and that disabling `full_page_writes` can cause unrecoverable or silent corruption after failure [[raw/postgres-12/doc/src/sgml/config.sgml#guc-fsync|config.sgml#fsync]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-full-page-writes|config.sgml#full_page_writes]].
2. Put the hottest OLTP data, `pg_wal`, and temp-spill space on the fastest provisioned storage you can justify. PG 12 can place WAL outside the data directory at `initdb` time with `--waldir`, can place tables/indexes in tablespaces, and can place temporary files through `temp_tablespaces` [[raw/postgres-12/doc/src/sgml/ref/initdb.sgml#L340-L347|initdb.sgml#L340-L347]], [[raw/postgres-12/doc/src/sgml/manage-ag.sgml#manage-ag-tablespaces|manage-ag.sgml#manage-ag-tablespaces]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-temp-tablespaces|config.sgml#temp_tablespaces]].
3. Use disk-class-specific planner settings only when the storage behavior differs enough to affect plan choices. `random_page_cost`, `seq_page_cost`, and `effective_io_concurrency` can be overridden per tablespace, which is useful when one tablespace is on a faster or slower disk than the rest [[raw/postgres-12/doc/src/sgml/ref/alter_tablespace.sgml#sql-altertablespace|alter_tablespace.sgml#sql-altertablespace]], [[raw/postgres-12/src/backend/utils/cache/spccache.c#get_tablespace_page_costs|spccache.c#get_tablespace_page_costs]].
4. Make checkpoint and background-writer settings measurement-driven. Frequent checkpoints are expensive because they flush dirty pages and increase later full-page-write WAL traffic; PG 12 docs recommend setting checkpoint parameters high enough that checkpoints do not happen too often, while keeping crash-recovery and `pg_wal` space budgets in mind [[raw/postgres-12/doc/src/sgml/wal.sgml#wal-configuration|wal.sgml#wal-configuration]].

### Disk-class starting points

The numeric planner values in this table are starting probes, not source-defined constants. PG 12 says there is no well-defined method for ideal planner cost constants, that SSDs can be modeled with lower `random_page_cost`, and that `effective_io_concurrency` on SSD or memory-based storage may be in the hundreds [[raw/postgres-12/doc/src/sgml/config.sgml#runtime-config-query-constants|config.sgml#runtime-config-query-constants]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-random-page-cost|config.sgml#random_page_cost]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-effective-io-concurrency|config.sgml#effective_io_concurrency]].

| Disk class | Recommended PostgreSQL role | Planner starting point | Checkpoint/WAL posture | Notes |
|---|---|---|---|---|
| Ultra Disk | Primary data and `pg_wal` for write-heavy OLTP, high-concurrency bitmap scans, and temp spill workloads that must stay low latency. | Keep `seq_page_cost = 1.0`; start `random_page_cost` around `1.1`-`1.3`; start `effective_io_concurrency` in the high hundreds, then benchmark. | Prefer time-driven checkpoints: raise `max_wal_size` when `checkpoints_req` or checkpoint logs show WAL pressure; use `checkpoint_completion_target` near the documented high end, such as `0.9`, when normal workload is near I/O saturation. | If WAL bandwidth is still a bottleneck and CPU is available, test `wal_compression = on`; it reduces full-page-write WAL volume at CPU cost [[raw/postgres-12/doc/src/sgml/config.sgml#guc-wal-compression|config.sgml#wal_compression]]. |
| Premium SSD v2 | Strong default for production data and WAL when Ultra is unnecessary or too costly. | Keep `seq_page_cost = 1.0`; start `random_page_cost` around `1.1`-`1.5`; start `effective_io_concurrency` in the low to mid hundreds. | Same checkpoint goal as Ultra, but leave more margin before pushing foreground write concurrency. Monitor `checkpoint_sync_time`, `buffers_backend_fsync`, and actual WAL distance. | Good fit for per-tablespace separation of hot data from colder objects; set tablespace cost overrides when only part of the database lives here. |
| Premium SSD | Production data and WAL for mission-critical but less extreme throughput needs. | Start `random_page_cost` around `1.5`-`2.0`; start `effective_io_concurrency` around `50`-`200`, depending on measured concurrency and VM limits. | Raise `max_wal_size` if WAL-caused checkpoints are common; keep `checkpoint_completion_target` above default when checkpoint write bursts are visible. | Bursting behavior is not modeled in PG 12; use PG counters plus cloud metrics to avoid tuning for a short burst window as if it were sustained capacity. |
| Standard SSD | Light production, dev/test, read-mostly data, or colder tablespaces. Avoid making it the main WAL/temp-spill tier for a busy OLTP system. | Start `random_page_cost` around `2.0`-`3.0`; start `effective_io_concurrency` around `10`-`50`; validate with representative plans. | Be conservative with background write pressure. If checkpoint sync stalls appear, first increase checkpoint smoothing and WAL headroom rather than making foreground writes more aggressive. | Watch `pg_stat_database.temp_bytes` and `log_temp_files`; frequent temp spills are a sign to move temp space to faster storage or increase query memory carefully. |
| Standard HDD | Backups, archives, cold sequential data, and tablespaces where low random I/O is acceptable. Avoid active OLTP WAL and high-spill temp workloads. | Keep the default `random_page_cost = 4.0`, or raise it if random reads are materially worse than the default cached-read assumption; keep `effective_io_concurrency` low, usually near `1`. | Use longer, smoother checkpoint intervals only if `pg_wal` space and recovery time allow it. Do not use checkpoint frequency as a substitute for a faster disk when foreground latency matters. | Suitable for cold tablespaces with higher per-tablespace `random_page_cost`; not suitable for latency-critical commit paths. |

### Setting groups

#### Memory and temp spill control

`shared_buffers` is a restart-required `PGC_POSTMASTER` setting in the PG 12 GUC table, and the docs recommend about 25% of RAM as a starting point on a dedicated server with at least 1 GB RAM, while saying more than 40% is unlikely to work better because PostgreSQL also relies on the OS cache [[raw/postgres-12/src/backend/utils/misc/guc.c#shared_buffers|guc.c#shared_buffers]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-shared-buffers|config.sgml#shared_buffers]]. Larger `shared_buffers` usually requires a larger `max_wal_size` so dirty writes can be spread over a longer period [[raw/postgres-12/doc/src/sgml/config.sgml#guc-shared-buffers|config.sgml#shared_buffers]].

`effective_cache_size` is a planner estimate, not an allocation. Raising it makes index scans more likely; lowering it makes sequential scans more likely. It should include shared buffers plus the OS cache expected to be available for PostgreSQL data, adjusted for concurrent queries [[raw/postgres-12/doc/src/sgml/config.sgml#guc-effective-cache-size|config.sgml#effective_cache_size]], [[raw/postgres-12/src/backend/optimizer/path/costsize.c#index_pages_fetched|costsize.c#index_pages_fetched]].

Use `work_mem` to reduce temp files, but remember it applies per sort/hash operation and can be multiplied by complex queries and concurrent sessions [[raw/postgres-12/doc/src/sgml/config.sgml#guc-work-mem|config.sgml#work_mem]]. Use `maintenance_work_mem` for `VACUUM`, `CREATE INDEX`, and dump restore work; it can be larger than `work_mem`, but autovacuum workers can each allocate it unless `autovacuum_work_mem` is set separately [[raw/postgres-12/doc/src/sgml/config.sgml#guc-maintenance-work-mem|config.sgml#maintenance_work_mem]]. Use `temp_tablespaces` to put sort/hash spill files on faster disks or spread them across multiple temp tablespaces [[raw/postgres-12/doc/src/sgml/config.sgml#guc-temp-tablespaces|config.sgml#temp_tablespaces]].

#### Planner storage costs

Leave `seq_page_cost = 1.0` unless you are deliberately rescaling all cost constants. Lower `random_page_cost` relative to `seq_page_cost` on SSD classes where random reads are close to sequential reads; raise it when the default 90% cached-random-read assumption is too optimistic [[raw/postgres-12/doc/src/sgml/config.sgml#guc-random-page-cost|config.sgml#random_page_cost]]. Setting `random_page_cost` lower than `seq_page_cost` is allowed but not physically sensible; setting them equal makes sense only when the database is entirely cached in RAM [[raw/postgres-12/doc/src/sgml/config.sgml#guc-random-page-cost|config.sgml#random_page_cost]].

Raise `effective_io_concurrency` on SSD-backed tablespaces so bitmap heap scans and related prefetch paths can keep more I/O in flight. PG 12 documents that this currently affects bitmap heap scans and is backed by `posix_fadvise` where available; the executor computes the bitmap heap scan prefetch maximum from the relation's tablespace setting when present [[raw/postgres-12/doc/src/sgml/config.sgml#guc-effective-io-concurrency|config.sgml#effective_io_concurrency]], [[raw/postgres-12/src/backend/executor/nodeBitmapHeapscan.c#ExecInitBitmapHeapScan|nodeBitmapHeapscan.c#ExecInitBitmapHeapScan]], [[raw/postgres-12/src/include/pg_config_manual.h#USE_PREFETCH|pg_config_manual.h#USE_PREFETCH]].

#### Checkpoints, WAL, and writeback

Use `log_checkpoints = on` during tuning windows. It is reloadable (`PGC_SIGHUP`) and logs checkpoint/restartpoint statistics, including buffers written and write/sync timings [[raw/postgres-12/src/backend/utils/misc/guc.c#log_checkpoints|guc.c#log_checkpoints]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-log-checkpoints|config.sgml#log_checkpoints]], [[raw/postgres-12/src/backend/access/transam/xlog.c#LogCheckpointEnd|xlog.c#LogCheckpointEnd]].

For Ultra, Premium SSD v2, and Premium SSD, the usual PG-side target is to avoid WAL-pressure checkpoints: if `checkpoints_req` rises or checkpoint logs show `checkpoint starting: wal`, raise `max_wal_size` before changing lower-level writeback knobs. `max_wal_size` is a soft checkpoint trigger, not a hard `pg_wal` cap; WAL can exceed it under heavy load, archiver failure, or retention settings [[raw/postgres-12/doc/src/sgml/config.sgml#guc-max-wal-size|config.sgml#max_wal_size]], [[raw/postgres-12/doc/src/sgml/wal.sgml#wal-configuration|wal.sgml#wal-configuration]].

Set `checkpoint_completion_target` high enough to smooth writes, but below `1.0`; PG 12 docs say `0.9` may be an upper practical value because checkpoints include work besides dirty-buffer writes [[raw/postgres-12/doc/src/sgml/wal.sgml#wal-configuration|wal.sgml#wal-configuration]], [[raw/postgres-12/src/backend/utils/misc/guc.c#checkpoint_completion_target|guc.c#checkpoint_completion_target]]. On Linux, leave `checkpoint_flush_after` at the default `256kB` initially; it tries to push checkpoint writes from the OS page cache to storage before the final fsync, but it can hurt workloads larger than `shared_buffers` and smaller than OS cache, and may have no effect on some platforms [[raw/postgres-12/doc/src/sgml/config.sgml#guc-checkpoint-flush-after|config.sgml#checkpoint_flush_after]], [[raw/postgres-12/src/include/pg_config_manual.h#DEFAULT_CHECKPOINT_FLUSH_AFTER|pg_config_manual.h#DEFAULT_CHECKPOINT_FLUSH_AFTER]], [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BufferSync|bufmgr.c#BufferSync]].

Leave `wal_buffers = -1` unless measurements show WAL insertion pressure during many concurrent commits; PG 12's default selects about 3% of `shared_buffers`, bounded by 64kB and one WAL segment, and the docs say auto-tuning should be reasonable in most cases [[raw/postgres-12/doc/src/sgml/config.sgml#guc-wal-buffers|config.sgml#wal_buffers]], [[raw/postgres-12/src/backend/utils/misc/guc.c#wal_buffers|guc.c#wal_buffers]]. `wal_writer_delay` and `wal_writer_flush_after` control the WAL writer's time- and volume-based flush decisions; lowering them can reduce asynchronous-commit risk windows but increases flush pressure [[raw/postgres-12/doc/src/sgml/config.sgml#guc-wal-writer-delay|config.sgml#wal_writer_delay]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-wal-writer-flush-after|config.sgml#wal_writer_flush_after]], [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogBackgroundFlush|xlog.c#XLogBackgroundFlush]].

Use bgwriter tuning only after checkpoint/WAL pressure is understood. Higher `bgwriter_lru_maxpages`, higher `bgwriter_lru_multiplier`, or shorter `bgwriter_delay` can reduce backend writes when storage has headroom; on Standard SSD or HDD, increasing them too far can move pressure earlier rather than remove it. The source-visible bgwriter loop estimates upcoming buffer allocation from `bgwriter_lru_multiplier`, stops at `bgwriter_lru_maxpages`, and exposes `buffers_clean`, `buffers_backend`, `maxwritten_clean`, and `buffers_backend_fsync` in `pg_stat_bgwriter` [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BgBufferSync|bufmgr.c#BgBufferSync]], [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_bgwriter|system_views.sql#pg_stat_bgwriter]], [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg-stat-bgwriter-view|monitoring.sgml#pg_stat_bgwriter]].

#### Commit durability and WAL volume

Keep `synchronous_commit = on` for durable OLTP. If a specific class of transactions can tolerate losing recently acknowledged commits, `synchronous_commit = off` can be set per transaction or session and avoids the data-corruption risk of `fsync = off`; the risk window is bounded by up to three times `wal_writer_delay` [[raw/postgres-12/doc/src/sgml/config.sgml#guc-synchronous-commit|config.sgml#synchronous_commit]], [[raw/postgres-12/doc/src/sgml/wal.sgml#wal-async-commit|wal.sgml#wal-async-commit]], [[raw/postgres-12/src/backend/utils/misc/guc.c#synchronous_commit|guc.c#synchronous_commit]].

Test `wal_compression = on` when full-page-write WAL volume is expensive relative to CPU. It compresses full-page images written to WAL when `full_page_writes` is on or during base backup, reducing WAL volume without increasing corruption risk, at CPU cost during WAL logging and replay [[raw/postgres-12/doc/src/sgml/config.sgml#guc-wal-compression|config.sgml#wal_compression]], [[raw/postgres-12/src/backend/utils/misc/guc.c#wal_compression|guc.c#wal_compression]].

### Scope and rollout

Use `pg_settings.context` to decide rollout mechanics. PG 12 documents: `postmaster` requires restart; `sighup` requires config reload; `superuser` and `user` can be changed in a session with the required privilege and can also be set as defaults [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#pg_settings_context]], [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]].

| Setting family | Important GUCs | PG 12 scope |
|---|---|---|
| Restart-required memory/WAL sizing | `shared_buffers`, `wal_buffers` | `PGC_POSTMASTER`; restart required [[raw/postgres-12/src/backend/utils/misc/guc.c#shared_buffers|guc.c#shared_buffers]], [[raw/postgres-12/src/backend/utils/misc/guc.c#wal_buffers|guc.c#wal_buffers]]. |
| Checkpoint and background write pacing | `max_wal_size`, `min_wal_size`, `checkpoint_timeout`, `checkpoint_completion_target`, `checkpoint_flush_after`, `bgwriter_delay`, `bgwriter_lru_maxpages`, `bgwriter_lru_multiplier`, `bgwriter_flush_after`, `wal_writer_delay`, `wal_writer_flush_after`, `log_checkpoints` | `PGC_SIGHUP`; reload with `pg_reload_conf()`, `pg_ctl reload`, or SIGHUP; no restart required [[raw/postgres-12/src/backend/utils/misc/guc.c#max_wal_size|guc.c#max_wal_size]], [[raw/postgres-12/src/backend/utils/misc/guc.c#bgwriter_delay|guc.c#bgwriter_delay]], [[raw/postgres-12/src/backend/utils/misc/guc.c#wal_writer_delay|guc.c#wal_writer_delay]], [[raw/postgres-12/doc/src/sgml/ref/alter_system.sgml#sql-altersystem|alter_system.sgml#sql-altersystem]]. |
| Planner and session memory | `seq_page_cost`, `random_page_cost`, `effective_cache_size`, `effective_io_concurrency`, `work_mem`, `maintenance_work_mem`, `temp_tablespaces`, `backend_flush_after`, `synchronous_commit` | `PGC_USERSET`; session-level `SET` is allowed, and config-file defaults affect sessions without local overrides [[raw/postgres-12/src/backend/utils/misc/guc.c#seq_page_cost|guc.c#seq_page_cost]], [[raw/postgres-12/src/backend/utils/misc/guc.c#effective_io_concurrency|guc.c#effective_io_concurrency]], [[raw/postgres-12/src/backend/utils/misc/guc.c#work_mem|guc.c#work_mem]], [[raw/postgres-12/src/backend/utils/misc/guc.c#temp_tablespaces|guc.c#temp_tablespaces]]. |
| Superuser-only session/default controls | `track_io_timing`, `wal_compression`, `log_temp_files`, `temp_file_limit` | `PGC_SUSET`; superuser can use `SET`, or set config defaults and reload as needed [[raw/postgres-12/src/backend/utils/misc/guc.c#track_io_timing|guc.c#track_io_timing]], [[raw/postgres-12/src/backend/utils/misc/guc.c#wal_compression|guc.c#wal_compression]], [[raw/postgres-12/src/backend/utils/misc/guc.c#log_temp_files|guc.c#log_temp_files]], [[raw/postgres-12/src/backend/utils/misc/guc.c#temp_file_limit|guc.c#temp_file_limit]]. |
| Durability safety | `fsync`, `full_page_writes`, `wal_sync_method` | `PGC_SIGHUP`, but the recommendation is to keep `fsync` and `full_page_writes` enabled in production; changing `wal_sync_method` requires reload and platform testing [[raw/postgres-12/src/backend/utils/misc/guc.c#fsync|guc.c#fsync]], [[raw/postgres-12/src/backend/utils/misc/guc.c#full_page_writes|guc.c#full_page_writes]], [[raw/postgres-12/src/backend/utils/misc/guc.c#wal_sync_method|guc.c#wal_sync_method]], [[raw/postgres-12/doc/src/sgml/ref/pgtestfsync.sgml#pgtestfsync|pgtestfsync.sgml#pgtestfsync]]. |

### Production-safe inventory queries

The following snippets are read-only. The `SET` timeouts are session-scoped because `statement_timeout` and `lock_timeout` are `PGC_USERSET`; choose values appropriate for the observation window and workload [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout|guc.c#statement_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout|guc.c#lock_timeout]].

```sql
SET /* wiki_azure_settings_statement_timeout */ statement_timeout = '30s';
SET /* wiki_azure_settings_lock_timeout */ lock_timeout = '5s';

SELECT /* wiki_azure_storage_settings */
       CASE
         WHEN name IN ('seq_page_cost', 'random_page_cost', 'effective_cache_size',
                       'effective_io_concurrency') THEN 'planner_storage_cost'
         WHEN name IN ('shared_buffers', 'work_mem', 'maintenance_work_mem',
                       'temp_tablespaces', 'temp_file_limit') THEN 'memory_and_temp'
         WHEN name IN ('max_wal_size', 'min_wal_size', 'checkpoint_timeout',
                       'checkpoint_completion_target', 'checkpoint_flush_after',
                       'checkpoint_warning', 'log_checkpoints') THEN 'checkpoint'
         WHEN name IN ('bgwriter_delay', 'bgwriter_lru_maxpages',
                       'bgwriter_lru_multiplier', 'bgwriter_flush_after',
                       'backend_flush_after') THEN 'writeback'
         WHEN name IN ('wal_buffers', 'wal_writer_delay', 'wal_writer_flush_after',
                       'wal_compression', 'fsync', 'full_page_writes',
                       'synchronous_commit', 'wal_sync_method') THEN 'wal_durability'
         WHEN name IN ('track_io_timing', 'log_temp_files') THEN 'observability'
       END AS setting_group,
       name,
       setting,
       unit,
       context,
       source,
       pending_restart,
       boot_val,
       reset_val,
       min_val,
       max_val,
       short_desc
  FROM pg_settings
 WHERE name IN (
       'seq_page_cost', 'random_page_cost', 'effective_cache_size',
       'effective_io_concurrency',
       'shared_buffers', 'work_mem', 'maintenance_work_mem',
       'temp_tablespaces', 'temp_file_limit',
       'max_wal_size', 'min_wal_size', 'checkpoint_timeout',
       'checkpoint_completion_target', 'checkpoint_flush_after',
       'checkpoint_warning', 'log_checkpoints',
       'bgwriter_delay', 'bgwriter_lru_maxpages',
       'bgwriter_lru_multiplier', 'bgwriter_flush_after',
       'backend_flush_after',
       'wal_buffers', 'wal_writer_delay', 'wal_writer_flush_after',
       'wal_compression', 'fsync', 'full_page_writes',
       'synchronous_commit', 'wal_sync_method',
       'track_io_timing', 'log_temp_files'
 )
 ORDER BY setting_group, name;
```

`pg_settings` is defined from `pg_show_all_settings()`, and the columns used above are documented in the PG 12 catalog docs [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_settings|system_views.sql#pg_settings]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#pg_settings]].

```sql
SET /* wiki_azure_io_statement_timeout */ statement_timeout = '30s';
SET /* wiki_azure_io_lock_timeout */ lock_timeout = '5s';

SELECT /* wiki_azure_storage_io_snapshot */
       now() AS sampled_at,
       d.datname,
       d.blks_read,
       d.blks_hit,
       d.blk_read_time,
       d.blk_write_time,
       d.temp_files,
       d.temp_bytes,
       b.checkpoints_timed,
       b.checkpoints_req,
       b.checkpoint_write_time,
       b.checkpoint_sync_time,
       b.buffers_checkpoint,
       b.buffers_clean,
       b.maxwritten_clean,
       b.buffers_backend,
       b.buffers_backend_fsync,
       b.buffers_alloc
  FROM pg_stat_database AS d
 CROSS JOIN pg_stat_bgwriter AS b
 WHERE d.datname = current_database();
```

`pg_stat_database` exposes read/write timing and temp-file counters, and `pg_stat_bgwriter` exposes checkpoint and background-write counters. `blk_read_time` and `blk_write_time` depend on `track_io_timing` being enabled [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_database|system_views.sql#pg_stat_database]], [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg-stat-database-view|monitoring.sgml#pg_stat_database]], [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_bgwriter|system_views.sql#pg_stat_bgwriter]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-track-io-timing|config.sgml#track_io_timing]].

## Context Reviewed

- Navigation and bookkeeping: `wiki/versions.md`, `wiki/index.md`, `scripts/recent_log --limit 20`, and `wiki/v12/index.md`.
- Context pack: `.wiki-runtime/context/postgres-12/manifest.md` confirmed source path `raw/postgres-12`, source HEAD `45b88269a353ad93744772791feb6d01bc7e1e42`, generated compile database, include dependencies, tree context, and no failed artifacts.
- Context artifacts used: `.wiki-runtime/context/postgres-12/tree-L4.txt`, `.wiki-runtime/context/postgres-12/include-deps.txt`, `.wiki-runtime/context/postgres-12/compile_commands.json`, direct include queries for `src/backend/utils/misc/guc.c`, `src/backend/optimizer/path/costsize.c`, and `src/backend/storage/buffer/bufmgr.c`, bounded transitive include query for `costsize.c`, reverse include users for `optimizer/cost.h`, and compile-unit queries for `guc.c`, `costsize.c`, `nodeBitmapHeapscan.c`, `bufmgr.c`, and `xlog.c`.
- Source search envelope: targeted `scripts/source_lookup --version 12` searches and slices for `shared_buffers`, `work_mem`, `maintenance_work_mem`, `temp_tablespaces`, `temp_file_limit`, `seq_page_cost`, `random_page_cost`, `effective_cache_size`, `effective_io_concurrency`, `backend_flush_after`, `checkpoint_*`, `max_wal_size`, `min_wal_size`, `bgwriter_*`, `wal_buffers`, `wal_writer_*`, `wal_compression`, `fsync`, `full_page_writes`, `synchronous_commit`, `wal_sync_method`, `log_checkpoints`, `track_io_timing`, `log_temp_files`, `pg_settings`, `pg_stat_database`, `pg_stat_bgwriter`, `ComputeIoConcurrency`, `BitmapPrefetch`, `BufferSync`, `BgBufferSync`, `XLogBackgroundFlush`, and `LogCheckpointEnd`.
- Tests and examples checked: regression view definitions for `pg_stat_database` and `pg_stat_bgwriter` in `src/test/regress/expected/rules.out`; tablespace option tests in `src/test/regress/input/tablespace.source` and `output/tablespace.source`; isolation/regression uses of `seq_page_cost`, `random_page_cost`, and `effective_io_concurrency`; recovery tests that set checkpoint parameters. The v12 tree has tests that exercise settings and view shapes, but no test encoding Azure-specific tuning.
- SQL snippets checked against PG 12 view definitions for `pg_settings`, `pg_stat_database`, and `pg_stat_bgwriter`, and against documented `pg_settings` columns. Every production-bound SQL statement includes an inline trace tag and session timeouts.

## Evidence Map

- Prompt-provided Azure disk classes are used only as input workload/storage categories; PostgreSQL behavior claims come from `raw/postgres-12/`.
- Planner storage behavior: `seq_page_cost`, `random_page_cost`, and `effective_cache_size` docs in [[raw/postgres-12/doc/src/sgml/config.sgml#runtime-config-query-constants|config.sgml#runtime-config-query-constants]]; defaults in [[raw/postgres-12/src/include/optimizer/cost.h#DEFAULT_RANDOM_PAGE_COST|cost.h#DEFAULT_RANDOM_PAGE_COST]]; path costing in [[raw/postgres-12/src/backend/optimizer/path/costsize.c#cost_index|costsize.c#cost_index]]; per-tablespace overrides in [[raw/postgres-12/src/backend/utils/cache/spccache.c#get_tablespace_page_costs|spccache.c#get_tablespace_page_costs]] and [[raw/postgres-12/doc/src/sgml/ref/alter_tablespace.sgml#sql-altertablespace|alter_tablespace.sgml#sql-altertablespace]].
- Async prefetch behavior: `effective_io_concurrency` GUC definition in [[raw/postgres-12/src/backend/utils/misc/guc.c#effective_io_concurrency|guc.c#effective_io_concurrency]], docs in [[raw/postgres-12/doc/src/sgml/config.sgml#guc-effective-io-concurrency|config.sgml#effective_io_concurrency]], compile/platform gates in [[raw/postgres-12/src/include/pg_config_manual.h#USE_PREFETCH|pg_config_manual.h#USE_PREFETCH]], bitmap heap scan use in [[raw/postgres-12/src/backend/executor/nodeBitmapHeapscan.c#BitmapPrefetch|nodeBitmapHeapscan.c#BitmapPrefetch]], and IO-concurrency translation in [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ComputeIoConcurrency|bufmgr.c#ComputeIoConcurrency]].
- Checkpoint/WAL behavior: GUC definitions in [[raw/postgres-12/src/backend/utils/misc/guc.c#max_wal_size|guc.c#max_wal_size]], WAL docs in [[raw/postgres-12/doc/src/sgml/wal.sgml#wal-configuration|wal.sgml#wal-configuration]], checkpoint logging in [[raw/postgres-12/src/backend/access/transam/xlog.c#LogCheckpointEnd|xlog.c#LogCheckpointEnd]], checkpoint writeback in [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BufferSync|bufmgr.c#BufferSync]], and WAL writer flush rules in [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogBackgroundFlush|xlog.c#XLogBackgroundFlush]].
- Durability and WAL-volume choices: `fsync`, `full_page_writes`, `synchronous_commit`, `wal_compression`, and `wal_sync_method` docs in [[raw/postgres-12/doc/src/sgml/config.sgml#runtime-config-wal-settings|config.sgml#runtime-config-wal-settings]]; corresponding GUC definitions in [[raw/postgres-12/src/backend/utils/misc/guc.c#fsync|guc.c#fsync]]; async commit discussion in [[raw/postgres-12/doc/src/sgml/wal.sgml#wal-async-commit|wal.sgml#wal-async-commit]].
- Placement and temp-spill behavior: `initdb --waldir` in [[raw/postgres-12/doc/src/sgml/ref/initdb.sgml#L340-L347|initdb.sgml#L340-L347]], tablespace placement in [[raw/postgres-12/doc/src/sgml/manage-ag.sgml#manage-ag-tablespaces|manage-ag.sgml#manage-ag-tablespaces]], `CREATE TABLESPACE` / `ALTER TABLESPACE` docs in [[raw/postgres-12/doc/src/sgml/ref/create_tablespace.sgml#sql-createtablespace|create_tablespace.sgml#sql-createtablespace]] and [[raw/postgres-12/doc/src/sgml/ref/alter_tablespace.sgml#sql-altertablespace|alter_tablespace.sgml#sql-altertablespace]], and `temp_tablespaces` docs in [[raw/postgres-12/doc/src/sgml/config.sgml#guc-temp-tablespaces|config.sgml#temp_tablespaces]].
- Observability: `pg_settings` view in [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_settings|system_views.sql#pg_settings]] and docs in [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#pg_settings]]; `pg_stat_database` and `pg_stat_bgwriter` view definitions in [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_database|system_views.sql#pg_stat_database]] / [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_bgwriter|system_views.sql#pg_stat_bgwriter]]; monitoring docs in [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg-stat-database-view|monitoring.sgml#pg_stat_database]] and [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg-stat-bgwriter-view|monitoring.sgml#pg_stat_bgwriter]].

## Open Questions

- The Azure disk limits and feature notes in the question were provided by the prompt and were not verified against Azure documentation. Azure VM-level IOPS/throughput caps, host caching mode, disk striping, bursting rules, filesystem/mount choices, and regional SKU availability are outside the pinned PostgreSQL 12 source.
- PostgreSQL 12 source does not define numeric `random_page_cost` or `effective_io_concurrency` values for Azure disk classes. The table's numeric ranges are starting probes derived from source-documented directionality and must be validated with representative plans and latency measurements.
- `effective_io_concurrency` depends on an effective prefetch implementation. PG 12 documents that some platforms lack `posix_fadvise`, and some platforms may expose it without useful behavior [[raw/postgres-12/doc/src/sgml/config.sgml#guc-effective-io-concurrency|config.sgml#effective_io_concurrency]].
- `checkpoint_flush_after`, `bgwriter_flush_after`, and `backend_flush_after` are writeback hints. PG 12 documents both possible latency benefit and possible regression for workloads larger than `shared_buffers` but smaller than OS cache, and states the settings may have no effect on some platforms [[raw/postgres-12/doc/src/sgml/config.sgml#guc-checkpoint-flush-after|config.sgml#checkpoint_flush_after]], [[raw/postgres-12/doc/src/sgml/config.sgml#guc-backend-flush-after|config.sgml#backend_flush_after]].

## Source References

- Source pin and context pack: `raw/postgres-12/`, `.wiki-runtime/context/postgres-12/manifest.md`
- GUC definitions and context: [[raw/postgres-12/src/backend/utils/misc/guc.c#fsync|guc.c#fsync]], [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml#view-pg-settings|catalogs.sgml#view-pg-settings]]
- Planner costing and tablespaces: [[raw/postgres-12/doc/src/sgml/config.sgml#runtime-config-query-constants|config.sgml#runtime-config-query-constants]], [[raw/postgres-12/src/backend/optimizer/path/costsize.c#cost_index|costsize.c#cost_index]], [[raw/postgres-12/src/backend/utils/cache/spccache.c#get_tablespace_page_costs|spccache.c#get_tablespace_page_costs]], [[raw/postgres-12/doc/src/sgml/ref/alter_tablespace.sgml#sql-altertablespace|alter_tablespace.sgml#sql-altertablespace]]
- I/O prefetch and writeback: [[raw/postgres-12/src/backend/executor/nodeBitmapHeapscan.c#BitmapPrefetch|nodeBitmapHeapscan.c#BitmapPrefetch]], [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BufferSync|bufmgr.c#BufferSync]], [[raw/postgres-12/src/include/pg_config_manual.h#USE_PREFETCH|pg_config_manual.h#USE_PREFETCH]]
- WAL and checkpoints: [[raw/postgres-12/doc/src/sgml/wal.sgml#wal-configuration|wal.sgml#wal-configuration]], [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogBackgroundFlush|xlog.c#XLogBackgroundFlush]], [[raw/postgres-12/doc/src/sgml/ref/pgtestfsync.sgml#pgtestfsync|pgtestfsync.sgml#pgtestfsync]]
- Monitoring and SQL support: [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_stat_database|system_views.sql#pg_stat_database]], [[raw/postgres-12/doc/src/sgml/monitoring.sgml#pg-stat-database-view|monitoring.sgml#pg_stat_database]], [[raw/postgres-12/src/backend/parser/gram.y#VariableSetStmt|gram.y#VariableSetStmt]]
