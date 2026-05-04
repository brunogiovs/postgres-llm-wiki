---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# How to mitigate "dirty victim" synchronous writes during SELECT queries in PostgreSQL 12?

## Question

In PostgreSQL 12, SELECT queries can block on synchronous I/O writes when the buffer pool is full of dirty buffers. How can this "dirty victim" issue be mitigated?

## Short Answer

**Tune background writer parameters** to proactively clean more dirty buffers, reducing the likelihood that SELECT queries encounter dirty victims requiring synchronous flushing:

- Increase `bgwriter_lru_maxpages` (default: 100) to write more buffers per background writer cycle
- Adjust `bgwriter_lru_multiplier` (default: 2.0) to be more aggressive in anticipating allocation needs
- Set `checkpoint_completion_target = 0.9` to spread checkpoint I/O over more time
- Consider increasing `shared_buffers` if memory allows

## Detailed Answer

### The Dirty Victim Problem

When a SELECT query needs to read a page not in the buffer pool, `BufferAlloc` selects a victim buffer using the clock-sweep algorithm (`StrategyGetBuffer`). If the selected victim is dirty (`BM_DIRTY` flag set), PostgreSQL must synchronously flush it to disk via `FlushBuffer` before the SELECT can proceed.

```c
// bufmgr.c:1095-1167
if (oldFlags & BM_DIRTY)
{
    // Synchronous flush blocks the SELECT query
    FlushBuffer(buf, NULL);
}
```

This causes read-only SELECT queries to block on write I/O, defeating the purpose of asynchronous background cleaning.

### Background Writer Mechanics

The background writer (`BgBufferSync`) runs every `BgWriterDelay` milliseconds (default 200ms) and attempts to clean dirty buffers proactively. It uses a feedback control loop to estimate how many buffers need cleaning:

1. **Allocation rate tracking**: Monitors `recent_alloc` (buffers allocated since last cycle)
2. **Density estimation**: Tracks ratio of reusable buffers to total buffers scanned
3. **Predictive cleaning**: Writes `upcoming_alloc_est = smoothed_alloc * bgwriter_lru_multiplier` buffers per cycle
4. **Maximum per cycle**: Limited by `bgwriter_lru_maxpages` (default 100)

### Mitigation Strategies

#### 1. Increase bgwriter_lru_maxpages

```sql
-- Allow background writer to write more buffers per cycle
ALTER SYSTEM SET bgwriter_lru_maxpages = 200;
SELECT pg_reload_conf();
```

**Rationale**: Default of 100 may be too conservative for high-throughput workloads. Increasing allows more proactive cleaning.

#### 2. Adjust bgwriter_lru_multiplier

```sql
-- Be more aggressive in anticipating allocation needs
ALTER SYSTEM SET bgwriter_lru_multiplier = 4.0;
SELECT pg_reload_conf();
```

**Rationale**: Multiplier of 2.0 may underestimate peak allocation rates. Higher values provide more buffer headroom.

#### 3. Optimize Checkpoint Spreading

```sql
-- Spread checkpoint I/O over 90% of checkpoint interval
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
SELECT pg_reload_conf();
```

**Rationale**: Reduces sudden bursts of dirty buffers from checkpoints, giving background writer more time to clean gradually.

#### 4. Increase Shared Buffers (if possible)

```sql
-- More buffer cache reduces victim selection pressure
ALTER SYSTEM SET shared_buffers = '2GB';  -- Adjust based on available RAM
SELECT pg_reload_conf();
```

**Rationale**: Larger buffer pool means fewer allocations needed, reducing dirty victim encounters.

#### 5. Monitor Effectiveness

```sql
-- Check if mitigation is working
SELECT
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_tup_hot_upd,
    n_dead_tup,
    vacuum_count,
    autovacuum_count,
    analyze_count,
    autoanalyze_count
FROM pg_stat_user_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY n_tup_upd DESC;

-- Monitor buffer hit ratio
SELECT
    sum(blks_hit) / (sum(blks_hit) + sum(blks_read))::float as hit_ratio
FROM pg_stat_database;

-- Check for synchronous dirty victim flushes in SELECT queries
SELECT query, blk_write_time, shared_blks_written
FROM pg_stat_statements
WHERE blk_write_time > 0 AND query LIKE '%SELECT%'
ORDER BY blk_write_time DESC;
```

### Performance Trade-offs

- **Higher bgwriter_lru_maxpages**: More I/O from background writer, but less blocking during queries
- **Higher bgwriter_lru_multiplier**: More aggressive cleaning, potentially wasting I/O on over-cleaning
- **Lower checkpoint_completion_target**: Slower checkpoints, but smoother I/O patterns

### When to Escalate

If tuning doesn't help:
- Storage I/O is the bottleneck (consider faster disks/RAID)
- Workload has very high update rates (consider partitioning or archiving)
- Memory constraints prevent larger `shared_buffers`

## Cross-Links

- [[v12/questions/track-io-timing-blk-write-time-dirty-victim-select]] - Related question about measuring this issue
- [[v12/questions/query-disk-io-with-warm-cache]] - Disk I/O patterns in SELECT queries
- [[v12/questions/detect-slow-random-io-disk-metrics]] - Detecting slow I/O issues

## Source References

- `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:1095-1167` (`BufferAlloc` dirty victim handling)
- `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:2051-2336` (`BgBufferSync` algorithm)
- `raw/postgres-12/src/backend/storage/buffer/freelist.c:200-358` (`StrategyGetBuffer` victim selection)
- `raw/postgres-12/src/backend/utils/misc/guc.c` (GUC parameter definitions)

## Open Questions

- Optimal bgwriter_lru_maxpages values for different workload patterns?
- Interaction with `effective_io_concurrency` settings?
- Impact of different storage types (SSD vs HDD) on tuning?