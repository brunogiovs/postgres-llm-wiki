---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: claude-opus-4-7 2026-05-03T14:47:00Z
---

## Question

In PostgreSQL 12, what are the key metrics to categorize the usage of the database engine and its current operational status like if it is doing well or not?

## Answer

PostgreSQL 12 provides comprehensive statistics through system views to monitor database usage and operational health. The key metrics fall into several categories:

### Connection and Session Metrics

**Active Connections**: `pg_stat_activity` shows current database connections, their states (active, idle, idle in transaction), and current queries.

- `numbackends` from `pg_stat_database` indicates total connections per database
- Connection states help identify if the database is overloaded or has idle connections

**Wait Events**: `pg_stat_activity.wait_event_type` and `wait_event` show what backends are waiting for (locks, I/O, etc.).

### Database-Level Performance Metrics

**Transaction Activity**: `pg_stat_database` provides:
- `xact_commit` / `xact_rollback` - transaction success rates
- `deadlocks` - deadlock frequency indicating contention issues

**Buffer Cache Efficiency**: `pg_stat_database` shows:
- `blks_hit` / (`blks_hit` + `blks_read`) = cache hit ratio
- High hit ratio (>99%) indicates good performance
- Low ratio suggests insufficient shared_buffers or poor query patterns

**I/O Performance**: When `track_io_timing = on`:
- `blk_read_time` and `blk_write_time` in milliseconds
- High I/O times indicate slow storage or memory pressure

**Temporary File Usage**: `pg_stat_database`:
- `temp_files` and `temp_bytes` indicate work_mem/hash_mem issues
- Frequent temp file creation suggests query optimization opportunities

### Background Writer and Checkpoint Metrics

**Checkpoint Activity**: `pg_stat_bgwriter` shows:
- `checkpoints_timed` vs `checkpoints_req` - scheduled vs forced checkpoints
- High `checkpoints_req` indicates checkpoint tuning issues
- `checkpoint_write_time` and `checkpoint_sync_time` - I/O time spent on checkpoints

**Buffer Management**: `pg_stat_bgwriter`:
- `buffers_clean` - buffers written by bgwriter
- `maxwritten_clean` - times bgwriter hit `bgwriter_lru_maxpages`
- `buffers_backend` - buffers written directly by backends (indicates bgwriter tuning issues)

### Table and Index Usage Metrics

**Table Access Patterns**: `pg_stat_user_tables`:
- `seq_scan` vs `idx_scan` - sequential vs indexed access
- High sequential scans may indicate missing indexes
- `n_tup_ins`/`n_tup_upd`/`n_tup_del` - DML activity levels

**Table Maintenance**: `pg_stat_user_tables`:
- `last_vacuum` / `last_autovacuum` timestamps
- `n_dead_tup` - dead tuple accumulation
- `vacuum_count` / `autovacuum_count` - maintenance frequency

**Index Efficiency**: `pg_stat_user_indexes`:
- `idx_scan` - index usage frequency
- Unused indexes may need removal

### Lock Contention

**Lock Information**: `pg_locks` view shows:
- Current locks held and waited for
- Lock types and modes
- Blocking relationships

### Query Performance (with pg_stat_statements extension)

When enabled, provides per-query metrics:
- `total_time` - total execution time
- `calls` - execution count
- `mean_time` - average execution time
- `rows` - rows returned

### Operational Health Assessment

**Good Health Indicators**:
- High buffer cache hit ratio (>95%)
- Low forced checkpoints
- Reasonable I/O times (<10ms average)
- Few deadlocks
- Regular autovacuum activity
- Low temp file usage

**Warning Signs**:
- High connection counts near `max_connections`
- Many idle in transaction connections
- Low cache hit ratio
- Frequent forced checkpoints
- High I/O wait times
- Accumulating dead tuples
- Excessive temp file creation

**Critical Issues**:
- Deadlocks occurring regularly
- Backends frequently waiting on locks
- Persistent high I/O times
- Out of memory conditions (temp files)
- Checkpoint spikes causing performance degradation

## Source References

- System view definitions: [[raw/postgres-12/src/backend/catalog/system_views.sql]]
- Statistics collection functions: [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c]]
- Background writer statistics: [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#1600-1666]]
- Database-level statistics: [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#1207-1598]]
- Activity monitoring: [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#546-924]]

## Open Questions

- How do these metrics correlate with specific performance issues?
- What are recommended thresholds for each metric?
- How does replication status affect operational assessment?