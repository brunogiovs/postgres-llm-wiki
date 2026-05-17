---
type: question
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: false
verified_by_agent: not yet
---

# Computing and Storing avg_leaf_density During (Auto)VACUUM of a B-Tree Index (unverified)

**Answer up front.** A B-tree VACUUM already reads and cleanup-locks *every* leaf
page in physical order, so `avg_leaf_density` can be computed for free by
accumulating two running sums inside the existing leaf branch of `btvacuumpage`:
the post-compaction free space (`PageGetExactFreeSpace`) and the per-leaf usable
space. No page is read a second time and no extra page is dirtied for the
computation itself. The cheapest durable place to *store* the result is the
B-tree metapage, because `btvacuumcleanup` already writes and WAL-logs the
metapage once per VACUUM through `_bt_set_cleanup_info`; adding one `float4`
field there piggybacks on a write that already happens. A queryable copy can
also be pushed into the cumulative statistics system from the same call site
(shared-memory write, flushed later, zero VACUUM-time disk I/O). The only real
limitation is that VACUUM can legitimately skip the index scan entirely, in
which case the stored value must be left untouched (it describes the last scan,
not "now").

## Question

> in PostgreSQL 18, create a detailed analysis on how to modify vacuum and
> autovacuum to calculate avg_leaf_density for an index like pgstatindex and
> store it the a stat table, so after each successful vacuum or autovacuum of
> an index the information would be available, this solution should minimize to
> the max any extra I/O so the calculation should try to use all the current
> data during the vacuum to calculate the avg_leaf_density

## What avg_leaf_density Is

`pgstatindex` defines it as the percentage of *usable* leaf-page space that is
actually occupied, averaged over all leaf pages:

- For each leaf page it adds `max_avail = BLCKSZ - (BLCKSZ - pd_special + SizeOfPageHeaderData)`
  and `free_space = PageGetExactFreeSpace(page)`
  ([[raw/postgres-18/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#pgstatindex_impl]]).
- The reported figure is `100.0 - free_space / max_avail * 100.0`, or `NaN` when
  there are no leaf pages
  ([[raw/postgres-18/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#pgstatindex_impl]]).

The `max_avail` expression algebraically reduces to
`pd_special - SizeOfPageHeaderData`. `SizeOfPageHeaderData` is
`offsetof(PageHeaderData, pd_linp)`
([[raw/postgres-18/src/include/storage/bufpage.h#SizeOfPageHeaderData|bufpage.h#SizeOfPageHeaderData]]),
and for a B-tree leaf page `pd_special = BLCKSZ - MAXALIGN(sizeof(BTPageOpaqueData))`.
So `max_avail` is the **same constant** for every leaf page in a given build:

```
C = BLCKSZ - SizeOfPageHeaderData - MAXALIGN(sizeof(BTPageOpaqueData))
```

`free_space` is exactly `pd_upper - pd_lower`
([[raw/postgres-18/src/backend/storage/page/bufpage.c#PageGetExactFreeSpace|bufpage.c#PageGetExactFreeSpace]]).

Therefore the whole statistic needs only two scalars per index:

```
nleaf            = number of live leaf pages visited
sum_free_space   = Σ (pd_upper - pd_lower) over those leaf pages
avg_leaf_density = 100.0 * (1.0 - sum_free_space / (nleaf * C))   -- NaN if nleaf == 0
```

Accumulating `max_avail` per page (instead of `nleaf * C`) keeps byte-for-byte
parity with `pgstatindex` and is robust if the constant ever varies; the cost
is identical.

## Why VACUUM Is the Zero-Extra-I/O Place

`pgstatindex` exists only because, outside VACUUM, there is no other moment when
every leaf page is already in hand. A B-tree VACUUM removes that objection:

- `btbulkdelete` and `btvacuumcleanup` both funnel into `btvacuumscan`
  ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btbulkdelete|nbtree.c#btbulkdelete]],
  [[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumcleanup|nbtree.c#btvacuumcleanup]]).
- `btvacuumscan` walks **all** blocks except the metapage in physical order via
  a maintenance read stream and calls `btvacuumpage` on each
  ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#btvacuumscan]]).
- `btvacuumpage` takes a cleanup lock on every live leaf page "whether or not it
  actually contains any deletable tuples" and then has the page pointer in hand
  ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumpage|nbtree.c#btvacuumpage]]).

So the bytes `pgstatindex` would read are *already* pinned, locked, and CPU-cache
hot during VACUUM. Computing the two sums there adds a subtraction and two adds
per leaf page and no I/O at all.

## The Computation: Where to Hook In

### 1. Carry accumulators in `BTVacState`

`BTVacState` is the per-scan private state already threaded through
`btvacuumscan` -> `btvacuumpage`
([[raw/postgres-18/src/include/access/nbtree.h#BTVacState|nbtree.h#BTVacState]]).
Add three fields:

```c
/* avg_leaf_density accumulators (whole-index, reset per btvacuumscan) */
uint64   nleaf;            /* live leaf pages visited */
uint64   sum_free_space;   /* Σ PageGetExactFreeSpace over those leaves */
uint64   sum_max_avail;    /* Σ per-leaf usable space (== nleaf * C) */
```

Zero them next to the existing `stats->num_pages = 0; ...` resets at the top of
`btvacuumscan`, so a multi-pass VACUUM that calls `btvacuumscan` more than once
does not double-count
([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#btvacuumscan]]).

### 2. Accumulate in the `P_ISLEAF` branch of `btvacuumpage`, *after* compaction

`btvacuumpage` classifies the page. Recyclable, already-deleted, half-dead, and
internal pages are handled in earlier branches; the `else if (P_ISLEAF(opaque))`
branch is reached for exactly the live leaf pages `pgstatindex` counts
([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumpage|nbtree.c#btvacuumpage]]).
Inside that branch, `_bt_delitems_vacuum` may delete/compact items and `maxoff`
is recomputed afterward
([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumpage|nbtree.c#btvacuumpage]]).
Place the accumulation **after** the `if (ndeletable > 0 || nupdatable > 0)`
apply block and after the empty-page `attempt_pagedel` decision, so the measured
free space reflects the **post-VACUUM** page, which is the state the user wants
"after a successful vacuum":

```c
/* after _bt_delitems_vacuum has run and maxoff was recomputed */
if (!attempt_pagedel)            /* page survives this VACUUM as a leaf */
{
    Size max_avail = ((PageHeader) page)->pd_special - SizeOfPageHeaderData;

    vstate->nleaf++;
    vstate->sum_free_space += PageGetExactFreeSpace(page);
    vstate->sum_max_avail  += max_avail;
}
```

Skipping pages that go on to `attempt_pagedel` matches `pgstatindex`, which
never counts deleted/half-dead pages as leaves
([[raw/postgres-18/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#pgstatindex_impl]]).
This branch also runs in the cleanup-only path (`callback == NULL`), so the
statistic is still produced when `btvacuumcleanup` triggers a scan
([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumcleanup|nbtree.c#btvacuumcleanup]]).

### 3. Derive the final figure at the end of `btvacuumscan`

After the page loop, where `stats->num_pages` is finalized
([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#btvacuumscan]]),
compute:

```c
float4 avg_leaf_density =
    (vstate.nleaf == 0)
      ? -1.0f                                         /* sentinel for NaN */
      : 100.0 * (1.0 - (double) vstate.sum_free_space
                            / (double) vstate.sum_max_avail);
```

Use a sentinel (e.g. `-1`) for the "no leaf pages" case so a single numeric
column can represent `pgstatindex`'s `NaN`.

## Where to Store It (the "stat table")

Two complementary targets, chosen for minimal extra I/O.

### Option A (recommended, durable, ~zero added I/O): the B-tree metapage

`btvacuumcleanup` already calls `_bt_set_cleanup_info`, which reads the metapage,
**conditionally takes a write lock, dirties it, and emits an
`xl_btree_metadata` WAL record** to maintain `btm_last_cleanup_num_delpages`
([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumcleanup|nbtree.c#btvacuumcleanup]],
[[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_set_cleanup_info|nbtpage.c#_bt_set_cleanup_info]]).
That write already happens once per VACUUM that scans the index. Add the density
to the same write:

1. Add `float4 btm_last_avg_leaf_density;` to `BTMetaPageData`, after the
   existing cleanup fields
   ([[raw/postgres-18/src/include/access/nbtree.h#BTMetaPageData|nbtree.h#BTMetaPageData]]).
2. Add the matching field to `xl_btree_metadata`
   ([[raw/postgres-18/src/include/access/nbtxlog.h#xl_btree_metadata|nbtxlog.h#xl_btree_metadata]])
   and set/restore it in `_bt_restore_meta`
   ([[raw/postgres-18/src/backend/access/nbtree/nbtxlog.c#_bt_restore_meta|nbtxlog.c#_bt_restore_meta]]).
3. Pass the value into `_bt_set_cleanup_info` and store it there, reusing the
   *existing* `MarkBufferDirty` + WAL path; only widen the early-return
   "nothing changed" guard to also compare the density
   ([[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_set_cleanup_info|nbtpage.c#_bt_set_cleanup_info]]).
4. Initialize the field on metapage upgrade/rewrite, the same way
   `btm_last_cleanup_num_heap_tuples` is set to `-1.0`
   ([[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_set_cleanup_info|nbtpage.c#_bt_set_cleanup_info]],
   [[raw/postgres-18/src/backend/access/nbtree/nbtxlog.c#_bt_restore_meta|nbtxlog.c#_bt_restore_meta]]).

Incremental I/O cost: **zero extra page reads** and **zero extra dirtied
pages/WAL records** in the common case, because the metapage write is already
performed by `_bt_set_cleanup_info`. The only edge case is an index where
`num_delpages` did not change *and* nothing else forced the metapage write; the
widened guard then converts a skipped write into one metapage write + one small
WAL record per VACUUM. This mirrors exactly how `num_delpages` is already
persisted, and on-disk compatibility is handled the same way (the field is only
valid for `btm_version >= BTREE_NOVAC_VERSION`; older metapages upgrade in place)
([[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_set_cleanup_info|nbtpage.c#_bt_set_cleanup_info]]).

To expose it, add a contrib function or `pageinspect`-style accessor that reads
the metapage field, or surface it through Option B.

### Option B (queryable, no VACUUM-time disk I/O): cumulative statistics

The "stat table" users normally query is the cumulative statistics system. Index
entries already live there under `PGSTAT_KIND_RELATION`, keyed by the index
relid, exposed via `pg_stat_all_indexes`
([[raw/postgres-18/src/backend/utils/activity/pgstat_relation.c#pgstat_report_vacuum|pgstat_relation.c#pgstat_report_vacuum]]).
Plan:

1. Add `PgStat_Counter` / `float` `avg_leaf_density` (plus a
   `density_stats_valid` flag, or use a sentinel) to `PgStat_StatTabEntry`
   ([[raw/postgres-18/src/include/pgstat.h#PgStat_StatTabEntry|pgstat.h#PgStat_StatTabEntry]]).
   It is meaningful only for B-tree index entries; it stays at the sentinel for
   tables and other AMs.
2. Return the value out of the AM. `IndexBulkDeleteResult` is the AM-to-VACUUM
   contract
   ([[raw/postgres-18/src/include/access/genam.h#IndexBulkDeleteResult|genam.h#IndexBulkDeleteResult]]);
   add `float4 avg_leaf_density;` to it and set it from the `btvacuumscan`
   computation. Both `btbulkdelete` and `btvacuumcleanup` already return this
   struct
   ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btbulkdelete|nbtree.c#btbulkdelete]],
   [[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumcleanup|nbtree.c#btvacuumcleanup]]).
3. Report it from VACUUM. The struct surfaces in
   `lazy_vacuum_one_index`/`lazy_cleanup_one_index`
   ([[raw/postgres-18/src/backend/access/heap/vacuumlazy.c#lazy_cleanup_one_index|vacuumlazy.c#lazy_cleanup_one_index]])
   and is retained in `vacrel->indstats`. Add a per-index reporter modeled on
   `pgstat_report_vacuum`, which takes a locked shared entry, writes fields, and
   unlocks — an in-memory shared-hashtable update, **not** a disk write
   ([[raw/postgres-18/src/backend/utils/activity/pgstat_relation.c#pgstat_report_vacuum|pgstat_relation.c#pgstat_report_vacuum]]).
   Stats are flushed to `pg_stat` files lazily/at shutdown, off the VACUUM I/O
   path.
4. Expose it as a new column in the `pg_stat_all_indexes` view and a
   `pg_stat_get_*` accessor
   ([[raw/postgres-18/src/backend/catalog/system_views.sql#pg_statio_all_indexes|system_views.sql]]).

Autovacuum needs no separate change: autovacuum workers run the same
`vacuumlazy.c` -> `index_bulk_delete`/`index_vacuum_cleanup` ->
`btbulkdelete`/`btvacuumcleanup` path, and `pgstat_report_vacuum` already
distinguishes the autovacuum worker via `AmAutoVacuumWorkerProcess()`
([[raw/postgres-18/src/backend/utils/activity/pgstat_relation.c#pgstat_report_vacuum|pgstat_relation.c#pgstat_report_vacuum]]).

### Recommendation

Do **both**: metapage as the durable source of truth (it survives crash/restart
and replicates via WAL with no added I/O), cumulative stats as the cheap
queryable surface. If only one is wanted, the metapage alone fully satisfies
"available after each successful vacuum" with the least I/O and the strongest
durability, at the cost of needing an accessor function to read it.

| Aspect | Metapage (A) | Cumulative stats (B) |
|---|---|---|
| Extra read I/O during VACUUM | none | none |
| Extra write I/O during VACUUM | none in common case (write already happens) | none (shared memory; flushed later) |
| Durable across crash/restart | yes (WAL-logged) | best-effort (stats file; reset on crash) |
| Directly queryable | needs accessor function | yes, via `pg_stat_all_indexes` |
| Replicated to standbys | yes | no |

## When the Value Will *Not* Refresh (coverage caveats)

The figure describes the **last index scan**, not the live index. VACUUM can
correctly skip the B-tree scan:

- `btvacuumcleanup` returns `NULL` without scanning when there was no
  `btbulkdelete` and `_bt_vacuum_needs_cleanup` is false (the common
  no-dead-tuples, few-deleted-pages case)
  ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumcleanup|nbtree.c#btvacuumcleanup]],
  [[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_vacuum_needs_cleanup|nbtpage.c#_bt_vacuum_needs_cleanup]]).
- VACUUM skips index vacuuming entirely under `INDEX_CLEANUP off` or when the
  wraparound failsafe is active (handled in `vacuumlazy.c`).

In all of these, `stats` is `NULL` or unscanned, so **leave the stored density
unchanged** and keep its previous timestamp/value. Do not write a zero or a
stale recomputation. Document that the field reflects the most recent scan and
pair it with a "last computed" timestamp (the metapage LSN, or the existing
`last_vacuum_time`/`last_autovacuum_time` in `PgStat_StatTabEntry`) so consumers
can judge staleness
([[raw/postgres-18/src/include/pgstat.h#PgStat_StatTabEntry|pgstat.h#PgStat_StatTabEntry]]).

## Accuracy Notes

- The figure is post-compaction within this VACUUM, so it reflects the index as
  VACUUM leaves it, which is the desired semantic.
- Concurrent page splits can make `btvacuumscan` visit a moved page twice; this
  is the same known double-counting class already acknowledged for
  `num_index_tuples`
  ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumcleanup|nbtree.c#btvacuumcleanup]]).
  The density error from this is bounded and no worse than the existing tuple
  estimate, so treating it as an estimate (like `estimated_count`) is
  consistent.
- The backtrack path in `btvacuumpage` re-reads a sibling block but the
  `btpo_cycleid`/`P_ISDELETED` early-return guard prevents reprocessing a page
  already handled, so accumulation stays once-per-live-leaf
  ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumpage|nbtree.c#btvacuumpage]]).

## Minimal Change List

1. `BTVacState`: add `nleaf`, `sum_free_space`, `sum_max_avail`
   ([[raw/postgres-18/src/include/access/nbtree.h#BTVacState|nbtree.h#BTVacState]]).
2. `btvacuumscan`: zero them with the other resets; derive `avg_leaf_density`
   after the page loop
   ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#btvacuumscan]]).
3. `btvacuumpage`: accumulate in the `P_ISLEAF` branch after compaction
   ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumpage|nbtree.c#btvacuumpage]]).
4. `IndexBulkDeleteResult`: add `avg_leaf_density`
   ([[raw/postgres-18/src/include/access/genam.h#IndexBulkDeleteResult|genam.h#IndexBulkDeleteResult]]).
5. Metapage path: extend `BTMetaPageData`, `xl_btree_metadata`,
   `_bt_set_cleanup_info`, `_bt_restore_meta`
   ([[raw/postgres-18/src/include/access/nbtree.h#BTMetaPageData|nbtree.h#BTMetaPageData]],
   [[raw/postgres-18/src/include/access/nbtxlog.h#xl_btree_metadata|nbtxlog.h#xl_btree_metadata]],
   [[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_set_cleanup_info|nbtpage.c#_bt_set_cleanup_info]],
   [[raw/postgres-18/src/backend/access/nbtree/nbtxlog.c#_bt_restore_meta|nbtxlog.c#_bt_restore_meta]]).
6. Stats path: extend `PgStat_StatTabEntry`, add a reporter beside
   `pgstat_report_vacuum`, call it from `lazy_*_one_index`, add a view column
   ([[raw/postgres-18/src/include/pgstat.h#PgStat_StatTabEntry|pgstat.h#PgStat_StatTabEntry]],
   [[raw/postgres-18/src/backend/utils/activity/pgstat_relation.c#pgstat_report_vacuum|pgstat_relation.c#pgstat_report_vacuum]],
   [[raw/postgres-18/src/backend/access/heap/vacuumlazy.c#lazy_cleanup_one_index|vacuumlazy.c#lazy_cleanup_one_index]]).
7. No autovacuum-specific change: the autovacuum worker uses the same path and
   is already distinguished by `AmAutoVacuumWorkerProcess()`
   ([[raw/postgres-18/src/backend/utils/activity/pgstat_relation.c#pgstat_report_vacuum|pgstat_relation.c#pgstat_report_vacuum]]).

## Context Reviewed

- B-tree VACUUM driver and per-page handler: `btbulkdelete`,
  `btvacuumcleanup`, `btvacuumscan`, `btvacuumpage`
  ([[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#btvacuumscan]]).
- Metapage maintenance and WAL: `_bt_set_cleanup_info`,
  `_bt_vacuum_needs_cleanup`, `_bt_restore_meta`, `BTMetaPageData`,
  `xl_btree_metadata`.
- VACUUM/index boundary: `lazy_vacuum_one_index`, `lazy_cleanup_one_index`,
  `vac_bulkdel_one_index`, `vac_cleanup_one_index`, `IndexVacuumInfo`,
  `IndexBulkDeleteResult`.
- Statistics surface: `pgstat_report_vacuum`, `PgStat_StatTabEntry`,
  `PGSTAT_KIND_RELATION`, `pg_stat*_all_indexes` view definitions.
- Reference semantics: `pgstatindex_impl`, `PageGetExactFreeSpace`,
  `SizeOfPageHeaderData`.

## Evidence Map

| Claim | Source |
|---|---|
| `avg_leaf_density = 100 - free/max_avail*100`, NaN if no leaves | [[raw/postgres-18/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#pgstatindex_impl]] |
| Free space is `pd_upper - pd_lower` | [[raw/postgres-18/src/backend/storage/page/bufpage.c#PageGetExactFreeSpace|bufpage.c#PageGetExactFreeSpace]] |
| VACUUM visits every leaf under cleanup lock | [[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumpage|nbtree.c#btvacuumpage]], [[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#btvacuumscan]] |
| Metapage already written/WAL-logged at cleanup | [[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_set_cleanup_info|nbtpage.c#_bt_set_cleanup_info]] |
| Index scan can be skipped entirely | [[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumcleanup|nbtree.c#btvacuumcleanup]], [[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_vacuum_needs_cleanup|nbtpage.c#_bt_vacuum_needs_cleanup]] |
| Stats write is shared-memory, autovacuum-aware | [[raw/postgres-18/src/backend/utils/activity/pgstat_relation.c#pgstat_report_vacuum|pgstat_relation.c#pgstat_report_vacuum]] |
| AM result contract struct | [[raw/postgres-18/src/include/access/genam.h#IndexBulkDeleteResult|genam.h#IndexBulkDeleteResult]] |

## Source References

- [[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#btvacuumscan]] - whole-index VACUUM scan; reset point for accumulators and derivation site.
- [[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumpage|nbtree.c#btvacuumpage]] - per-page handler; `P_ISLEAF` branch is the accumulation point.
- [[raw/postgres-18/src/backend/access/nbtree/nbtree.c#btvacuumcleanup|nbtree.c#btvacuumcleanup]] - cleanup entry; skip-scan decision and metapage maintenance call.
- [[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_set_cleanup_info|nbtpage.c#_bt_set_cleanup_info]] - existing WAL-logged metapage write to piggyback on.
- [[raw/postgres-18/src/backend/access/nbtree/nbtpage.c#_bt_vacuum_needs_cleanup|nbtpage.c#_bt_vacuum_needs_cleanup]] - when the index scan is skipped entirely.
- [[raw/postgres-18/src/backend/access/nbtree/nbtxlog.c#_bt_restore_meta|nbtxlog.c#_bt_restore_meta]] - metapage WAL redo to extend.
- [[raw/postgres-18/src/include/access/nbtree.h#BTVacState|nbtree.h#BTVacState]], [[raw/postgres-18/src/include/access/nbtree.h#BTMetaPageData|nbtree.h#BTMetaPageData]] - structs to extend.
- [[raw/postgres-18/src/include/access/nbtxlog.h#xl_btree_metadata|nbtxlog.h#xl_btree_metadata]] - WAL record struct to extend.
- [[raw/postgres-18/src/include/access/genam.h#IndexBulkDeleteResult|genam.h#IndexBulkDeleteResult]] - AM-to-VACUUM result contract.
- [[raw/postgres-18/src/backend/access/heap/vacuumlazy.c#lazy_cleanup_one_index|vacuumlazy.c#lazy_cleanup_one_index]] - VACUUM/index boundary and stats reporting site.
- [[raw/postgres-18/src/backend/utils/activity/pgstat_relation.c#pgstat_report_vacuum|pgstat_relation.c#pgstat_report_vacuum]] - model for the cumulative-stats reporter.
- [[raw/postgres-18/src/include/pgstat.h#PgStat_StatTabEntry|pgstat.h#PgStat_StatTabEntry]] - cumulative stats entry to extend.
- [[raw/postgres-18/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#pgstatindex_impl]] - reference `avg_leaf_density` semantics.
- [[raw/postgres-18/src/backend/storage/page/bufpage.c#PageGetExactFreeSpace|bufpage.c#PageGetExactFreeSpace]] - free-space primitive used in the formula.

## Open Questions

- This page proposes a code modification, not a description of existing
  behavior. The accumulation/storage logic is designed from verified source but
  has not been compiled or runtime-verified; treat code snippets as design
  intent, not patches.
- Adding a B-tree-only `float4` to the shared `PgStat_StatTabEntry` wastes a
  few bytes per table entry. A separate `PGSTAT_KIND_*` for index physical
  stats, or a `pgstat`-variable-numbered stats entry, may be cleaner but was
  not traced here.
- WAL format change to `xl_btree_metadata` implies an `XLOG_PAGE_MAGIC` bump
  and pg_upgrade considerations; the upgrade-in-place mechanics were confirmed
  for the field-add pattern but the release-process impact was not assessed.
- Whether to expose the sentinel as SQL `NULL` vs `'NaN'::float` to match
  `pgstatindex` output exactly is a UI decision left open.
