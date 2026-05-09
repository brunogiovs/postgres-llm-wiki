---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# REINDEX CONCURRENTLY disk space requirements (unverified)

## Question

In PostgreSQL 12, with a table heap of 10 GB and an index of 5 GB, how much extra disk space is needed to safely run `REINDEX INDEX CONCURRENTLY` on a production database?

## Answer

Assumption: "PostgreSQL 12" means the local source checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`. Assumed default tablespace, a single regular B-tree index, and `wal_level >= replica` on a primary that is being archived or streamed to a standby.

Headline sizing for a 5 GB B-tree index:

- Reserve **≥ 2× the old index size on the data filesystem** that holds the index's tablespace, so roughly **10 GB free**. The actual peak occupancy of the new file is ~5 GB, but the old file is kept until phase 6, catch-up writes can extend the new file, and the gap between the swap and the drop should not push the filesystem to full.
- Reserve **≈ 1× the index size on `pg_wal`** above your normal headroom, so roughly **5 GB free**. The build WAL-logs every page through `log_newpage`.
- Reserve **up to ≈ 1× the index size in temp space** (under `temp_tablespaces`, or `base/pgsql_tmp/` if unset) for the B-tree build sort, unless `maintenance_work_mem` is large enough to hold the sort in memory.
- The 10 GB heap is read but **not rewritten**, so the heap-side filesystem only needs the small overhead of catch-up WAL.

`REINDEX CONCURRENTLY` does not move the index to a different tablespace. The new file is created in the old index's tablespace, so all per-index disk pressure lands on that filesystem [[raw/postgres-12/src/backend/catalog/index.c#index_concurrently_create_copy|index.c#index_concurrently_create_copy]].

## Six Phases And What They Cost

`ReindexRelationConcurrently()` runs in six explicitly numbered phases [[raw/postgres-12/src/backend/commands/indexcmds.c#ReindexRelationConcurrently|indexcmds.c#ReindexRelationConcurrently]].

| Phase | What it does | Disk impact for a 5 GB index |
|---|---|---|
| 1. Catalog entry | Creates the new index row named `<idx>_ccnew` with `INDEX_CREATE_SKIP_BUILD | INDEX_CREATE_CONCURRENT`, in the **same tablespace** as the old index | Zero index data; tiny catalog rows in `pg_class`, `pg_index`, dependencies. |
| 2. Build | `index_concurrently_build()` calls `index_build()`, which for B-tree drives `btbuild()` → `_bt_spools_heapscan()` → `_bt_leafbuild()` → `_bt_load()` → `_bt_blwritepage()` | New file grows from 0 to ~5 GB; sort spill up to ~5 GB in temp space if it exceeds `maintenance_work_mem`; WAL records for every page. |
| 3. Catch-up | Waits for in-flight transactions, then `validate_index()` scans the heap and inserts missed tuples into the new index | New index file may grow further by the volume of writes that landed during phase 2; bounded by table churn during the build window. |
| 4. Swap | `index_concurrently_swap()` flips names: `_ccnew` → original name, original → `_ccold`, sets `indisvalid` correctly | No file movement; both files still on disk. |
| 5. Mark dead | `index_concurrently_set_dead()` flips `indisready`/`indislive` on the old (now `_ccold`) row | No data file change. |
| 6. Drop | `performMultipleDeletions(... PERFORM_DELETION_CONCURRENT_LOCK ...)` removes the old `_ccold` index | Old 5 GB file is unlinked, freeing the space [[raw/postgres-12/src/backend/commands/indexcmds.c#ReindexRelationConcurrently|indexcmds.c#L3296-L3329]]. |

Phase boundaries: phase 2 builds, phases 3 catch up via `validate_index`, phase 4 swaps, phase 6 drops [[raw/postgres-12/src/backend/commands/indexcmds.c#ReindexRelationConcurrently|indexcmds.c#L2941-L2955]], [[raw/postgres-12/src/backend/catalog/index.c#index_concurrently_swap|index.c#index_concurrently_swap]], [[raw/postgres-12/src/backend/catalog/index.c#validate_index|index.c#validate_index]].

The peak coexistence window is from the start of phase 2 through phase 6: the old 5 GB file and the new 5 GB-plus file live side by side.

## Where The Bytes Land

| Bucket | Approximate volume | Filesystem | Source |
|---|---|---|---|
| New index data file (`_ccnew`) | ~5 GB | Same tablespace as old index (uses `indexRelation->rd_rel->reltablespace`) | [[raw/postgres-12/src/backend/catalog/index.c#index_concurrently_create_copy|index.c#index_concurrently_create_copy]] |
| Old index data file kept until phase 6 | ~5 GB | Same tablespace | [[raw/postgres-12/src/backend/commands/indexcmds.c#ReindexRelationConcurrently|indexcmds.c#L3296-L3329]] |
| Catch-up growth on the new index | Bounded by tuple writes during the build window; small for cold tables, larger for hot ones | Same tablespace | `validate_index()` insert path [[raw/postgres-12/src/backend/catalog/index.c#validate_index|index.c#validate_index]] |
| B-tree build sort spill | Up to ~5 GB if the sort does not fit in `maintenance_work_mem`; near zero otherwise | `temp_tablespaces` if set, otherwise `base/<dboid>/pgsql_tmp/` | `tuplesort_performsort()` in [[raw/postgres-12/src/backend/access/nbtree/nbtsort.c#_bt_leafbuild|nbtsort.c#_bt_leafbuild]] |
| Validate-phase TID sort | ~8 bytes per index entry; small relative to the index size | Same temp location as above | [[raw/postgres-12/src/backend/catalog/index.c#validate_index|index.c#L3239-L3269]] |
| WAL on `pg_wal` | ~5 GB above normal traffic, because `_bt_blwritepage()` calls `log_newpage()` for every page when `XLogIsNeeded() && RelationNeedsWAL(index)` | `pg_wal/` (default) or its symlink target | [[raw/postgres-12/src/backend/access/nbtree/nbtsort.c#_bt_blwritepage|nbtsort.c#_bt_blwritepage]], [[raw/postgres-12/src/backend/access/nbtree/nbtsort.c#_bt_leafbuild|nbtsort.c#L580]] |

`btws_use_wal` is set to `XLogIsNeeded() && RelationNeedsWAL(wstate.index)` [[raw/postgres-12/src/backend/access/nbtree/nbtsort.c#_bt_leafbuild|nbtsort.c#L580]]. On a primary with archiving or replication enabled (`wal_level = replica` or higher), `XLogIsNeeded()` is true, so the entire build is WAL-logged.

The 10 GB heap is read but never rewritten by `REINDEX CONCURRENTLY`. `validate_index()` rescans the heap to insert missed tuples but does not copy heap data anywhere [[raw/postgres-12/src/backend/catalog/index.c#validate_index|index.c#validate_index]].

## Practical Sizing Recipe

For a single 5 GB B-tree index:

1. **Index tablespace filesystem**: ≥ 10 GB free (≥ 2× the old index size). The minimum is 1× to hold the new file alongside the old, but a 2× cushion absorbs catch-up writes, sort spill if `temp_tablespaces` is unset and falls into the same volume, and the gap before phase 6 frees the old file.
2. **`pg_wal` filesystem**: ≥ 5 GB free above normal headroom, more if `wal_keep_segments`, replication slots, or archive lag retain segments. A stuck slot can balloon `pg_wal` past the build size.
3. **Temp tablespace** (or `base/` if `temp_tablespaces` is unset): size `maintenance_work_mem` so the build sort and the validate-phase TID sort fit in memory, or reserve up to ~5 GB.
4. **No additional heap-side reservation** beyond catch-up WAL. The 10 GB heap is read-only from the rebuild's standpoint.
5. **Bgwriter/checkpoint headroom**: WAL-logging the entire build adds checkpoint pressure during the run. This is a throughput concern, not a steady-state disk-size concern.

If the index lives in its own tablespace, the 2× rule applies to that tablespace only. If `temp_tablespaces` points elsewhere, the 5 GB sort-spill estimate moves to that filesystem.

## GUC Reload Semantics

These GUCs influence the reindex disk profile. All three are session-scoped, so no restart or reload is needed when set per session before the command:

- `maintenance_work_mem` is `PGC_USERSET`. Larger values reduce or eliminate the build-sort spill, at the cost of backend memory.
- `temp_tablespaces` is `PGC_USERSET` [[raw/postgres-12/src/backend/utils/misc/guc.c#temp_tablespaces|guc.c#temp_tablespaces]]. Set it to a tablespace with adequate space before running the reindex if the data tablespace is tight.
- `statement_timeout` and `lock_timeout` are `PGC_USERSET`. `REINDEX CONCURRENTLY` waits for lockers at multiple points, so a sensible `lock_timeout` keeps the command from blocking forever behind a long-running transaction.

`PGC_USERSET` means session or transaction `SET` needs no restart or reload; changing config-file or role/database defaults requires the normal reload path for new sessions.

## Production-Safe Pre-Flight Query

Verify free space before running the reindex. The following snippet uses session-scoped timeouts and an inline tag.

```sql
BEGIN /* wiki_pg12_reindex_concurrent_preflight */;
SET /* wiki_pg12_reindex_concurrent_preflight */ LOCAL statement_timeout = '30s';
SET /* wiki_pg12_reindex_concurrent_preflight */ LOCAL lock_timeout = '1s';

SELECT /* wiki_pg12_reindex_concurrent_preflight */
       n.nspname  AS schema_name,
       c.relname  AS index_name,
       pg_size_pretty(pg_relation_size(c.oid))                  AS index_size,
       pg_size_pretty(pg_relation_size(c.oid) * 2)              AS recommended_free_on_index_tablespace,
       pg_size_pretty(pg_relation_size(c.oid))                  AS recommended_free_on_pg_wal,
       coalesce(t.spcname, 'pg_default')                        AS index_tablespace
  FROM pg_class            c
  JOIN pg_namespace        n ON n.oid = c.relnamespace
  LEFT JOIN pg_tablespace  t ON t.oid = c.reltablespace
 WHERE c.relkind = 'i'
   AND c.relname = :'index_name'
   AND n.nspname = :'schema_name';

COMMIT /* wiki_pg12_reindex_concurrent_preflight */;
```

The `pg_relation_size()` here returns the main fork size of the index relation; the recommended free-space columns embed the 2× and 1× rules from the sizing recipe above.

## Failure And Cleanup

If the run aborts after phase 1 but before phase 6, the catalog can keep an `INVALID` `_ccnew` (or `_ccold` after a later-phase abort) that continues to consume disk space. `index_concurrently_swap()` explicitly toggles `indisvalid` on both rows during phase 4 [[raw/postgres-12/src/backend/catalog/index.c#index_concurrently_swap|index.c#L1531-L1537]]. A reindex runbook should:

1. List leftover `_ccnew` and `_ccold` indexes with `pg_index.indisvalid = false`.
2. Drop them explicitly with `DROP INDEX CONCURRENTLY` once the failure cause is understood.

`REINDEX CONCURRENTLY` itself cannot be run on a partitioned table parent in PG 12; an attempted run logs a `WARNING` and skips it [[raw/postgres-12/src/backend/commands/indexcmds.c#ReindexRelationConcurrently|indexcmds.c#L2917-L2923]]. Run the command per partition instead.

## Context Reviewed

- `wiki/versions.md` to confirm PG 12 source pin `45b88269...` and legacy status.
- `wiki/v12/index.md` to fit the page into existing coverage.
- `wiki/log.md` recent entries to follow current filing conventions.
- Pinned source under `raw/postgres-12/` via `scripts/source_graph_query --version 12`.

## Evidence Map

- Six-phase orchestration: [[raw/postgres-12/src/backend/commands/indexcmds.c#ReindexRelationConcurrently|indexcmds.c#ReindexRelationConcurrently]] (`L2941-L2955` enumerates phases; `L3296-L3329` performs the drop).
- New index in old index's tablespace: `index_concurrently_create_copy` passes `indexRelation->rd_rel->reltablespace` and `INDEX_CREATE_SKIP_BUILD | INDEX_CREATE_CONCURRENT` to `index_create()` [[raw/postgres-12/src/backend/catalog/index.c#index_concurrently_create_copy|index.c#index_concurrently_create_copy]].
- Concurrent build entry point: [[raw/postgres-12/src/backend/catalog/index.c#index_concurrently_build|index.c#index_concurrently_build]].
- B-tree page write and WAL: [[raw/postgres-12/src/backend/access/nbtree/nbtsort.c#_bt_blwritepage|nbtsort.c#_bt_blwritepage]] (calls `log_newpage` when `btws_use_wal` is true; `btws_use_wal = XLogIsNeeded() && RelationNeedsWAL(...)` set in [[raw/postgres-12/src/backend/access/nbtree/nbtsort.c#_bt_leafbuild|nbtsort.c#L580]]).
- B-tree sort flow: `btbuild()` → `_bt_spools_heapscan()` → `_bt_leafbuild()` → `tuplesort_performsort()` → `_bt_load()` [[raw/postgres-12/src/backend/access/nbtree/nbtsort.c#btbuild|nbtsort.c#btbuild]], [[raw/postgres-12/src/backend/access/nbtree/nbtsort.c#_bt_leafbuild|nbtsort.c#_bt_leafbuild]], [[raw/postgres-12/src/backend/access/nbtree/nbtsort.c#_bt_load|nbtsort.c#_bt_load]].
- Catch-up: `validate_index()` rescans heap, sorts TIDs with `maintenance_work_mem`, inserts missed tuples [[raw/postgres-12/src/backend/catalog/index.c#validate_index|index.c#validate_index]].
- Swap and dead-mark: [[raw/postgres-12/src/backend/catalog/index.c#index_concurrently_swap|index.c#index_concurrently_swap]] sets `indisvalid` on both rows.
- `temp_tablespaces` is `PGC_USERSET` [[raw/postgres-12/src/backend/utils/misc/guc.c#temp_tablespaces|guc.c#temp_tablespaces]].
- Partitioned-table parent unsupported: [[raw/postgres-12/src/backend/commands/indexcmds.c#ReindexRelationConcurrently|indexcmds.c#L2917-L2923]].

## Open Questions

- The new B-tree's post-rebuild size can be smaller than the original 5 GB on a previously bloated index. The "≈5 GB" used throughout the page is a worst-case "same size as old" assumption, not a source-derived guarantee. The actual final size depends on tuple density and page-fill behavior during `_bt_load()`.
- For non-B-tree access methods (GIN, GiST, BRIN, hash) the build path differs and the WAL volume and temp-spill behavior may diverge from the figures above. The numbers in this page are verified for the B-tree path only; the question wording did not specify an access method, so a B-tree assumption is applied.
- Catch-up index growth in phase 3 is bounded by the table's write rate during the build window, not by a constant. A precise bound for a specific workload would need write-rate measurement that is outside the scope of this page.
- The exact incremental WAL accounting under `wal_compression`, `wal_init_zero`, and `wal_recycle` is not analyzed here. The "≈ index size" WAL estimate assumes uncompressed `log_newpage` records on a typical configuration.
