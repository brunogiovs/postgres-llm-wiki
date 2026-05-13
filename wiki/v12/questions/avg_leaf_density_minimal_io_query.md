---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Estimate avg_leaf_density with Minimal I/O (unverified)

## Answer

In PostgreSQL 12, exact `avg_leaf_density` is the `pgstattuple` extension's `pgstatindex()` result. It is not minimal I/O: `pgstatindex_impl()` opens a btree index, reads block 0 as the metapage, then loops from block 1 to `RelationGetNumberOfBlocks(rel) - 1` and reads each block before computing the aggregate leaf density [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]].

For minimal I/O, treat the value as an estimate. The source-compatible approach is to sample a bounded number of btree leaf pages and reuse the same per-page formula as `pgstatindex()`:

```text
avg_leaf_density = 100.0 - sampled_free_space / sampled_max_avail * 100.0
```

`pgstatindex_impl()` adds `PageGetFreeSpace(page)` to `free_space`, adds `BLCKSZ - (BLCKSZ - pd_special + SizeOfPageHeaderData)` to `max_avail`, counts only normal leaf pages, and returns `NaN` when no leaf-page denominator exists [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]]. This makes sampling a change in coverage, not a change in the density definition.

## Recommended Paths

### Exact but Full-Scan

Use `pgstatindex(index_oid_or_name)` when the exact value matters more than I/O. PostgreSQL 12 exposes `avg_leaf_density` and `leaf_fragmentation` in the `pgstattuple` extension SQL definitions [[raw/postgres-12/contrib/pgstattuple/pgstattuple--1.4--1.5.sql#pgstatindex_regclass]]. The regression test calls `pgstatindex()` on text, name, and regclass inputs and checks the returned density columns [[raw/postgres-12/contrib/pgstattuple/sql/pgstattuple.sql#pgstatindex_tests]].

### Best Minimal-I/O Shape: Small C Function

A small C function can sample blocks with the same primitives as `pgstatindex()`:

```c
BufferAccessStrategy bstrategy = GetAccessStrategy(BAS_BULKREAD);

for (blkno = first_sampled_block; blkno < nblocks; blkno += step)
{
    Buffer buffer = ReadBufferExtended(rel, MAIN_FORKNUM, blkno,
                                       RBM_NORMAL, bstrategy);
    LockBuffer(buffer, BUFFER_LOCK_SHARE);

    page = BufferGetPage(buffer);
    opaque = (BTPageOpaque) PageGetSpecialPointer(page);

    if (!P_ISDELETED(opaque) && !P_IGNORE(opaque) && P_ISLEAF(opaque))
    {
        max_avail += BLCKSZ -
            (BLCKSZ - ((PageHeader) page)->pd_special + SizeOfPageHeaderData);
        free_space += PageGetFreeSpace(page);
        sampled_leaf_pages++;
    }

    LockBuffer(buffer, BUFFER_LOCK_UNLOCK);
    ReleaseBuffer(buffer);
}
```

This is only a skeleton. A filed extension still needs PostgreSQL extension boilerplate, `get_call_result_type()` handling, relation-close cleanup on every error path, a real btree access-method check, and tests. The relevant source pattern is `pgstatindex_impl()` itself: it uses `GetAccessStrategy(BAS_BULKREAD)`, `ReadBufferExtended()`, `BUFFER_LOCK_SHARE`, `PageGetSpecialPointer()`, and the density formula above [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]].

`BAS_BULKREAD` is a large read-only scan strategy, not a private temporary-buffer mechanism [[raw/postgres-12/src/include/storage/bufmgr.h#BufferAccessStrategyType]]. PostgreSQL implements it as backend-private state for a ring of shared buffers, and PG12 chooses a 256KB ring for `BAS_BULKREAD`, capped at one eighth of shared buffers [[raw/postgres-12/src/backend/storage/buffer/freelist.c#GetAccessStrategy]]. The buffer README describes this ring as a way to avoid blowing out the whole buffer cache during scans [[raw/postgres-12/src/backend/storage/buffer/README#buffer_ring_strategy]].

### SQL Estimate with pageinspect

If `pageinspect` is available, SQL can sample page numbers and call `bt_page_stats()` for those blocks. This is an estimate, not a byte-for-byte `pgstatindex()` clone, because PostgreSQL 12's SQL signature exposes `free_size` and `page_size` but not the internal `max_avail` field [[raw/postgres-12/contrib/pageinspect/pageinspect--1.5.sql#bt_page_stats]]. The C implementation computes `stat.max_avail`, but the result tuple omits it [[raw/postgres-12/contrib/pageinspect/btreefuncs.c#bt_page_stats]].

Recommended session-scoped safety settings:

```sql
SET /* wiki_estimate_avg_leaf_density_statement_timeout */ statement_timeout = '30s';
SET /* wiki_estimate_avg_leaf_density_lock_timeout */ lock_timeout = '2s';
```

Both settings are `PGC_USERSET` in PostgreSQL 12, so `SET` applies in the current session, `SET LOCAL` would apply in the current transaction, and neither needs reload or restart [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout]] [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout]] [[raw/postgres-12/src/include/utils/guc.h#GucContext]].

Sampling query:

```sql
SELECT /* wiki_estimate_avg_leaf_density */
       p.index_name,
       p.total_blocks,
       count(*) FILTER (WHERE s.type = 'l') AS sampled_leaf_pages,
       count(*) FILTER (WHERE s.type <> 'l') AS sampled_non_leaf_pages,
       round(
           100.0
           - (sum(s.free_size) FILTER (WHERE s.type = 'l'))::numeric
             / NULLIF((sum(s.page_size) FILTER (WHERE s.type = 'l'))::numeric, 0)
             * 100.0,
           2
       ) AS estimated_leaf_density_page_denominator_pct
FROM (
    SELECT c.oid AS index_oid,
           c.oid::regclass::text AS index_name,
           greatest(
               0,
               (pg_relation_size(c.oid) / current_setting('block_size')::int)::int
           ) AS total_blocks,
           128 AS requested_sample_pages
    FROM pg_class AS c
    JOIN pg_am AS am ON am.oid = c.relam
    WHERE c.oid = 'your_schema.your_index'::regclass
      AND c.relkind = 'i'
      AND am.amname = 'btree'
) AS p
CROSS JOIN LATERAL generate_series(
    1,
    least(p.requested_sample_pages, greatest(p.total_blocks - 1, 0))
) AS g(sample_no)
CROSS JOIN LATERAL (
    SELECT DISTINCT
           1 + floor(
               (p.total_blocks - 1)::numeric
               * (g.sample_no - 0.5)
               / least(p.requested_sample_pages, greatest(p.total_blocks - 1, 1))
           )::int AS blkno
) AS b
CROSS JOIN LATERAL bt_page_stats(p.index_name, b.blkno) AS s
GROUP BY p.index_name, p.total_blocks;
```

This query samples block numbers from `1` through `total_blocks - 1` because btree block 0 is the metapage. `bt_page_stats()` rejects block 0 with `ERROR: block 0 is a meta page`, and it rejects out-of-range blocks [[raw/postgres-12/contrib/pageinspect/btreefuncs.c#bt_page_stats]]. The pageinspect regression test covers those two errors and a successful leaf-page call [[raw/postgres-12/contrib/pageinspect/expected/btree.out#bt_page_stats_output]].

The SQL query uses `pg_relation_size(index_oid)` instead of `pg_class.relpages` so the block count comes from the current main-fork file size. PG12's one-argument `pg_relation_size(regclass)` is a SQL wrapper for `pg_relation_size($1, 'main')`, and the C function opens the relation with `AccessShareLock` before calculating the relation fork size [[raw/postgres-12/src/include/catalog/pg_proc.dat#pg_relation_size]] [[raw/postgres-12/src/backend/utils/adt/dbsize.c#pg_relation_size]].

## Why Plain Catalog Math Is Not Enough

`pg_class.relpages` and fillfactor can describe a model, not actual btree leaf density. The catalog has `relpages`, `relam`, and `relkind` fields [[raw/postgres-12/src/include/catalog/pg_class.h#FormData_pg_class]], and btree fillfactor defaults to 90 for leaf pages [[raw/postgres-12/src/include/access/nbtree.h#BTREE_DEFAULT_FILLFACTOR]]. Those facts do not expose per-page `free_space`. Actual density depends on each sampled page's `PageGetFreeSpace(page)` result [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageGetFreeSpace]].

Fillfactor is still useful context. PG12 documents that btree leaf fillfactor defaults to 90, is user-adjustable, applies during index build and rightmost-page splits, and differs from the fixed 70 percent non-leaf fillfactor [[raw/postgres-12/src/include/access/nbtree.h#btree_fillfactor]]. The reloptions table registers btree `fillfactor` as a reloption from 10 to 100 with default `BTREE_DEFAULT_FILLFACTOR` [[raw/postgres-12/src/backend/access/common/reloptions.c#btree_fillfactor_reloption]].

## Partial Indexes

Partial indexes do not need a different page-density formula. On insert, `ExecInsertIndexTuples()` evaluates `ii_Predicate`; if the predicate is false, it skips that index update, and if true it forms the index datum and calls `index_insert()` [[raw/postgres-12/src/backend/executor/execIndexing.c#ExecInsertIndexTuples]]. During index validation/exclusion checking, PostgreSQL also ignores heap tuples that do not satisfy the partial-index predicate [[raw/postgres-12/src/backend/catalog/index.c#IndexCheckExclusion]].

The inference is direct: tuples that fail the predicate do not become index tuples, so btree leaf pages still contain ordinary btree tuples. The density calculation still depends on btree page layout and free space, not on the predicate text. The key page structures are `BTPageOpaqueData`, which stores sibling links, level, and flags, and `PageHeaderData`, which stores `pd_lower`, `pd_upper`, and `pd_special` [[raw/postgres-12/src/include/access/nbtree.h#BTPageOpaqueData]] [[raw/postgres-12/src/include/storage/bufpage.h#PageHeaderData]].

## Edge Cases

- Empty indexes can produce no leaf-page denominator. `pgstatindex_impl()` returns `NaN` for `avg_leaf_density` when `indexStat.max_avail` is zero [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]].
- `pgstatindex_impl()` rejects relations that are not ordinary btree indexes and rejects non-local temporary relations [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]].
- `bt_page_stats()` requires a btree index, rejects non-local temporary relations, rejects block 0, and checks that the requested block is in range [[raw/postgres-12/contrib/pageinspect/btreefuncs.c#bt_page_stats]].
- Deleted pages and half-dead pages are not counted as leaf density inputs by `pgstatindex_impl()`: deleted pages increment `deleted_pages`, `P_IGNORE()` pages increment `empty_pages`, and only normal leaf pages add to `free_space` and `max_avail` [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]].
- A SQL `pageinspect` estimate reads exactly the sampled page numbers, but `bt_page_stats()` uses `ReadBuffer()` rather than the `BAS_BULKREAD` strategy used by `pgstatindex_impl()` [[raw/postgres-12/contrib/pageinspect/btreefuncs.c#bt_page_stats]] [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]].

## Context Reviewed

- `contrib/pgstattuple/pgstatindex.c`: exact full-scan implementation, page classification, density formula, and edge cases.
- `contrib/pgstattuple/pgstattuple--1.4--1.5.sql`: SQL-visible `pgstatindex()` result columns and execution grants.
- `contrib/pageinspect/btreefuncs.c` and `pageinspect--1.5.sql`: page-level btree inspection function and its SQL-visible columns.
- `src/include/access/nbtree.h`: btree page opaque data, page flags, metapage data, and fillfactor constants.
- `src/include/storage/bufpage.h` and `src/backend/storage/page/bufpage.c`: page header layout, special-space access, and `PageGetFreeSpace()`.
- `src/backend/storage/buffer/freelist.c`, `src/include/storage/bufmgr.h`, and `src/backend/storage/buffer/README`: bulk-read buffer strategy behavior.
- `src/backend/executor/execIndexing.c` and `src/backend/catalog/index.c`: partial-index predicate evaluation during index tuple insertion and validation.
- Regression tests under `contrib/pgstattuple/sql/` and `contrib/pageinspect/sql/`.

## Evidence Map

| Claim | Evidence |
|---|---|
| Exact `avg_leaf_density` comes from `pgstatindex()` and requires a full page loop. | [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]] |
| `pgstatindex()` density uses `PageGetFreeSpace()` divided by accumulated `max_avail`. | [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]] |
| Normal leaf pages are counted; deleted, half-dead, and internal pages are classified separately. | [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]] |
| `BAS_BULKREAD` is a read-scan buffer strategy implemented with a small shared-buffer ring. | [[raw/postgres-12/src/include/storage/bufmgr.h#BufferAccessStrategyType]] [[raw/postgres-12/src/backend/storage/buffer/freelist.c#GetAccessStrategy]] [[raw/postgres-12/src/backend/storage/buffer/README#buffer_ring_strategy]] |
| `bt_page_stats()` exposes page type, free size, and page size, but not `max_avail`, to SQL. | [[raw/postgres-12/contrib/pageinspect/pageinspect--1.5.sql#bt_page_stats]] [[raw/postgres-12/contrib/pageinspect/btreefuncs.c#bt_page_stats]] |
| Partial-index predicates gate index tuple insertion before `index_insert()`. | [[raw/postgres-12/src/backend/executor/execIndexing.c#ExecInsertIndexTuples]] |
| Page layout and btree opaque fields are C-level structures. | [[raw/postgres-12/src/include/storage/bufpage.h#PageHeaderData]] [[raw/postgres-12/src/include/access/nbtree.h#BTPageOpaqueData]] |
| Recommended timeouts are session/transaction scoped because both are `PGC_USERSET`. | [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout]] [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout]] [[raw/postgres-12/src/include/utils/guc.h#GucContext]] |
| Tests cover `pgstatindex()` output columns and `bt_page_stats()` success/error paths, but not a sampling estimator. | [[raw/postgres-12/contrib/pgstattuple/sql/pgstattuple.sql#pgstatindex_tests]] [[raw/postgres-12/contrib/pageinspect/sql/btree.sql#btree_pageinspect_tests]] |

## Source References

- [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]]
- [[raw/postgres-12/contrib/pgstattuple/pgstattuple--1.4--1.5.sql#pgstatindex_regclass]]
- [[raw/postgres-12/contrib/pageinspect/btreefuncs.c#bt_page_stats]]
- [[raw/postgres-12/contrib/pageinspect/pageinspect--1.5.sql#bt_page_stats]]
- [[raw/postgres-12/src/include/access/nbtree.h#BTPageOpaqueData]]
- [[raw/postgres-12/src/include/storage/bufpage.h#PageHeaderData]]
- [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageGetFreeSpace]]
- [[raw/postgres-12/src/backend/utils/misc/guc.c#statement_timeout]]
- [[raw/postgres-12/src/backend/utils/misc/guc.c#lock_timeout]]
- [[raw/postgres-12/src/include/utils/guc.h#GucContext]]
- [[raw/postgres-12/src/backend/executor/execIndexing.c#ExecInsertIndexTuples]]
- [[raw/postgres-12/contrib/pgstattuple/sql/pgstattuple.sql#pgstatindex_tests]]
- [[raw/postgres-12/contrib/pageinspect/sql/btree.sql#btree_pageinspect_tests]]

## Open Questions

- The SQL estimator above uses `page_size` as the denominator because PG12 `bt_page_stats()` does not expose `max_avail`. This is useful for low-I/O trend checks, but it is not the exact `pgstatindex()` formula.
- A production C extension should be compiled and regression-tested against PostgreSQL 12 server headers before this page presents it as complete code.
- Sampling accuracy depends on page-density distribution. Periodic or localized fragmentation can bias systematic samples. A random-start systematic sample or random sample should be validated against full `pgstatindex()` runs on representative indexes.
