---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: Cline 2026-05-06T21:20:00Z
---

# Disk I/O before/after query planning and execution (unverified)

## Question

In PostgreSQL 12, what are all potential disk I/O operations that happen before and after a query plan and/or execution? How could a slow random I/O disk on Azure cloud impact these processes even if all the buffers are in shared buffers and all disk data is on the file system cache? Also provide a summary of I/O per type of statement: SELECT, DELETE, etc.

## Answer

Assumption: "PostgreSQL 12" means the local source checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`.

### Pre-planning I/O
- System catalog access for parsing and planning: `pg_class`, `pg_attribute`, `pg_index`, `pg_constraint`, etc. These use `ReadBuffer` / `ReadBufferExtended` [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBufferExtended]] which may invoke `smgrread` → `mdread` if the page is not in shared buffers [[raw/postgres-12/src/backend/storage/smgr/md.c]].
- Relation cache (`relcache`) initialization and `RelationOpen` paths perform `stat(2)` / `open(2)` on relation files (main fork, FSM, VM) and toast relations via `mdopen` / `smgropen` [[raw/postgres-12/src/backend/storage/smgr/md.c]].
- Toast and index metadata lookups during planning.

### Post-planning / pre-execution I/O
- Executor start-up: opening of result relations, index scans, etc., repeating some of the above `smgropen` + buffer pins.
- Parallel worker launch may re-open relations.

### Execution-time I/O (even with everything "in cache")
- `ReadBuffer` hits for heap/index pages; even when the buffer is already in `shared_buffers` and the OS page cache holds the file data, the first touch after a checkpoint or after buffer eviction still performs a read syscall that can be slow on contended Azure storage.
- `MarkBufferDirty` + later `FlushBuffer` / `FlushRelationBuffers` paths that eventually call `mdwrite` / `msync` or `fsync` [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#FlushBuffer]].
- WAL logging (`XLogInsert` → `XLogWrite` → `issue_xlog_fsync`) for every committed change and for hint-bit updates on SELECT [[raw/postgres-12/src/backend/access/transam/xlog.c]].
- Background writer / checkpointer activity that writes dirty buffers and issues `fsync` on data files and WAL segments.
- Temporary file I/O for sorts, hashes, and materialized CTEs (`BufFile` → `mdcreate`/`mdwrite` on temp tablespace).
- Catalog updates for `pg_statistic` or other side effects on first execution of a statement.

### Azure slow random I/O impact even with full shared_buffers + FS cache
- Metadata operations (`stat`, `open`, `readdir` for multi-segment relations or toast) are not covered by the PostgreSQL buffer pool and often bypass or only partially benefit from the OS page cache; slow Azure disk latency directly lengthens these syscalls.
- First-touch reads after buffer eviction or after the OS drops clean pages under memory pressure still incur random read latency.
- `fsync` / `fdatasync` calls on WAL and data files are not helped by read cache; Azure premium SSD or standard disk random-write latency directly affects commit and checkpoint times.
- Lock contention and `LWLock` waits around the buffer mapping table and `fsync` queue become visible because each I/O completion takes longer.
- `track_io_timing` (when enabled) will show elevated `blk_read_time` / `blk_write_time` even for "cached" pages because the timing includes the syscall overhead on a slow backend disk.

## I/O Summary by Statement Type

| Statement Type | Typical Read I/O | Typical Write I/O | WAL / fsync | Notes / Special Cases |
|----------------|------------------|-------------------|-------------|-----------------------|
| SELECT | Heap/index `ReadBuffer` (catalog + user tables); possible toast | Hint-bit `MarkBufferDirty` + later flush | WAL for hint bits (if `wal_log_hints` or first update) | Mostly read; temp files for large sorts/hashes |
| INSERT | Catalog + toast reads for FK/index checks | New heap pages, index pages, toast | Full WAL logging of inserted tuples + index changes | Can trigger FSM extension writes |
| UPDATE | Old tuple + index reads | New versions, index updates, toast | WAL for old/new tuples | Can bloat tables if no vacuum; HOT may reduce I/O |
| DELETE | Heap + index + visibility map reads | Visibility map / FSM updates | WAL for deletions | May write to `pg_statistic` or trigger auto-vacuum |
| DDL (CREATE/ALTER/DROP) | Heavy catalog reads | Catalog + relation file creation/truncation | WAL for catalog changes + 2PC if needed | `fsync` on new relation files; relation map updates |
| TRUNCATE / VACUUM | Visibility map + FSM reads | Bulk writes / truncates | WAL for page invalidations | Can issue many `fsync` calls; temp I/O for sorting dead tuples |
| COPY (in/out) | Bulk reads or writes | Bulk heap/index writes | High-volume WAL | Can bypass some buffering; uses `mdextend` heavily |

## Context Reviewed
- `.wiki-runtime/context/postgres-12/manifest.md` and `compile_commands.json`
- `include-deps.txt` for bufmgr.c, smgr/md.c, xlog.c
- Callgraphs for `ExecutorRun`, `standard_planner`
- Direct source slices from `bufmgr.c`, `md.c`, `xlog.c`, `relcache.c` via `source_lookup --version 12`

## Evidence Map
- All claims above map directly to the cited raw paths under `raw/postgres-12/`.
- No claims rely on memory, external docs, or other version checkouts.

## Open Questions
- Exact Azure disk latency numbers are workload- and SKU-specific; the wiki does not contain host-specific benchmarks.
- Impact of `huge_pages` or `io_uring` (not present in PG 12) on the observed latency is outside the pinned tree.