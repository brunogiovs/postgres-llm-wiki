---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
---

# Detecting Slow Random Disk I/O Using Database Metrics in PostgreSQL 12

## Question

in PostgreSQL 12, how to find evidence and detect a slow random i/o disk using database metrics?

## Short Answer

PostgreSQL 12 exposes disk I/O metrics via `pg_stat_database`, `pg_stat_statements` (contrib), and `pg_stat_activity`. Key indicators:

- **High read latency**: `track_io_timing = on`; `blk_read_time / blks_read > 5-10ms` in `pg_stat_database` or per-query in `pg_stat_statements`.
- **Disk pressure**: Cache hit ratio `blks_hit / (blks_hit + blks_read) < 0.99`.
- **Random access heavy**: High `idx_scan`/`idx_tup_fetch` vs `seq_scan`/`seq_tup_read` in `pg_stat_user_tables`.
- **Wait events**: High count of backends with `wait_event_type = 'IO'` and `wait_event = 'DataFileRead'` in `pg_stat_activity`.

Slow random I/O shows as elevated `blk_read_time` despite low `blks_read` (warm cache), esp. for scattered index/catalog reads.

```
SELECT datname, 
       blks_read, blks_hit,
       round(100.0 * blks_hit / nullif(blks_hit + blks_read, 0), 2) AS hit_ratio,
       blk_read_time, blk_write_time,
       round(blk_read_time / nullif(blks_read, 0), 2) AS avg_read_ms
FROM pg_stat_database
WHERE blks_read > 0
ORDER BY avg_read_ms DESC;
```

## Detailed Answer

### 1. Enable I/O Timing

`track_io_timing` (`boolean` GUC, default `off`, SIGHUP reloadable; `raw/postgres-12/src/backend/utils/misc/guc.c`): enables per-operation timing of kernel I/O calls (`pg_pread`/`pg_pwrite`/`pg_fsync`; `src/port/pg_pread.c` added PG12 for positioned I/O). Accumulates **wall-clock time** (not just kernel) in `BufferUsage.blk_read_time`/`blk_write_time` for **shared buffers** (`bufmgr.c:ExtendBufHeader` etc.), **local/temp buffers** (`localbuf.c:buffer_read`, `buffile.c:FileRead`), WAL (`xlog.c`).

**Overhead**: ~3-10% CPU (function call + instr_time.h overhead).

**Scope**: All block-level reads/writes/fsyncs; excludes seq scans prefetch.

```
SET track_io_timing = on;
```
Tracks `blk_read_time`/`blk_write_time` in buffer manager (`raw/postgres-12/src/backend/storage/buffer/bufmgr.c` increments `pgBufferUsage.blks_read`, `blk_read_time`), exposed via `pg_stat_database`/`pg_stat_statements`.

### 2. Database-Wide Metrics (`pg_stat_database`)
- `blks_read`: Physical disk blocks read (`pg_stat_get_db_blks_read` in `raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c`).
- `blks_hit`: Cache hits.
- `blk_read_time`: Time spent reading (ms).

**Detection**:
- Low hit ratio → disk pressure.
- High `blk_read_time / blks_read` → slow disk (HDD random ~10-20ms, SSD ~0.1ms).
- Compare databases/hosts.

### 3. Per-Query Metrics (`pg_stat_statements`)
Load contrib/pg_stat_statements.
- `blk_read_time`, `shared_blks_read`, `local_blks_read`, `temp_blks_read` (`raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c`).

**Detection**:
```
SELECT query, shared_blks_read, blk_read_time,
       round(blk_read_time / nullif(shared_blks_read, 0), 3) AS avg_read_ms
FROM pg_stat_statements
WHERE shared_blks_read > 0
ORDER BY avg_read_ms DESC;
```
Pinpoint queries with slow reads (index scans, scattered).

### 4. Access Pattern Inference (`pg_stat_user_tables`)
- `seq_scan`/`seq_tup_read`: Sequential (prefetch-friendly).
- `idx_scan`/`idx_tup_fetch`: Random I/O likely.

High idx_scan + high read latency → slow random disk.

### 5. Live Wait Events (`pg_stat_activity`)
```
SELECT wait_event_type, wait_event, count(*)
FROM pg_stat_activity
WHERE wait_event IS NOT NULL
GROUP BY 1,2
ORDER BY count(*) DESC;
```
`IO:DataFileRead` (`raw/postgres-12/src/backend/postmaster/pgstat.c`) indicates blocking reads, often random.

### Inference for "Random" I/O
No direct seq/random stat (unlike some DBs). Infer:
- Catalog/index heavy → random.
- Correlate with `EXPLAIN (BUFFERS)`: high shared read blocks.
- `random_page_cost` tuning assumes random slower.

## Mitigations Summary

| Symptom | Mitigation |
|---------|------------|
| High `blk_read_time / blks_read` | Use SSD; tune `track_io_timing=on` for monitoring only. |
| Low cache hit ratio | Increase `shared_buffers` (25% RAM), `effective_cache_size`. |
| Frequent dirty victim flushes (`FlushBuffer`) | Tune bgwriter: `bgwriter_lru_maxpages=1000`, `bgwriter_delay=200ms`; checkpoints: `checkpoint_completion_target=0.9` (spread writes), shorter `checkpoint_timeout=5min` (more frequent small CPs reduce bursty dirty buffers, less eviction flushes in `bufmgr.c:StrategyGetBuffer` → `FlushBuffer`). |
| Planning/catalog random reads | `plan_cache_mode=force_generic_plan` reduces replans ([[v12/questions/plan-cache-mode-production-impact]]). |
| Index scan heavy | Tune indexes, `random_page_cost=1.1-2` (SSD), `seq_page_cost=1`. |
| Temp blks_read | Increase `work_mem`. |

See `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:FlushBuffer` (dirty eviction), `src/backend/postmaster/bgwriter.c`.

## Cross-Links
- [[v12/questions/query-disk-io-with-warm-cache]] - Why slow random I/O hurts even warm caches.
- [[v12/questions/plan-cache-mode-production-impact]] - Slow disk amplifies planning latency.
- [[v12/index]]

## Source References
- `raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c:pg_stat_get_db_blk_read_time`
- `raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c` (blk_read_time accumulation)
- `raw/postgres-12/src/backend/storage/buffer/bufmgr.c` (pgBufferUsage.blks_read, blk_read_time)
- `raw/postgres-12/src/backend/postmaster/pgstat.c` (WAIT_EVENT_DATA_FILE_READ)
- `raw/postgres-12/src/backend/executor/instrument.c` (BufferUsage)

## Open Questions
- Core aggregate wait stats view? (pg_stat_database lacks waits)
- Direct seq/random block stats?
- Temp blks vs shared for SSD/HDD distinction?