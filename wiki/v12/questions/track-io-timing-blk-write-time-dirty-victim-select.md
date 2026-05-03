---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
---

# Does blk_write_time capture "dirty victim" time during SELECT in PostgreSQL 12?

## Question

In PostgreSQL 12 with `track_io_timing = on`, during SELECT execution, does `blk_write_time` (e.g. from `pg_stat_statements`) capture the time spent writing "dirty victim" buffers?

## Short Answer

**Yes**, for *synchronous* dirty victim evictions. 

When a SELECT needs a new buffer (`BufferAlloc` / `ReadBuffer` → `StrategyGetBuffer`), if no clean victim is available, the selected dirty victim buffer is synchronously flushed via `FlushBuffer` (`src/backend/storage/buffer/bufmgr.c:~StrategyGetBuffer` → `FlushBuffer`). If `track_io_timing=on`, `FlushBuffer` times the `smgrwrite` wall-clock time, increments `pgBufferUsage.blk_write_time` (`bufmgr.c:2769`), and `pg_stat_statements` captures the global `pgBufferUsage` delta during statement execution (`contrib/pg_stat_statements/pg_stat_statements.c:1051,1292`).

**No** for purely *asynchronous* writes (bgwriter/checkpointer), but any increments to the *global* `pgBufferUsage.blk_write_time` during SELECT execution (including concurrent bgwriter flushes) are included in the SELECT's `blk_write_time`.

## Detailed Answer

### Background: track_io_timing and blk_write_time

- `track_io_timing` (`boolean` GUC, `src/backend/utils/misc/guc.c:1402`): Enables wall-clock timing of block I/O operations (reads/writes via `smgrread`/`smgrwrite`).
- Global `PgBufferUsage pgBufferUsage` (`src/include/executor/instrument.h`) accumulates:
  - `blks_written`: `pgBufferUsage.shared_blks_written++` (`bufmgr.c:2772`).
  - `blk_write_time`: `INSTR_TIME_ADD(pgBufferUsage.blk_write_time, io_time)` after timing `smgrwrite` (`bufmgr.c:2764-2769`).
- `pg_stat_statements` deltas `pgBufferUsage` at statement start/end:
  ```
  bufusage_start = pgBufferUsage;  // pg_stat_statements.c:~1040
  // ... statement exec ...
  bufusage.blk_write_time = pgBufferUsage.blk_write_time;
  INSTR_TIME_SUBTRACT(bufusage.blk_write_time, bufusage_start.blk_write_time);  // :1051-1052
  e->counters.blk_write_time += INSTR_TIME_GET_MILLISEC(bufusage->blk_write_time);  // :1292
  ```
- Result: `pg_stat_statements.blk_write_time` = **total system-wide buffer write time** during statement execution (ms).

### Dirty Victim Eviction During SELECT

- SELECT execution (e.g. `SeqScan` → `heap_getnext` → `ReadBuffer`) allocates buffers via `BufferAlloc` / `ReadBuffer` → `StrategyGetBuffer` (`bufmgr.c`).
- `StrategyGetBuffer`: Scans LRU chain for victim. Prefers clean buffers. If *all* candidates dirty:
  - Selects "victim" buffer.
  - Caller (`BufferAlloc` etc.) checks `if (buf_state & BM_DIRTY)` → `FlushBuffer(victim)` *synchronously*.
- `FlushBuffer` (`bufmgr.c:2700+`):
  1. WAL flush if permanent (`XLogFlush(recptr)` :2735).
  2. `PageSetChecksumCopy` if needed (:2750).
  3. If `track_io_timing`: `INSTR_TIME_SET_CURRENT(io_start)` (:2752).
  4. `smgrwrite(reln, fork, block, bufToWrite)` (:2758).
  5. If `track_io_timing`: compute `io_time`, `pgstat_count_buffer_write_time(INSTR_TIME_GET_MICROSEC(io_time))` (:2768), `INSTR_TIME_ADD(pgBufferUsage.blk_write_time, io_time)` (:2769).
  6. `pgBufferUsage.shared_blks_written++` (:2772).
  7. `TerminateBufferIO(buf, true /*clear_dirty*/, 0 /*set_flag_bits*/)` (:2778).
- Timing includes *wall-clock* `smgrwrite` (kernel `pg_pwrite` + any waits).

### Synchronous vs. Asynchronous

| Eviction Type | During SELECT? | Captured in blk_write_time? | Citation |
|---------------|----------------|-----------------------------|----------|
| Sync dirty victim (no clean buffer) | Yes, blocks SELECT until flush | Yes, direct `FlushBuffer` call | `bufmgr.c:StrategyGetBuffer` → `BufferAlloc` → `FlushBuffer:2769` |
| Async bgwriter (`BgWriterMain`) | Concurrent possible | Yes, if during SELECT exec (global counter) | `src/backend/postmaster/bgwriter.c:FlushOlderBuffers` → `FlushBuffer` |
| Checkpointer | Concurrent possible | Yes, if during SELECT exec | `src/backend/postmaster/checkpointer.c` → `FlushSomeBuffers`? |

- **Pure SELECT writes**: Rare (e.g. hint bits, prune WAL via `heap_page_prune_opt` → `XLOG_HEAP2_PRUNE_ON_ACCESS`).
- **Mitigation**: Tune `bgwriter_lru_maxpages`, `bgwriter_delay`, `checkpoint_completion_target=0.9` to reduce dirty victims ([[v12/questions/detect-slow-random-io-disk-metrics]]).

### Verification Query

```
SELECT query, blk_write_time, shared_blks_written,
       round(blk_write_time / nullif(shared_blks_written, 0), 3) AS avg_write_ms
FROM pg_stat_statements
WHERE blk_write_time > 0 AND query LIKE '%SELECT%'
ORDER BY blk_write_time DESC;
```

High `avg_write_ms` on SELECTs → dirty victim pressure or concurrent writes.

## Cross-Links
- [[v12/questions/detect-slow-random-io-disk-metrics]] - IO metrics overview, cites `bufmgr.c`.
- [[v12/questions/query-disk-io-with-warm-cache]] - Dirty victim in execution paths.
- [[v12/index]]

## Source References
- `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:2764-2770` (`FlushBuffer` timing / `pgBufferUsage`).
- `raw/postgres-12/contrib/pg_stat_statements/pg_stat_statements.c:1051-1052,1292` (delta).
- `raw/postgres-12/src/backend/utils/misc/guc.c:1402` (`track_io_timing`).
- `raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c` (db stats).

## Open Questions
- Exact `StrategyGetBuffer` line nums for PG12 victim selection / flush decision?
- Does `pg_stat_database.blk_write_time` behave identically?
- bgwriter/checkpointer exact `FlushBuffer` paths?