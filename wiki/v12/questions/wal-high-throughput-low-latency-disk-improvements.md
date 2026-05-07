---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# WAL Directory on High Throughput, Low Latency Disk Improvements (unverified)

## Question

In PostgreSQL 12, having the WAL directory (`pg_wal`) on high throughput and extremely low latency disk gives improvement to what activities and operations in the database?

## Short Answer

Placing the WAL directory on high-throughput, low-latency storage primarily improves:

1. **Transaction commit latency** - Synchronous WAL flushes during commits
2. **Checkpoint performance** - WAL segment writing during checkpoints  
3. **Background WAL writing** - Periodic WAL buffer flushing
4. **WAL segment switches** - Fsync operations when segments fill

## Detailed Answer

PostgreSQL's Write-Ahead Logging (WAL) system requires durable storage of transaction records before commits can complete. The `pg_wal` directory contains these critical log files that must be written and synchronized to disk.

### Transaction Commit Latency

When transactions commit, PostgreSQL calls `XLogFlush()` to ensure WAL records are written and synchronized to disk. This is a synchronous operation that blocks the committing transaction:

```c
// From src/backend/access/transam/xact.c:1371
XLogFlush(XactLastRecEnd);
```

The `XLogFlush()` function performs both writing (`XLogWrite()`) and synchronization (`issue_xlog_fsync()`). Low-latency storage reduces the time transactions wait for `fsync()` operations, directly improving commit response times.

### Checkpoint Performance

During checkpoints, PostgreSQL writes a checkpoint record to WAL and ensures all dirty WAL buffers are flushed. The `CreateCheckPoint()` function calls `XLogFlush()` after inserting the checkpoint record:

```c
// From src/backend/access/transam/xlog.c:8819
XLogFlush(recptr);
```

Checkpoints can generate significant WAL I/O as they flush accumulated transaction logs. High-throughput storage allows checkpoints to complete faster, reducing the window where the system is I/O bound.

### Background WAL Writing

The WAL writer process (`WalWriterMain()`) periodically calls `XLogBackgroundFlush()` to write WAL buffers to disk proactively:

```c
// From src/backend/postmaster/walwriter.c:263
if (XLogBackgroundFlush())
    left_till_hibernate = LOOPS_UNTIL_HIBERNATE;
```

This reduces the synchronous work needed during commits. High-throughput storage allows the WAL writer to keep up with write activity more effectively, preventing WAL buffer pressure from impacting foreground operations.

### WAL Segment Switches

When WAL segments fill up, PostgreSQL switches to new segments and immediately fsyncs the completed segment:

```c
// From src/backend/access/transam/xlog.c:2533
issue_xlog_fsync(openLogFile, openLogSegNo);
```

Low-latency storage minimizes the pause during segment switches, which occur every 16MB by default.

## Source References

- Source pin and context pack: [[raw/postgres-12/]], `.wiki-runtime/context/postgres-12/manifest.md`
- Transaction commit flush path: `RecordTransactionCommit()` in [[raw/postgres-12/src/backend/access/transam/xact.c#RecordTransactionCommit|xact.c#RecordTransactionCommit]] and `XLogFlush()` in [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogFlush|xlog.c#XLogFlush]].
- Checkpoint WAL flush path: `CreateCheckPoint()` in [[raw/postgres-12/src/backend/access/transam/xlog.c#CreateCheckPoint|xlog.c#CreateCheckPoint]] and `XLogFlush()` in [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogFlush|xlog.c#XLogFlush]].
- Background WAL writing: `WalWriterMain()` in [[raw/postgres-12/src/backend/postmaster/walwriter.c#WalWriterMain|walwriter.c#WalWriterMain]] and `XLogBackgroundFlush()` in [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogBackgroundFlush|xlog.c#XLogBackgroundFlush]].
- WAL write and sync operations: `XLogWrite()` in [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogWrite|xlog.c#XLogWrite]], segment-completion `issue_xlog_fsync()` calls in [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogWrite|xlog.c#XLogWrite]], and `issue_xlog_fsync()` in [[raw/postgres-12/src/backend/access/transam/xlog.c#issue_xlog_fsync|xlog.c#issue_xlog_fsync]].
- WAL wait-event identifiers: `WAIT_EVENT_WAL_WRITE` and `WAIT_EVENT_WAL_SYNC` in [[raw/postgres-12/src/include/pgstat.h#WAIT_EVENT_WAL_WRITE|pgstat.h#WAIT_EVENT_WAL_WRITE]].

## Performance Impact

The improvements are most significant for:
- **High-frequency OLTP workloads** where commit latency directly affects response times
- **Write-heavy applications** where WAL volume is high
- **Systems with frequent checkpoints** where checkpoint WAL flush and sync work is visible in latency or throughput

## Context Reviewed

- WAL write-ahead logging mechanism and durability requirements
- Synchronous vs asynchronous commit behavior
- WAL writer background process operation
- Checkpoint timing and I/O patterns
- WAL segment size and switching behavior

## Evidence Map

- **Transaction commit path**: `xact.c` → `XLogFlush()` → `XLogWrite()` + `issue_xlog_fsync()`
- **Checkpoint path**: `CreateCheckPoint()` → WAL record insertion → `XLogFlush()`
- **Background writing**: `WalWriterMain()` → `XLogBackgroundFlush()` → `XLogWrite()`
- **Segment switching**: `XLogWrite()` → segment completion → `issue_xlog_fsync()`

## Related Pages

- [[v12/questions/wal-separate-disk-full-replication-slots|WAL on a separate full disk and replication slots]]
- [[v12/questions/checkpoint-monitoring-optimization-scenarios|Checkpoint monitoring and optimization scenarios]]

## Open Questions

- Quantitative performance impact measurements for different storage types
- Interaction with `synchronous_commit` settings
- WAL compression effects on I/O patterns
