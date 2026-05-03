---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
---

# Disk I/O in PostgreSQL 12.2: Pre-Execution, Execution, and Slow Random I/O Impact (Warm Cache)

## Question

In PostgreSQL 12.2, what are all potential disk I/O before a query execution and during execution? How does slow random I/O impact these even if all buffers are in shared_buffers and disk data in FS cache?

## Short Answer

Warm caches avoid data reads. Remaining I/O:

1. Commit WAL fsync: `raw/postgres-12/src/backend/access/transam/xact.c:1371` XLogFlush(XactLastRecEnd).

2. WAL wraparound: `raw/postgres-12/src/backend/access/transam/xlog.c:AdvanceXLInsertBuffer`.

3. Dirty victim flush: `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:2672` FlushBuffer.

4. Relation extension: `raw/postgres-12/src/backend/storage/smgr/md.c:mdextend`.

5. Temp spills: `raw/postgres-12/src/backend/storage/file/buffile.c:BufFileWrite`.

Slow random I/O blocks fsync (durability wait), writeback throttling, SLRU evictions (CLOG), bgwriter contention.

## Pre-Execution I/O (Parse, Analyze, Rewrite, Plan)

Catalog reads (pg_class, pg_attribute, pg_statistic) via BufferAlloc; hit shared_buffers no disk. Dirty victim possible. No WAL.

## Execution I/O

Buffer reads hit. Hint bits dirty pages (no WAL unless wal_log_hints). Temp files for sort/hash. WAL for DML/prune.

## Summary for Planning Phase

| Phase | Disk I/O Risk |
|-------|---------------|
| Raw Parse | None |
| Analyze | Catalog buffers (syscache miss) |
| Rewrite | Rules pg_rewrite |
| Planner | pg_statistic, pg_index |
| Plan Cache Reval | Re-analyze if invalid |
| JIT | Bitcode load (first) |

Slow disk hits catalog victim flushes.

## Summary I/O per Statement Type

| Statement | WAL Emission | Commit Fsync | Extend | Temp Spill | SLRU | Dirty Victim |
|-----------|--------------|--------------|--------|------------|------|--------------|
| SELECT | Prune (rare) | Rare | No | Sort/Hash | CLOG hint | Yes |
| INSERT | Yes | Yes | Yes | No | No | Yes |
| UPDATE | Yes | Yes | Maybe | No | No | Yes |
| DELETE | Yes | Yes | No | No | No | Yes |
| COPY FROM | Heavy | Yes | Heavy | No | No | Yes |
| VACUUM | Yes | Yes | No | No | Yes | Heavy |
| ANALYZE | Catalog | Yes | No | Sample | No | Low |

Slow disk worst for COPY/VACUUM (sustained), DML (fsync), SELECT (victim).

## Cross-Links

[[v12/index]]

## Source References

- `raw/postgres-12/src/backend/access/transam/xact.c:1371`
- `raw/postgres-12/src/backend/access/transam/xlog.c:2086`
- `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:2672`
- `raw/postgres-12/src/backend/storage/smgr/md.c:mdextend`
- `raw/postgres-12/src/backend/storage/file/buffile.c:BufFileWrite`
- `raw/postgres-12/src/backend/access/transam/clog.c:TransactionIdGetStatus`

