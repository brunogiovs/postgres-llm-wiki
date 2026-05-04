---
type: question
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: false
verified_by_agent: not yet
---

# Calculate `avg_leaf_density` Inside (Auto)VACUUM And Persist It Per Index

## Question

In PostgreSQL 18, design how to modify VACUUM and autovacuum so that, after every successful (auto)vacuum of a btree index, an [[v18/code-paths/pgstatindex|pgstatindex]]-style `avg_leaf_density` is computed and stored in a stat table keyed by the index, so that the value is queryable without ever running `pgstatindex`. Assume the primary version from [[versions]].

## Design Goal: Zero Added I/O

The hard constraint on this design is "do not read any page that VACUUM would not already have read, do not lock any page VACUUM would not already have locked, and do not generate any storage write that VACUUM would not already have generated". The whole reason this is feasible is that `btvacuumscan` *already* visits and cleanup-locks every leaf page in the index, and `pgstatindex` derives `avg_leaf_density` from data that lives in the page header (`pd_lower`, `pd_upper`, `pd_special`) of those very same pages. So the value can be computed inline using the bytes already in the buffer at the moment VACUUM is touching it. Every choice in this page (where to read, where to accumulate, where to persist, what storage layer to use) is selected to preserve that invariant. See [[#Zero-Added-I/O Audit]] below for a per-dimension proof.

## Short Answer

The fix is structural rather than algorithmic. `pgstatindex` and `btvacuumscan` already walk the same set of pages — every non-meta block of the btree, under a buffer lock — so the work to derive `avg_leaf_density` is *already paid for* inside `btvacuumpage`. Two integer accumulators added next to the existing `num_index_tuples` accounting, plumbed through `IndexBulkDeleteResult`, give the value at zero added page reads, zero added page writes, zero added WAL bytes, and zero added shared/cleanup locks. Persistence rides the existing `update_relstats_all_indexes` boundary at `src/backend/access/heap/vacuumlazy.c:854` so that the value lands at the same moment `pg_class.relpages`/`reltuples` are written, after a *successful* VACUUM of that index. Both manual `VACUUM` and autovacuum already funnel through `vacuum() → lazy_scan_heap → lazy_vacuum_all_indexes → vac_bulkdel_one_index / vac_cleanup_one_index → ambulkdelete / amvacuumcleanup`, so a single change covers both. Citations: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1186`, `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1467`, `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1485`, `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:3722`, `raw/postgres-18/src/backend/postmaster/autovacuum.c:3173`.

The recommended persistence target is the cumulative-statistics system rather than `pg_class` or a hand-rolled regular table: PG 18 ships a `PGSTAT_KIND_RELATION` entry per index OID that already records `last_vacuum_time` / `last_autovacuum_time`, and `pgstat_kind.h` reserves explicit slots for new built-in kinds so a new `PGSTAT_KIND_INDEX_DENSITY` can carry the leaf-byte sums next to that timestamp without DDL, without WAL traffic, and with the same crash semantics as the rest of the cumulative stats. A user view `pg_stat_index_density` over `pg_stat_get_index_density(oid)` exposes it. Citations: `raw/postgres-18/src/include/utils/pgstat_kind.h:28`, `raw/postgres-18/src/include/utils/pgstat_kind.h:46`, `raw/postgres-18/src/backend/utils/activity/pgstat_relation.c:210`, `raw/postgres-18/src/include/pgstat.h:422`.

## What `pgstatindex` Computes Today, And Why VACUUM Already Has That Data

`pgstatindex_impl` opens a btree under `AccessShareLock`, reads the metapage, and then walks every other block under `BUFFER_LOCK_SHARE` from a `BAS_BULKREAD` ring buffer. For each leaf page it accumulates two byte ranges:

```c
max_avail = BLCKSZ - (BLCKSZ - ((PageHeader) page)->pd_special + SizeOfPageHeaderData);
indexStat.max_avail += max_avail;
indexStat.free_space += PageGetExactFreeSpace(page);
```

After the loop:

```c
100.0 - (double) indexStat.free_space / (double) indexStat.max_avail * 100.0
```

is the reported `avg_leaf_density`. Citations: `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:309`, `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:311`, `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:362`. See [[v18/code-paths/pgstatindex]] for the full per-page classification and [[v18/questions/btree-leaf-density-estimate]] for a catalog-only approximation.

The btree VACUUM path already traverses exactly this same per-block surface and goes a step further: `btvacuumpage` upgrades the buffer lock to a *full cleanup lock* on every leaf page over the course of the scan (`_bt_upgradelockbufcleanup`), regardless of whether anything is deleted. The relevant block is:

```c
else if (P_ISLEAF(opaque))
{
    OffsetNumber deletable[MaxIndexTuplesPerPage];
    int         ndeletable;
    ...
    /*
     * Trade in the initial read lock for a full cleanup lock on this
     * page.  We must get such a lock on every leaf page over the course
     * of the vacuum scan, whether or not it actually contains any
     * deletable tuples --- see nbtree/README.
     */
    _bt_upgradelockbufcleanup(rel, buf);
```

Citations: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1467`, `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1485`. The leaf branch is the same one that already increments `num_index_tuples` at `nbtree.c:1637/1639`. So the page is in shared buffers, pinned, leaf-classified, and held under cleanup lock at the exact moment `max_avail` and `free_space` would be summed. Reading `pd_special`, `SizeOfPageHeaderData`, and `PageGetExactFreeSpace(page)` on that page is essentially free in cache and CPU terms.

The implication: there is no need to add a second pass and no need to read the index a second time after VACUUM. The avg_leaf_density numbers are a byproduct of the scan VACUUM is already doing.

## Where The Existing Vacuum Pipeline Already Persists Index Stats

VACUUM (manual or autovacuum) goes through the same funnel:

| Step | Function | File | Notes |
|---|---|---|---|
| 1 | `vacuum(rel_list, &params, bstrategy, …)` | `src/backend/commands/vacuum.c` | One entry point shared by `VACUUM` and autovacuum. |
| 2 | `autovacuum_do_vac_analyze` | `src/backend/postmaster/autovacuum.c:3173` | Autovacuum path: builds a single-element rel list and calls `vacuum()`. |
| 3 | `lazy_scan_heap` → `lazy_vacuum` | `src/backend/access/heap/vacuumlazy.c:1200`, `:441` | Heap-side workhorse that drives the per-index passes. |
| 4 | `lazy_vacuum_all_indexes` | `src/backend/access/heap/vacuumlazy.c:2574` | Loops over `vacrel->indrels[]` calling `lazy_vacuum_one_index`. |
| 5 | `lazy_vacuum_one_index` / `lazy_cleanup_one_index` | `src/backend/access/heap/vacuumlazy.c:3070`, `:3119` | Builds an `IndexVacuumInfo`, calls `vac_bulkdel_one_index` / `vac_cleanup_one_index`. |
| 6 | `parallel_vacuum_process_one_index` | `src/backend/commands/vacuumparallel.c:864` | Equivalent entry for the parallel-vacuum path; copies the result struct into DSM at `:919`–`:922`. |
| 7 | `vac_bulkdel_one_index` / `vac_cleanup_one_index` | `src/backend/commands/vacuum.c:2650`, `:2671` | Thin wrappers around `index_bulk_delete` / `index_vacuum_cleanup`; return an `IndexBulkDeleteResult`. |
| 8 | `ambulkdelete` / `amvacuumcleanup` | `src/include/access/amapi.h`; for btree: `nbtree.c:btbulkdelete` / `nbtree.c:btvacuumcleanup` | The per-AM hooks that actually scan the index. |
| 9 | `update_relstats_all_indexes` | `src/backend/access/heap/vacuumlazy.c:3722` | After `lazy_scan_heap` returns, walks `vacrel->indstats[]` and calls `vac_update_relstats` per index. |
| 10 | `vac_update_relstats` | `src/backend/commands/vacuum.c:1442` | In-place updates `pg_class.relpages` / `reltuples` for the index. |

The struct that carries information back from step 8 to step 9 is:

```c
typedef struct IndexBulkDeleteResult
{
    BlockNumber num_pages;          /* pages remaining in index */
    bool        estimated_count;    /* num_index_tuples is an estimate */
    double      num_index_tuples;   /* tuples remaining */
    double      tuples_removed;     /* # removed during vacuum operation */
    BlockNumber pages_newly_deleted;
    BlockNumber pages_deleted;
    BlockNumber pages_free;
} IndexBulkDeleteResult;
```

Citation: `raw/postgres-18/src/include/access/genam.h:98`. The struct is plain old data, fixed-size, and is `memcpy`'d into DSM by the parallel-vacuum path at `vacuumparallel.c:919`–`:922`. That makes it a natural carrier for two more `uint64` fields.

The contract for `update_relstats_all_indexes` deliberately skips indexes whose stats are inaccurate:

```c
if (istat == NULL || istat->estimated_count)
    continue;
```

Citation: `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:3736`. Any new persisted leaf-density value should follow the same rule: only persist when the bulk-delete/cleanup pass actually walked the index, never when VACUUM bypassed index vacuuming or when the AM returned an estimated result.

## Edge Cases The Design Must Respect

These are the observable cases where an autovacuum runs but a btree index is *not* fully scanned. The persistence layer must not overwrite the stored density in any of them — the most recent good value should remain the source of truth.

1. **Bypass branch.** `lazy_vacuum` skips `lazy_vacuum_all_indexes` entirely when `lpdead_item_pages < BYPASS_THRESHOLD_PAGES * rel_pages` and the dead-item TID store is small. It still calls `lazy_cleanup_one_index`, but with no `btbulkdelete` pass. Citation: `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:2521`–`:2533`.
2. **Cleanup-only no-op.** `btvacuumcleanup` early-returns `NULL` when `_bt_vacuum_needs_cleanup(info->index)` is false. No leaf scan happens. Citation: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1117`–`:1121`.
3. **`ANALYZE` only.** `info->analyze_only` causes `btvacuumcleanup` to return immediately. Citation: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1102`–`:1104`.
4. **Cleanup-only count is an estimate.** When `btvacuumcleanup` chose to call `btvacuumscan(NULL, NULL, 0)` itself, it sets `stats->estimated_count = true`. Citation: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1139`. The leaf-byte sums it produced are still exact (because `max_avail`/`free_space` come from the page header, not from the dedup-affected tuple count), so density can be marked exact even when `num_index_tuples` is flagged as estimated. The per-index density record should track the two confidences separately.
5. **VACUUM of a non-btree index.** Other index AMs do not produce leaf-density data. The default behavior must be "leave the field NULL / do not write a record" rather than synthesize one. Tagging the new fields as "btree-only" via the AM check `rel->rd_rel->relam == BTREE_AM_OID` inside the persistence step is the cheapest way to enforce this.
6. **Failsafe / interrupted scan.** When `VacuumFailsafeActive` aborts mid-cycle, `lazy_vacuum_all_indexes` returns `false` and the assertion at `vacuumlazy.c:2556` is reached. The result struct may be partial; the persistence step should also gate on a "scan completed" flag.
7. **Parallel vacuum.** Workers `memcpy` the entire `IndexBulkDeleteResult` to DSM. If the struct gains two `uint64` fields, the leader sees them on the first vacuum cycle without further plumbing. Citation: `raw/postgres-18/src/backend/commands/vacuumparallel.c:919`–`:922`.

## Proposed Source Changes

This is the smallest change that satisfies the question. It is intentionally minimal: add fields where data already flows, gate the new write through the existing post-VACUUM index-stats hook, and add a new pgstat kind so persistence costs are zero for crash safety and DDL.

### 1. Extend `IndexBulkDeleteResult`

`src/include/access/genam.h:98`:

```c
typedef struct IndexBulkDeleteResult
{
    BlockNumber num_pages;
    bool        estimated_count;
    double      num_index_tuples;
    double      tuples_removed;
    BlockNumber pages_newly_deleted;
    BlockNumber pages_deleted;
    BlockNumber pages_free;

    /*
     * Optional density inputs for AMs that walk every leaf page during
     * bulkdelete/cleanup. Both are the byte sums pgstatindex computes.
     * When density_valid is false, callers must ignore the sums and avoid
     * overwriting any persisted density record.
     */
    bool        density_valid;
    uint64      leaf_max_avail_bytes;
    uint64      leaf_free_bytes;
    uint32      leaf_pages_scanned;
} IndexBulkDeleteResult;
```

The struct stays plain-old-data, so the existing `memcpy` in the parallel-vacuum path at `vacuumparallel.c:919`–`:922` keeps working. AMs that do not implement leaf-density accounting set `density_valid = false` (the natural zero-init from `palloc0` at `nbtree.c:1076` and `:1137` already does this).

### 2. Accumulate inside `btvacuumpage`

`src/backend/access/nbtree/nbtree.c`, inside the `else if (P_ISLEAF(opaque))` branch *after* `_bt_upgradelockbufcleanup` and *after* any `_bt_delitems_vacuum` call (so the byte counts reflect the post-vacuum state, matching what `pgstatindex` reports immediately after VACUUM):

```c
{
    Page         leafpage = BufferGetPage(buf);
    PageHeader   ph        = (PageHeader) leafpage;
    uint32       max_avail = ph->pd_special - SizeOfPageHeaderData;

    stats->leaf_max_avail_bytes += max_avail;
    stats->leaf_free_bytes      += PageGetExactFreeSpace(leafpage);
    stats->leaf_pages_scanned   += 1;
}
```

This is the same arithmetic as `pgstatindex.c:309`–`:311`. It is computed only on live leaf pages, matching `pgstatindex`'s classifier (deleted, half-dead, internal pages do not contribute). No new buffer pin and no new lock are taken — `btvacuumpage` already holds the page under cleanup lock here. Reading `pd_special` is a single load; `PageGetExactFreeSpace(page)` is two loads (`pd_upper - pd_lower`) and is the same call `pgstatindex` makes today.

`btvacuumscan` then sets:

```c
stats->density_valid = (stats->leaf_pages_scanned > 0);
```

just before it returns at `nbtree.c:1330`. `btbulkdelete` and `btvacuumcleanup` both already return through `btvacuumscan`, so neither needs any additional work; the AM fields propagate through `index_bulk_delete` / `index_vacuum_cleanup` because those routines simply return the AM's result struct.

### 3. Persist alongside `vac_update_relstats`

`src/backend/access/heap/vacuumlazy.c:3722`, replace `update_relstats_all_indexes` with the existing `vac_update_relstats` call plus a sibling persistence call:

```c
static void
update_relstats_all_indexes(LVRelState *vacrel)
{
    Relation   *indrels   = vacrel->indrels;
    int         nindexes  = vacrel->nindexes;
    IndexBulkDeleteResult **indstats = vacrel->indstats;

    Assert(vacrel->do_index_cleanup);

    for (int idx = 0; idx < nindexes; idx++)
    {
        Relation    indrel = indrels[idx];
        IndexBulkDeleteResult *istat = indstats[idx];

        if (istat == NULL || istat->estimated_count)
            continue;

        vac_update_relstats(indrel, istat->num_pages, istat->num_index_tuples,
                            0, 0, false,
                            InvalidTransactionId, InvalidMultiXactId,
                            NULL, NULL, false);

        /* New: only btree, only when the AM filled the density fields. */
        if (istat->density_valid &&
            indrel->rd_rel->relam == BTREE_AM_OID &&
            istat->leaf_max_avail_bytes > 0)
        {
            pgstat_report_index_density(RelationGetRelid(indrel),
                                        istat->leaf_max_avail_bytes,
                                        istat->leaf_free_bytes,
                                        istat->leaf_pages_scanned,
                                        AmAutoVacuumWorkerProcess());
        }
    }
}
```

Two properties of this placement matter:

- The call sits *inside* the `istat->estimated_count` filter. `pg_class` is only updated when VACUUM has accurate per-index numbers; the same gate keeps stale density from being persisted.
- `update_relstats_all_indexes` runs at `vacuumlazy.c:854`–`:855`, after `lazy_scan_heap` and after the heap-side `vac_update_relstats` for the table. This is the existing "successful index vacuum" boundary: by the time we reach it, the per-index pass returned cleanly, the failsafe did not trip, and the index pass was a real bulkdelete or a real cleanup-with-scan (not the bypass branch). That is exactly the boundary the question asks for.

### 4. New cumulative-statistics kind

`src/include/utils/pgstat_kind.h:28` reserves built-in IDs up to 23 with custom kinds starting at 24. Add a new built-in ID, e.g.

```c
#define PGSTAT_KIND_INDEX_DENSITY 13
```

and bump `PGSTAT_KIND_BUILTIN_MAX` accordingly. The shared and pending entry shapes:

```c
typedef struct PgStat_StatIndexDensityEntry
{
    PgStat_Counter leaf_max_avail_bytes;   /* sum across last successful scan */
    PgStat_Counter leaf_free_bytes;
    PgStat_Counter leaf_pages_scanned;
    PgStat_Counter vacuum_count;           /* successful scans counted */
    TimestampTz    last_vacuum_time;
    TimestampTz    last_autovacuum_time;
    bool           by_autovacuum;          /* origin of the last update */
} PgStat_StatIndexDensityEntry;
```

Persistence handlers go in a new `src/backend/utils/activity/pgstat_index_density.c`, modeled closely on `pgstat_relation.c`. The new file exports:

```c
extern void pgstat_report_index_density(Oid indexoid,
                                        uint64 max_avail_bytes,
                                        uint64 free_bytes,
                                        uint32 leaf_pages_scanned,
                                        bool by_autovacuum);
extern PgStat_StatIndexDensityEntry *
pgstat_fetch_stat_index_density(Oid indexoid);
```

`pgstat_register_kind` (`src/backend/utils/activity/pgstat.c:1465`) is the registration entry point; the fixed `PgStat_KindInfo` array at `pgstat.c:303` for builtin kinds gains a new row with `accessed_across_databases = false`, `shared_size = sizeof(PgStatShared_IndexDensity)`, etc.

The shape mirrors `PGSTAT_KIND_RELATION` deliberately. Because cumulative stats already crash-survive (they are written to the pg_stat permanent file at clean shutdown and reset on crash), the design inherits exactly the same durability semantics that `last_autovacuum_time` already has at `pgstat.h:446`. No catalog DDL, no WAL traffic, no extra toast.

A user-facing view is then a one-liner:

```sql
CREATE VIEW pg_stat_index_density AS
SELECT  c.oid                 AS indexrelid,
        c.relname             AS indexrelname,
        n.nspname             AS schemaname,
        d.leaf_pages_scanned,
        d.leaf_max_avail_bytes,
        d.leaf_free_bytes,
        CASE
            WHEN d.leaf_max_avail_bytes > 0
            THEN 100.0 - 100.0 * d.leaf_free_bytes / d.leaf_max_avail_bytes
            ELSE NULL
        END                                       AS avg_leaf_density,
        d.vacuum_count,
        d.last_vacuum_time,
        d.last_autovacuum_time,
        d.by_autovacuum
FROM    pg_class c
JOIN    pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN LATERAL pg_stat_get_index_density(c.oid) d ON TRUE
WHERE   c.relkind = 'i'
  AND   c.relam   = (SELECT oid FROM pg_am WHERE amname = 'btree');
```

`pg_stat_get_index_density(oid)` is a `SRF_PER_CALL` SRF that wraps `pgstat_fetch_stat_index_density`.

### 5. Drop the row when the index is dropped

`pgstat_drop_entry(PGSTAT_KIND_INDEX_DENSITY, MyDatabaseId, indexoid)` already has a hook in `pgstat_drop_relation` for the `PGSTAT_KIND_RELATION` entry. Add the same call there so that `DROP INDEX` (and reindex-with-different-OID flows that use `RelationDropStorage` plumbing) cleans up the density entry.

## Why This Placement Is "After Each Successful Vacuum"

The question's success requirement maps to two boundaries: per-index success (the AM's bulkdelete/cleanup returned with a non-estimated count) and per-VACUUM success (the heap-side state machine reached the `update_relstats_all_indexes` call without the failsafe path).

- Calling `pgstat_report_index_density` from `update_relstats_all_indexes` automatically inherits the heap-side success guard. If `lazy_vacuum_all_indexes` took the failsafe path, `update_relstats_all_indexes` is reached but `istat->estimated_count` is set on the partial entries, so they are skipped exactly as the existing `pg_class` update is. Citations: `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:854`, `:3736`.
- `density_valid` is set only when `btvacuumscan` actually walked at least one leaf page. The bypass branch never enters the leaf-accumulator and never sets the flag, so it cannot overwrite the persisted record. Citation: `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:2521`–`:2533`.
- `AmAutoVacuumWorkerProcess()` distinguishes user-issued VACUUM from autovacuum, matching the convention `pgstat_report_vacuum` uses today at `pgstat_relation.c:250`–`:255`. The new entry's `by_autovacuum` plus `last_autovacuum_time` keep the audit trail symmetric with the table-side `pg_stat_all_tables` view.

So the "after every successful vacuum or autovacuum of the index" guarantee is the same guarantee `pg_class.relpages` and `pg_class.reltuples` already provide for indexes: it lands at the same boundary, gated by the same per-index estimated-count filter.

## Zero-Added-I/O Audit

The proposal is constructed so each dimension of I/O cost compared to baseline VACUUM is exactly zero. This section walks every relevant dimension to confirm.

### 1. Index page reads

Baseline `btvacuumscan` reads every non-meta block of the index through a `BAS_BULKREAD` ring-buffer access strategy via `read_stream_begin_relation` at `nbtree.c:1270`–`:1278`. The leaf-density accumulator runs *inside* the existing `else if (P_ISLEAF(opaque))` branch of `btvacuumpage` at `nbtree.c:1467`. By that point, the buffer is already pinned and the page is already in shared buffers — both established by `read_stream_next_buffer` at `nbtree.c:1307`. The new code reads three already-in-cache fields (`pd_lower`, `pd_upper`, `pd_special`) of the same page. No `ReadBufferExtended` call, no kernel `read()`, no extra ring-buffer eviction. Citation: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1264`–`:1312`.

### 2. Buffer / cleanup locks

Baseline `btvacuumpage` already takes a full cleanup lock on every leaf page via `_bt_upgradelockbufcleanup` at `nbtree.c:1485` ("we must get such a lock on every leaf page over the course of the vacuum scan, whether or not it actually contains any deletable tuples"). The accumulator runs while that lock is held; it does not call `LockBuffer`, `_bt_lockbuf`, or `_bt_upgradelockbufcleanup`. Citation: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1480`–`:1485`.

### 3. Page writes / dirtying

The accumulator only reads page header bytes. It does not call `MarkBufferDirty`, `MarkBufferDirtyHint`, `PageSetLSN`, `START_CRIT_SECTION`, or `_bt_delitems_vacuum`. The page's dirty bit is unaffected, so VACUUM's eventual write-out behavior is identical to baseline. There is no path by which the leaf-density logic causes a page that would have stayed clean to be written.

### 4. WAL traffic

No `XLogInsert`, no critical section, no `XLogBeginInsert`, no register-buffer call. The cumulative-statistics layer used for persistence is shared-memory only and does not WAL-log. `pgstat_report_vacuum` at `pgstat_relation.c:210` and the corresponding `last_autovacuum_time` write at `pgstat.h:446` are the precedent: per-VACUUM cumulative-stats updates already pay zero WAL today, and `pgstat_report_index_density` follows the same shape.

### 5. System catalog I/O

The persistence call sits next to `vac_update_relstats` (`vacuum.c:1442`) but does *not* add a new `pg_class` column or a new in-place catalog update. `pg_class` already accepts an in-place update at this point in the lifecycle (`vacuumlazy.c:3740`), and the new persistence call routes around it entirely by writing to shared-memory cumulative stats instead. So there is no additional `RowExclusiveLock` on `pg_class`, no extra `systable_inplace_update_*` call, no extra catalog buffer reads. Citation: `raw/postgres-18/src/backend/commands/vacuum.c:1463`–`:1474`.

### 6. Heap I/O for a "stat table"

The question phrase "stat table" is satisfied by the cumulative-statistics shmem entry, surfaced through a SQL view. It is *not* satisfied by inserting into a regular user table, which would generate heap writes, WAL records, possibly index inserts on that stat table, and would re-enter VACUUM accounting recursively. Picking a regular table is the only natural choice that would *break* the zero-I/O invariant; the design rejects it explicitly under "Alternatives Considered".

### 7. Network / replication

Cumulative-stats updates are not logically replicated. Standby servers do not see them, and they do not contribute to `wal_sender` traffic. A replica that wants its own density numbers would need to run its own VACUUM (which is unusual on hot standbys) or the value would simply remain unset there — symmetric with `pg_stat_all_tables.last_autovacuum_time` today.

### 8. CPU per leaf page

The added cost is bounded above by:

| Operation | Cost |
|---|---|
| Read `((PageHeader) page)->pd_special` | 1 cached load |
| Compute `pd_special - SizeOfPageHeaderData` | 1 sub |
| Call `PageGetExactFreeSpace(page)` | static-inline `pd_upper - pd_lower`, 2 cached loads + 1 sub |
| Three `uint32`/`uint64` accumulator increments | 3 adds |

That is roughly five additions and three loads per leaf page, against a baseline that already does cleanup-lock acquisition, page validity checks, line-pointer iteration when `callback` is set, and possibly a `_bt_delitems_vacuum` write. The relative CPU overhead is well under a percent on any realistic index. No allocations, no system calls, no atomics.

### 9. Cleanup-only and bypass paths

The bypass branch at `vacuumlazy.c:2521`–`:2533` skips index vacuuming entirely. The accumulator is never entered; no extra I/O is generated, by definition. The cleanup-only no-op at `nbtree.c:1117`–`:1121` returns `NULL` from `btvacuumcleanup` before any leaf scan. Same property: no work, no I/O. Both cases also leave any previously persisted density value untouched, which is the documented behavior the design wants.

### 10. Parallel vacuum

`parallel_vacuum_process_one_index` already `memcpy`'s `IndexBulkDeleteResult` from worker locals into DSM at `vacuumparallel.c:919`–`:922`. The struct gains 24 bytes (`bool` + `uint64` × 2 + `uint32`, with alignment padding), which raises the DSM segment size by `nindexes * 24` bytes total. That is a one-time DSM allocation increase, not per-page I/O, and is dwarfed by the existing per-index parallel state.

So under each axis the conclusion is the same: every byte the leaf-density logic reads is a byte VACUUM was going to read anyway, every lock it observes is one VACUUM was going to take anyway, and every write it produces is a shared-memory counter update that is not part of VACUUM's I/O budget.

## Cost Analysis

Per leaf page:

- One read of `pd_special` (already in cache; the page is pinned and cleanup-locked).
- One call to `PageGetExactFreeSpace(page)` (`pd_upper - pd_lower`, a `static inline` in `bufpage.h`).
- Three `uint32`/`uint64` increments on the per-AM result struct.

Per index, on top of the existing `vac_update_relstats` call:

- One `pgstat_get_entry_ref_locked` lookup, three counter writes, and one timestamp set. Identical cost shape to `pgstat_report_vacuum`. Citation: `raw/postgres-18/src/backend/utils/activity/pgstat_relation.c:210`.

The persistence layer adds no extra WAL traffic and no new heap or catalog updates. Compared to running `pgstatindex` in a follow-up transaction, the savings are the entire per-block read pass (`O(relpages)` per index), which on bloated indexes is the dominant cost.

## Alternatives Considered

- **Extend `pg_class` with `relleafdensity`.** Rejected. `pg_class` is a hot system catalog; `vac_update_relstats` already uses `systable_inplace_update_begin` to bypass MVCC for `relpages`/`reltuples` because regular updates would defeat VACUUM. Citation: `raw/postgres-18/src/backend/commands/vacuum.c:1463`–`:1474`. Adding a column means an initdb-incompatible catalog change and an extra inplace-update column for a rapidly changing value that does not need transactional semantics.
- **A regular user-table sink that VACUUM writes to.** Rejected. Writes from VACUUM into a regular table are blocked by the `PROC_IN_VACUUM` invariant referenced at `vacuum.c:1418`–`:1421` (a regular insert from a backend with `PROC_IN_VACUUM` is unsafe in the way `vac_update_relstats` documents). The cumulative-statistics shmem path is the project-supported way to record post-VACUUM facts without a regular INSERT.
- **A `pg_stat_progress_vacuum`-style ephemeral row.** Rejected. Progress views are wiped at end-of-vacuum; the question asks for a persisted last-known-good value queryable later.
- **Fold into `pg_stat_all_indexes`.** This is reasonable but conflates two reset semantics (`pg_stat_all_indexes` rows are reset by `pg_stat_reset_single_table_counters` and similar). A dedicated kind keeps the density value resettable on its own and makes the AM-only gating explicit. Both shapes share the same plumbing, so this can be deferred.

## Autovacuum Coverage Without Special Cases

Autovacuum requires zero additional code in `src/backend/postmaster/autovacuum.c`. Each launched worker invokes `autovacuum_do_vac_analyze` (`autovacuum.c:3173`), which forwards a single-relation list to `vacuum()`. From there the path is identical to a user-issued `VACUUM`, and the persistence call from step 3 is reached at the same point. The `by_autovacuum` flag and `last_autovacuum_time` timestamp are derived inside `pgstat_report_index_density` from `AmAutoVacuumWorkerProcess()`, the same condition `pgstat_report_vacuum` uses today.

`VACUUM ANALYZE` and stand-alone `ANALYZE` do not need to reach the new path: `analyze_only` short-circuits `btvacuumcleanup` before any leaf scan, and the bypass branches above prevent overwriting the previous successful sample.

## Caveats

- Deduplication does not affect `max_avail` or `free_space`; both are page-header derived. So the new density value is *not* skewed by dedup the way the catalog estimate in [[v18/questions/btree-leaf-density-estimate]] is. It matches `pgstatindex`'s output exactly, with one subtlety: the new value is captured *after* `_bt_delitems_vacuum`, so it reflects post-vacuum free space, while a later `pgstatindex` call would report whatever state the index has reached by then. That is the "more useful" point in time for monitoring bloat trajectories.
- Cleanup-only scans by `btvacuumcleanup` set `estimated_count = true`; under the `update_relstats_all_indexes` filter at `vacuumlazy.c:3736`, the new persistence call is also skipped. If preserving density data from cleanup-only scans is desirable, the gate can be split: persist density when `density_valid` is set even if `estimated_count` is true, and continue to skip `pg_class.reltuples` updates. The default proposed here keeps both writes under the same gate to avoid introducing a new "partially-trusted index stats" mode.
- Non-btree AMs (GIN, hash, BRIN, GIST, SP-GiST) leave `density_valid = false`. Their leaf-density story is different and is out of scope.
- Block size changes. Sums are stored in bytes, not in fractions, so a cluster rebuilt under a different `BLCKSZ` produces sums that scale automatically. The view computes the percentage at SELECT time.

## Cross-Links

- [[v18/code-paths/pgstatindex]] - The user-space scan whose result this design persists for free during VACUUM.
- [[v18/questions/btree-leaf-density-estimate]] - Catalog-only approximation when no recent VACUUM has been observed.
- [[v18/index]]
- [[versions]]

## Source References

- `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:309`
- `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:311`
- `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:362`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:btbulkdelete`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:btvacuumcleanup`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:btvacuumscan`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1068`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1098`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1102`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1117`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1139`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1186`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1330`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1361`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1467`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1485`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1637`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1639`
- `raw/postgres-18/src/include/access/genam.h:67`
- `raw/postgres-18/src/include/access/genam.h:98`
- `raw/postgres-18/src/backend/commands/vacuum.c:1442`
- `raw/postgres-18/src/backend/commands/vacuum.c:2650`
- `raw/postgres-18/src/backend/commands/vacuum.c:2671`
- `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:854`
- `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:2521`
- `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:2574`
- `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:3070`
- `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:3119`
- `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:3722`
- `raw/postgres-18/src/backend/access/heap/vacuumlazy.c:3736`
- `raw/postgres-18/src/backend/commands/vacuumparallel.c:864`
- `raw/postgres-18/src/backend/commands/vacuumparallel.c:919`
- `raw/postgres-18/src/backend/postmaster/autovacuum.c:3173`
- `raw/postgres-18/src/include/pgstat.h:422`
- `raw/postgres-18/src/include/pgstat.h:446`
- `raw/postgres-18/src/include/utils/pgstat_kind.h:28`
- `raw/postgres-18/src/include/utils/pgstat_kind.h:42`
- `raw/postgres-18/src/include/utils/pgstat_kind.h:46`
- `raw/postgres-18/src/backend/utils/activity/pgstat.c:303`
- `raw/postgres-18/src/backend/utils/activity/pgstat.c:1465`
- `raw/postgres-18/src/backend/utils/activity/pgstat_relation.c:210`

## Open Questions

- Should the new pgstat kind also carry `leaf_fragmentation` (counted via `btpo_next < blkno` exactly as `pgstatindex` does) so that the persisted view replaces both density columns, or should fragmentation stay in `pgstatindex` because it is a less actionable metric? Adding it costs one comparison and one increment per leaf in `btvacuumpage` and one extra counter in the entry struct.
- Cleanup-only `btvacuumcleanup` scans set `estimated_count = true` because of posting-list undercounting in `num_index_tuples` (`nbtree.c:1131`–`:1136`), but the leaf-byte sums are exact. Should the design split the persistence gate so density is preserved from cleanup-only scans even when `pg_class.reltuples` is skipped? That would shorten the staleness window for low-churn indexes that rarely trigger a bulkdelete pass.
- For non-btree AMs, is it worth defining an AM-level callback `amleafdensity` so that hash and GIN can opt in to the same persistence path with their own definitions of "leaf"? The shape of `IndexBulkDeleteResult` already permits AM extensions because the result struct is documented at `genam.h:86`–`:88` as "An index AM could choose to return a larger struct of which this is just the first field"; the new fields could move into AM-private subclasses if the cross-AM story matters.
