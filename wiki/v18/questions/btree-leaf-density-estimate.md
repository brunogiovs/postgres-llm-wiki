---
type: question
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: false
verified_by_agent: not yet
---

# Btree Leaf Density Estimate Without `pgstatindex`

## Question

In PostgreSQL 18, propose a SQL with no additional dependencies that returns `avg_leaf_density` of a btree index like [[v18/code-paths/pgstatindex]] but minimizing I/O to the minimum to get a reasonably accurate leaf density. It must work well with partial indexes and support indexes with and without deduplication. Assume the primary version from [[versions]].

## Short Answer

Assume PostgreSQL 18, the primary version in [[versions]]. `pgstatindex` reads every non-meta block of the index under share lock to sum exact `max_avail` and `free_space` per leaf page; the input I/O is `O(relpages)`. Citations: `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:pgstatindex_impl`, `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:309`, `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:362`.

The minimum-I/O reformulation reads only `pg_catalog` (`pg_class`, `pg_index`, `pg_attribute`, `pg_stats`, `pg_am`) and reconstructs `avg_leaf_density` analytically from `pg_class.reltuples`, `pg_class.relpages`, the per-key average width from `pg_stats`, and a per-entry on-disk footprint computed from the `IndexTupleData` header, an optional null bitmap, and `MAXALIGN`. No index data pages are read. Partial indexes need no special handling because the post-VACUUM `pg_class.reltuples` for the index already reflects only entries inside the partial predicate, written by `btvacuumcleanup` / `btbulkdelete` through `IndexBulkDeleteResult.num_index_tuples`. Deduplication is detected via the `deduplicate_items` reloption; when active, the catalog estimate is treated as an upper bound on density because posting-list compression makes the on-disk byte count smaller than `reltuples * bytes_per_entry`. Citations: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:btvacuumcleanup`, `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1637`, `raw/postgres-18/src/include/access/nbtree.h:1155`, `raw/postgres-18/src/include/access/nbtree.h:1170`.

## What `pgstatindex` Actually Computes

`pgstatindex_impl` opens the index with `AccessShareLock`, reads block 0 as the metapage, then loops every other block under `BUFFER_LOCK_SHARE` via a `BAS_BULKREAD` strategy. For each leaf page it accumulates two byte ranges:

```c
max_avail = BLCKSZ - (BLCKSZ - ((PageHeader) page)->pd_special + SizeOfPageHeaderData);
indexStat.max_avail += max_avail;
indexStat.free_space += PageGetExactFreeSpace(page);
```

After the loop, density is derived as `100.0 - (double) free_space / (double) max_avail * 100.0`, returned as `'NaN'` when `max_avail == 0`. Citations: `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:309`, `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:311`, `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:362`.

`max_avail` simplifies to `pd_special - SizeOfPageHeaderData`, the byte range between the page header and the special area on a leaf page. With `BLCKSZ = 8192`, `SizeOfPageHeaderData = offsetof(PageHeaderData, pd_linp) = 24`, and `sizeof(BTPageOpaqueData) = 16`, this is `8192 - 24 - 16 = 8152` bytes per leaf. Citations: `raw/postgres-18/src/include/storage/bufpage.h:159`, `raw/postgres-18/src/include/storage/bufpage.h:218`, `raw/postgres-18/src/include/access/nbtree.h:63`.

The dominant cost is the per-block scan: every block of the index is read from shared buffers (or the OS page cache, or disk) and share-locked. The catalog-only estimate eliminates that scan in exchange for a small modeling error.

## Reconstructing The Density From The Catalog

The same identity rewritten over the whole index is `density = 100 * total_used_bytes / total_max_avail_bytes`. We approximate the numerator and denominator from catalog statistics:

- **Denominator.** `total_max_avail_bytes ≈ leaf_pages * 8152`. Internal pages and the metapage are excluded. For a typical btree fanout (≈200 with narrow keys), internal pages are <0.5% of `relpages`, so `(relpages - 1)` is a usable proxy for `leaf_pages` with sub-percent error. `relpages` is maintained on `pg_class` and is read directly. Citations: `raw/postgres-18/src/include/storage/bufpage.h:218`, `raw/postgres-18/src/include/access/nbtree.h:63`.
- **Numerator.** `total_used_bytes ≈ reltuples * bytes_per_entry`, where `bytes_per_entry` is the on-disk cost of one logical index entry: a 4-byte line pointer plus a `MAXALIGN`-padded payload of an 8-byte `IndexTupleData` header, optional null bitmap, and key/INCLUDE column data. The heap TID is already inside `IndexTupleData.t_tid` for non-posting tuples. Citations: `raw/postgres-18/src/include/access/itup.h:35`, `raw/postgres-18/src/include/access/itup.h:51`.
- **Per-key width.** `pg_stats.avg_width` provides the mean stored width per column, including TOAST-aware behavior. Falls back to `pg_attribute.attlen` for fixed-length types when no stats row exists, and to a 32-byte default for expression keys (where `indkey[i] = 0`).

`pg_class.reltuples` for a btree index is written by VACUUM through `IndexBulkDeleteResult.num_index_tuples`. During a `btbulkdelete` pass with a callback, it accumulates `nhtidslive` per leaf — the count of *live heap TIDs*, including all members of posting-list tuples; during cleanup-only `btvacuumcleanup` it instead accumulates `maxoff - minoff + 1` per leaf — the physical line-pointer count. Either way, partial indexes are handled implicitly because only pages of the partial index are scanned. Citations: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:btvacuumcleanup`, `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1637`, `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1639`.

## SQL

```sql
WITH params AS (
    SELECT 'public.t_idx'::regclass AS idxoid                  -- target index
),
ix AS (
    SELECT  c.oid                            AS indexrelid,
            c.relpages::bigint               AS relpages,
            c.reltuples                      AS reltuples,
            c.reloptions,
            i.indrelid,
            i.indnatts,
            i.indkey,
            i.indpred IS NOT NULL            AS is_partial,
            n.nspname                        AS tab_schema,
            tc.relname                       AS tab_name
    FROM    pg_class    c
    JOIN    pg_index    i  ON i.indexrelid = c.oid
    JOIN    pg_class    tc ON tc.oid       = i.indrelid
    JOIN    pg_namespace n ON n.oid        = tc.relnamespace
    WHERE   c.oid   = (SELECT idxoid FROM params)
      AND   c.relam = (SELECT oid FROM pg_am WHERE amname = 'btree')
),
keys AS (
    SELECT  ix.indexrelid,
            SUM( COALESCE( s.avg_width,
                           NULLIF(a.attlen, -1),
                           32 ) )::int                          AS keys_width,
            BOOL_OR( COALESCE(NOT a.attnotnull, true) )         AS any_nullable
    FROM    ix
    CROSS JOIN LATERAL generate_series(1, ix.indnatts) AS g(k)
    LEFT JOIN pg_attribute a
           ON a.attrelid = ix.indrelid
          AND a.attnum   = ix.indkey[g.k - 1]                   -- expression keys (attnum 0) drop out
    LEFT JOIN pg_stats s
           ON s.schemaname = ix.tab_schema
          AND s.tablename  = ix.tab_name
          AND s.attname    = a.attname
    GROUP BY ix.indexrelid
),
calc AS (
    SELECT  ix.*,
            k.keys_width,
            k.any_nullable,
            COALESCE((
                SELECT lower(split_part(o, '=', 2)) = 'false'
                FROM   unnest(COALESCE(ix.reloptions, '{}'::text[])) AS o
                WHERE  o LIKE 'deduplicate_items=%'
                LIMIT  1
            ), false)                                           AS dedup_off
    FROM    ix
    JOIN    keys k USING (indexrelid)
)
SELECT
    indexrelid::regclass                                        AS index,
    is_partial,
    NOT dedup_off                                               AS dedup_potentially_active,
    relpages,
    reltuples::bigint                                           AS reltuples,
    -- per-entry footprint = line ptr + MAXALIGN(IndexTupleData + nullbitmap + payload)
    ( 4
      + 8 * (( 8
              + CASE WHEN any_nullable THEN ((indnatts + 7) / 8) ELSE 0 END
              + keys_width
              + 7) / 8)
    )                                                           AS bytes_per_entry_est,
    -- avg_leaf_density estimate (%): 100 * reltuples * bytes_per_entry / ((relpages-1) * 8152)
    ROUND(
        100.0 * reltuples *
          ( 4 + 8 * (( 8
                       + CASE WHEN any_nullable
                              THEN ((indnatts + 7) / 8)
                              ELSE 0 END
                       + keys_width
                       + 7) / 8) )
        / NULLIF( (relpages - 1)::numeric * 8152.0, 0 )
    , 2)                                                        AS avg_leaf_density_pct_est
FROM calc;
```

The `8152` constant assumes the cluster's compiled `BLCKSZ = 8192`, which is the standard build (`raw/postgres-18/src/include/pg_config_manual.h`). For non-default block sizes, replace with `current_setting('block_size')::int - 24 - 16`.

## Why The Estimate Is Reasonably Accurate

For a btree without deduplication and with stable column widths, the per-entry on-disk footprint is essentially `4 + MAXALIGN(8 + nullbitmap + key_width + include_width)`. `pg_stats.avg_width` typically tracks the same bytes the indexer pays per column (TOAST inline / detoasted-original handling matches what btree stores for indexable types). Because both sides of the ratio scale with the same population, multiplicative bias from imperfect width estimation cancels in the density ratio when the index is well-packed.

Two structural error sources remain:

- **Internal pages in the denominator.** Using `(relpages - 1)` instead of `leaf_pages` overcounts leaves by the internal-page share. For typical fanouts the resulting density is biased *down* by less than 1%; for very small indexes (a handful of pages) the bias can be larger.
- **Recently inserted growth.** New leaf splits leave half-empty pages until VACUUM and inserts repack them. Catalog stats lag actual page state, so the estimate reflects the population at the last `(auto)VACUUM`/`ANALYZE`, not "right now".

A second-pass calibration is available when needed: run `pgstatindex` once on a representative index, compute the ratio of measured to estimated density, and apply that as a per-shape correction factor. This still costs zero per-query I/O on the index after calibration.

## Partial Indexes

The estimate is partial-aware without special code:

- `pg_class.reltuples` is written from `IndexBulkDeleteResult.num_index_tuples`, which only sums leaves of the partial index that VACUUM walked. Citations: `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1637`, `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1639`.
- `pg_class.relpages` similarly counts only the partial index's blocks.
- The query exposes `is_partial` from `pg_index.indpred IS NOT NULL` so callers know the SQL is operating on a partial index.

The only systematic bias is in `keys_width`. This SQL reads `pg_stats` rows for the *table* columns (joining on table schema/name and the attribute name), not for a partial subset. If the partial predicate selects a sub-population whose column widths differ noticeably from the table-wide distribution, `keys_width` is biased toward the full-table mean. For variable-width keys where this matters, a sharper estimate is to add per-index expression statistics rows (ANALYZE on the index relation creates `pg_stats` entries with `tablename = <index_name>` for expression columns; the same pattern can be exploited by extending the join branch). The default form in this page is the widely-applicable, low-bias version.

## Deduplication

Btree deduplication is on by default in PG 18 (`BTGetDeduplicateItems` returns `true` unless the index's `BTOptions.deduplicate_items` reloption is `false`). Citations: `raw/postgres-18/src/include/access/nbtree.h:1155`, `raw/postgres-18/src/include/access/nbtree.h:1170`, `raw/postgres-18/src/backend/access/common/reloptions.c:161`.

When deduplication merges duplicate keys into posting-list tuples, several heap TIDs share one tuple header and one set of key bytes, paying ~6 extra bytes per additional TID instead of a full new tuple. After a `btbulkdelete` pass, `pg_class.reltuples` still counts heap TIDs (live posting-list members are counted as separate live tuples per `nbtree.c:1620-1622, 1637`), so:

- `reltuples * bytes_per_entry` overestimates the actual on-disk byte usage.
- The reported `avg_leaf_density_pct_est` is therefore an **upper bound** on the real density; values noticeably above 100% are a strong signal that dedup is doing meaningful work.

The query exposes `dedup_potentially_active` so callers can interpret the estimate accordingly. If a tighter number is required for a dedup-active index, fall back to `pgstatindex` for that one index — this is exactly the case where the per-block scan earns its I/O.

## Caveats

- The estimate depends on a recent `(auto)VACUUM` and `ANALYZE`. Stale stats produce stale density. For high-churn indexes between VACUUMs, this metric measures population at last cleanup, not present.
- INCLUDE columns are folded into `keys_width` because `indnatts` covers both key and INCLUDE attributes; their contribution is correct only when their `pg_stats.avg_width` (or `attlen`) is representative.
- Expression keys have `indkey = 0`, so the `LEFT JOIN pg_attribute` on `attnum` drops them and they fall back to the 32-byte default. For accuracy on expression indexes, `ANALYZE <index_name>` populates `pg_stats` rows with the index relation as `tablename`; extend the `pg_stats` join with that branch when needed.
- The `BLCKSZ - 40` denominator assumes the standard build. Replace with the runtime-aware `current_setting('block_size')::int - 24 - 16` for clusters with a non-default block size.
- This SQL is read-only; it does not lock the index, does not call into nbtree, and is safe to run during normal traffic.

## Cross-Links

- [[v18/code-paths/pgstatindex]] - Full per-block scan whose result this page approximates.
- [[v18/index]]
- [[versions]]

## Source References

- `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:pgstatindex_impl`
- `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:309`
- `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:311`
- `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:362`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:btvacuumcleanup`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1637`
- `raw/postgres-18/src/backend/access/nbtree/nbtree.c:1639`
- `raw/postgres-18/src/include/access/itup.h:35`
- `raw/postgres-18/src/include/access/itup.h:51`
- `raw/postgres-18/src/include/access/nbtree.h:63`
- `raw/postgres-18/src/include/access/nbtree.h:1155`
- `raw/postgres-18/src/include/access/nbtree.h:1170`
- `raw/postgres-18/src/include/storage/bufpage.h:159`
- `raw/postgres-18/src/include/storage/bufpage.h:218`
- `raw/postgres-18/src/backend/access/common/reloptions.c:161`
- `raw/postgres-18/src/backend/storage/page/bufpage.c:PageGetExactFreeSpace`

## Open Questions

- `pg_class.reltuples` for a btree index is updated through both `btbulkdelete` (counting heap TIDs via `nhtidslive`) and cleanup-only `btvacuumcleanup` (counting line pointers via `maxoff - minoff + 1`). On a dedup-heavy index whose last VACUUM was cleanup-only, `reltuples` is closer to the physical leaf-entry count than to the heap TID count, which subtly shifts the bias direction of this estimate. A follow-up trace through `vac_update_relstats` and `IndexBulkDeleteResult.num_index_tuples` should document which path each common autovacuum trigger takes, so the dedup caveat can be made precise.
- `pg_stats` for partial indexes: ANALYZE generates per-index expression-column rows for expression keys, but plain (non-expression) partial indexes rely on table-wide column statistics. Quantifying the resulting bias on real partial-index workloads would let us decide whether to default-extend the `pg_stats` join with an index-relation branch.
