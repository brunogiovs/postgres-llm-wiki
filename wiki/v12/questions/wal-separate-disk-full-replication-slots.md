---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: gpt-5 2026-05-07T16:15:33Z
---

# WAL on a separate full disk and replication slots

## Question

In PostgreSQL 12, if WAL is stored on a separate disk and that WAL disk runs out of space, what happens to replication slots? Does placing `pg_wal` on a disk separate from the data directory make database corruption risk higher or lower?

## Answer

Assumption: "PostgreSQL 12" means the local checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`.

The short answer is: a full WAL filesystem is an availability outage, not a normal replication-slot state transition. PostgreSQL 12 documentation says that if the filesystem containing `pg_wal` fills up, PostgreSQL performs a PANIC shutdown; committed transactions are not lost, but the database stays offline until space is freed [[raw/postgres-12/doc/src/sgml/backup.sgml|backup.sgml#L663-L677]]. Replication slots are not automatically dropped or invalidated to save space. In PG 12, slots can retain unbounded WAL: the docs state that replication slots prevent removal of needed WAL and that, unlike alternatives such as `wal_keep_segments` or archiving, there is no way in this version to bound `pg_wal` space use with slots [[raw/postgres-12/doc/src/sgml/high-availability.sgml|high-availability.sgml#L914-L930]].

### What happens to slots

Persistent replication slot metadata lives under the data directory's `pg_replslot`, while WAL segment files live under `pg_wal` [[raw/postgres-12/doc/src/sgml/storage.sgml|storage.sgml#L102-L147]]. `ReplicationSlotSave()` writes the acquired slot state under `pg_replslot/<slot_name>`, and checkpoint-time slot saving iterates in-use slots and saves them to the same directory [[raw/postgres-12/src/backend/replication/slot.c#ReplicationSlotSave|slot.c#ReplicationSlotSave]], [[raw/postgres-12/src/backend/replication/slot.c#CheckPointReplicationSlots|slot.c#CheckPointReplicationSlots]].

The WAL-retention part is separate: `ReplicationSlotsComputeRequiredLSN()` scans all in-use slots, finds the oldest valid `restart_lsn`, and passes it to the WAL subsystem [[raw/postgres-12/src/backend/replication/slot.c#ReplicationSlotsComputeRequiredLSN|slot.c#ReplicationSlotsComputeRequiredLSN]]. During checkpoint cleanup, `KeepLogSeg()` uses that slot minimum LSN, after considering `wal_keep_segments`, to avoid deleting WAL segments still required by slots [[raw/postgres-12/src/backend/access/transam/xlog.c#KeepLogSeg|xlog.c#KeepLogSeg]]. Then `CreateCheckPoint()` calls `RemoveOldXlogFiles()` only after applying that retention boundary [[raw/postgres-12/src/backend/access/transam/xlog.c#CreateCheckPoint|xlog.c#CreateCheckPoint]], [[raw/postgres-12/src/backend/access/transam/xlog.c#RemoveOldXlogFiles|xlog.c#RemoveOldXlogFiles]].

So, if a lagging or abandoned slot is the reason the WAL disk fills, the slot keeps retaining WAL until the consumer catches up, the slot is advanced, or the slot is dropped. `pg_replication_slot_advance()` will not move a slot backward and clamps the target to already flushed or replayed WAL; `pg_drop_replication_slot()` drops the named slot [[raw/postgres-12/src/backend/replication/slotfuncs.c#pg_replication_slot_advance|slotfuncs.c#pg_replication_slot_advance]], [[raw/postgres-12/src/backend/replication/slotfuncs.c#pg_drop_replication_slot|slotfuncs.c#pg_drop_replication_slot]]. The SQL-level docs warn that advancing a slot can be lost back to an earlier position after a crash until the updated slot information is written at a later checkpoint [[raw/postgres-12/doc/src/sgml/func.sgml|func.sgml#L20883-L20903]]. That failure mode retains more WAL than expected; it is not a slot being corrupted or auto-removed.

Temporary slots are different: the catalog docs say temporary slots are not saved to disk and are automatically dropped on error or session finish [[raw/postgres-12/doc/src/sgml/catalogs.sgml|catalogs.sgml#L9905-L9911]]. Persistent physical or logical slots should be expected to survive a restart unless intentionally dropped; the v12 recovery tests include physical and logical slot-advance persistence across clean restarts [[raw/postgres-12/src/test/recovery/t/001_stream_rep.pl|001_stream_rep.pl#L348-L371]], [[raw/postgres-12/src/test/recovery/t/006_logical_decoding.pl|006_logical_decoding.pl#L138-L160]].

### Disk-full failure path

The source matches the documentation. When normal WAL writing fails, `XLogWrite()` reports `PANIC` for a failed WAL `pg_pwrite()` [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogWrite|xlog.c#XLogWrite]]. When PostgreSQL has to initialize a new WAL segment, `XLogFileInit()` creates a temporary segment in `pg_wal`, writes or allocates the full segment, treats a short write without `errno` as `ENOSPC`, unlinks the temporary file, and errors; its own comment states that these errors promote to PANIC if called inside a critical section [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogFileInit|xlog.c#XLogFileInit]]. `XLogWrite()` calls `XLogFileInit()` from inside its WAL-write critical path when switching segments [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogWrite|xlog.c#XLogWrite]].

That is why a full WAL disk stops the cluster rather than allowing normal writes to continue without WAL. The buffer manager also enforces the WAL-before-data rule when writing permanent data buffers: `FlushBuffer()` flushes WAL up to the page LSN before writing the data page [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#FlushBuffer|bufmgr.c#FlushBuffer]]. The WAL chapter explains the recovery side: after a checkpoint, recovery reads `pg_control`, reads the checkpoint record, and replays WAL; with `full_page_writes` enabled, pages changed since checkpoint are restored to a consistent state [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L787-L799]].

### Corruption risk with separate WAL storage

Putting WAL on a different disk is not inherently more corrupting. PostgreSQL 12 documentation explicitly says it is advantageous for WAL to be on a different disk from the main database files and describes doing that by moving `pg_wal` while the server is shut down and symlinking it back into the data directory [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L751-L772]].

With equally reliable storage that correctly reports write and fsync failures, separating WAL usually lowers the chance that retained WAL consumes the same filesystem space needed by relation files, temporary files, and other data-directory contents. It does not lower the availability risk of WAL exhaustion: if the WAL filesystem fills, PostgreSQL still PANICs and remains offline until space is available [[raw/postgres-12/doc/src/sgml/backup.sgml|backup.sgml#L663-L677]].

The corruption risk depends more on WAL storage reliability than on whether the disk is separate. The WAL docs state that WAL's purpose is to ensure the log is written before database records are altered, and warn that disks holding WAL must not falsely report successful writes; false write success can lead to irrecoverable data corruption after power failure [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L774-L785]]. A separate WAL disk that is less reliable, not monitored, or too small can therefore raise operational risk. A separate WAL disk that is reliable, monitored, and sized for slot lag and archive delays can reduce data-filesystem pressure without increasing PostgreSQL's source-visible corruption risk.

### Operational check

The diagnostic query below is read-only and uses session-scoped timeouts. `statement_timeout` and `lock_timeout` are `PGC_USERSET`, so `SET` changes apply to the current session and need no restart or reload [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout|guc.c#statement_timeout]], [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout|guc.c#lock_timeout]], [[raw/postgres-12/src/include/utils/guc.h#GucContext|guc.h#GucContext]].

Choose timeout values appropriate to the incident. During a WAL-space incident, keep the query short and avoid piling up behind locks:

```sql
SET /* wiki_slot_retention_timeouts */ statement_timeout = '15s';
SET /* wiki_slot_retention_timeouts */ lock_timeout = '2s';

SELECT /* wiki_replication_slot_wal_retention */
       slot_name,
       slot_type,
       active,
       restart_lsn,
       confirmed_flush_lsn,
       pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) AS retained_bytes,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained_pretty
FROM pg_replication_slots
WHERE restart_lsn IS NOT NULL
ORDER BY pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) DESC;
```

The query uses the PG 12 `pg_replication_slots` view columns `slot_name`, `slot_type`, `active`, `restart_lsn`, and `confirmed_flush_lsn`; `restart_lsn` is documented as the oldest WAL that may still be required by that slot and therefore will not be automatically removed during checkpoints [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_replication_slots|system_views.sql#pg_replication_slots]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml|catalogs.sgml#L9836-L9970]]. `pg_current_wal_lsn()` and `pg_wal_lsn_diff(pg_lsn, pg_lsn)` exist in PG 12 and return the current WAL write location and a byte difference respectively; `pg_size_pretty(numeric)` formats the byte count [[raw/postgres-12/src/include/catalog/pg_proc.dat#pg_current_wal_lsn|pg_proc.dat#pg_current_wal_lsn]], [[raw/postgres-12/src/include/catalog/pg_proc.dat#pg_wal_lsn_diff|pg_proc.dat#pg_wal_lsn_diff]], [[raw/postgres-12/src/include/catalog/pg_proc.dat#pg_size_pretty|pg_proc.dat#pg_size_pretty]].

If the cluster is already down because the WAL filesystem is full, first add/free space at the filesystem or volume level so PostgreSQL can start. Do not delete WAL segments that PostgreSQL still needs. After startup, remove the retention cause by fixing the consumer, dropping an obsolete slot, or advancing a slot only when rebuilding or skipping the downstream consumer is acceptable; the next checkpoint cleanup can then remove/recycle WAL no longer protected by slot `restart_lsn` [[raw/postgres-12/src/backend/access/transam/xlog.c#CreateCheckPoint|xlog.c#CreateCheckPoint]], [[raw/postgres-12/src/backend/access/transam/xlog.c#KeepLogSeg|xlog.c#KeepLogSeg]].

## Context Reviewed

- Navigation and bookkeeping: `wiki/versions.md`, `wiki/index.md`, recent `wiki/log.md`, `wiki/v12/index.md`.
- Context pack: `.wiki-runtime/context/postgres-12/manifest.md`, generated from `raw/postgres-12` at commit `45b88269a353ad93744772791feb6d01bc7e1e42`; no deferred or failed artifacts recorded.
- Context artifacts used: `compile_commands.json`, `include-deps.txt`, direct include queries for `src/backend/access/transam/xlog.c` and `src/backend/replication/slot.c`, compile-unit queries for `xlog.c`, `slot.c`, and `slotfuncs.c`, and reverse include users of `access/xlog.h`.
- Source search envelope: targeted `scripts/source_lookup --version 12` searches and slices for `pg_wal`, `pg_replslot`, `ReplicationSlotsComputeRequiredLSN`, `KeepLogSeg`, `RemoveOldXlogFiles`, `CreateCheckPoint`, `XLogWrite`, `XLogFileInit`, `FlushBuffer`, `pg_replication_slot_advance`, `pg_drop_replication_slot`, `pg_replication_slots`, `pg_current_wal_lsn`, `pg_wal_lsn_diff`, `pg_size_pretty`, `statement_timeout`, `lock_timeout`, `max_replication_slots`, `wal_keep_segments`, and related documentation.
- Tests checked: `src/test/recovery/t/001_stream_rep.pl`, `src/test/recovery/t/006_logical_decoding.pl`, `contrib/test_decoding/sql/slot.sql`, and targeted `rg` searches under `src/test` and `contrib` for `ENOSPC`, `No space`, disk-full, and WAL-full behavior. I found slot creation/advance/drop/persistence coverage, but not a v12 regression test that simulates a full `pg_wal` filesystem.

## Evidence Map

- WAL and slot directories: `pg_replslot` and `pg_wal` directory roles are documented in [[raw/postgres-12/doc/src/sgml/storage.sgml|storage.sgml#L102-L147]]; `pg_wal` storage and separate-disk symlink setup are documented in [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L751-L772]].
- Slot retention: docs state slots retain needed WAL and have no PG 12 space bound in [[raw/postgres-12/doc/src/sgml/high-availability.sgml|high-availability.sgml#L914-L930]]; code computes the oldest slot `restart_lsn` in [[raw/postgres-12/src/backend/replication/slot.c#ReplicationSlotsComputeRequiredLSN|slot.c#ReplicationSlotsComputeRequiredLSN]] and applies it during WAL cleanup in [[raw/postgres-12/src/backend/access/transam/xlog.c#KeepLogSeg|xlog.c#KeepLogSeg]].
- Slot state persistence: slot state is saved under `pg_replslot` by [[raw/postgres-12/src/backend/replication/slot.c#ReplicationSlotSave|slot.c#ReplicationSlotSave]] and checkpoint slot saving by [[raw/postgres-12/src/backend/replication/slot.c#CheckPointReplicationSlots|slot.c#CheckPointReplicationSlots]]; tests cover clean-restart persistence for physical and logical slot advance in [[raw/postgres-12/src/test/recovery/t/001_stream_rep.pl|001_stream_rep.pl#L348-L371]] and [[raw/postgres-12/src/test/recovery/t/006_logical_decoding.pl|006_logical_decoding.pl#L138-L160]].
- Disk-full behavior: docs state a full `pg_wal` filesystem causes PANIC shutdown, no committed transactions lost, and offline status until space is freed in [[raw/postgres-12/doc/src/sgml/backup.sgml|backup.sgml#L663-L677]]; WAL write/create paths are [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogWrite|xlog.c#XLogWrite]] and [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogFileInit|xlog.c#XLogFileInit]].
- Corruption risk: WAL-before-data is enforced by [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#FlushBuffer|bufmgr.c#FlushBuffer]] and described in [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L774-L799]]; unreliable WAL storage can lead to irrecoverable corruption if it falsely reports write success in [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml#L774-L785]].
- Monitoring query: `pg_replication_slots` view definition and documented columns are in [[raw/postgres-12/src/backend/catalog/system_views.sql#pg_replication_slots|system_views.sql#pg_replication_slots]] and [[raw/postgres-12/doc/src/sgml/catalogs.sgml|catalogs.sgml#L9836-L9970]]; functions and timeout GUCs are in [[raw/postgres-12/src/include/catalog/pg_proc.dat#pg_current_wal_lsn|pg_proc.dat#pg_current_wal_lsn]], [[raw/postgres-12/src/include/catalog/pg_proc.dat#pg_wal_lsn_diff|pg_proc.dat#pg_wal_lsn_diff]], [[raw/postgres-12/src/include/catalog/pg_proc.dat#pg_size_pretty|pg_proc.dat#pg_size_pretty]], [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout|guc.c#statement_timeout]], and [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout|guc.c#lock_timeout]].

## Open Questions

- The pinned PG 12 source and tests do not include a regression test that exhausts the `pg_wal` filesystem. The disk-full claim is therefore grounded in the PG 12 documentation and source error paths, not in a local test run that fills a filesystem.
- The source does not quantify how much separate WAL storage changes real-world corruption probability. The answer treats corruption risk as dependent on WAL device reliability, truthful write/fsync behavior, monitoring, and capacity, which are outside the pinned PostgreSQL source tree.

## Source References

- Source pin and context pack: [[raw/postgres-12/]], `.wiki-runtime/context/postgres-12/manifest.md`
- WAL storage, recovery, and disk-full behavior: [[raw/postgres-12/doc/src/sgml/wal.sgml|wal.sgml]], [[raw/postgres-12/doc/src/sgml/backup.sgml|backup.sgml]], [[raw/postgres-12/doc/src/sgml/storage.sgml|storage.sgml]]
- WAL write, segment creation, checkpoint cleanup, and buffer WAL-before-data enforcement: [[raw/postgres-12/src/backend/access/transam/xlog.c|xlog.c]], [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c|bufmgr.c]]
- Replication slot state and SQL functions: [[raw/postgres-12/src/backend/replication/slot.c|slot.c]], [[raw/postgres-12/src/backend/replication/slotfuncs.c|slotfuncs.c]], [[raw/postgres-12/src/backend/catalog/system_views.sql|system_views.sql]], [[raw/postgres-12/src/include/catalog/pg_proc.dat|pg_proc.dat]]
- Replication-slot docs and monitoring columns: [[raw/postgres-12/doc/src/sgml/high-availability.sgml|high-availability.sgml]], [[raw/postgres-12/doc/src/sgml/catalogs.sgml|catalogs.sgml]], [[raw/postgres-12/doc/src/sgml/func.sgml|func.sgml]]
- GUC timeout context: [[raw/postgres-12/src/backend/utils/misc/guc.c|guc.c]], [[raw/postgres-12/src/include/utils/guc.h|guc.h]]
- Tests inspected: [[raw/postgres-12/src/test/recovery/t/001_stream_rep.pl|001_stream_rep.pl]], [[raw/postgres-12/src/test/recovery/t/006_logical_decoding.pl|006_logical_decoding.pl]], [[raw/postgres-12/contrib/test_decoding/sql/slot.sql|slot.sql]]
