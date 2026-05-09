---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: claude-opus-4-7 2026-05-09T00:00:00Z
---

# Estimate avg_leaf_density without pgstattuple

## Question

In PostgreSQL 12, propose a SQL query that returns `avg_leaf_density` for a B-tree index — equivalent to what `pgstatindex` reports — using only built-in features (no `pgstattuple`, no `pageinspect`, no other extensions), minimizing index I/O while still being reasonably accurate. The query must work correctly for partial indexes.

## Short Answer

Drive the estimate from catalog metadata only. Read zero index pages.

- `pg_class.relpages` and `pg_class.reltuples` on the index are written for the index relation itself by VACUUM and ANALYZE, so for a partial index they already reflect the post-predicate page count and row count [[raw/postgres-12/src/backend/access/heap/vacuumlazy.c#lazy_cleanup_index|vacuumlazy.c#L1798-L1815]], [[raw/postgres-12/src/backend/commands/analyze.c|analyze.c#L612-L628]], [[raw/postgres-12/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#L1022,L1094]].
- Estimate the average index-tuple size from `pg_attribute` (which columns are indexed, nullability) plus `pg_stats.avg_width` (per-column average width on the underlying table) plus fixed B-tree page geometry: header 24 B [[raw/postgres-12/src/include/storage/bufpage.h|bufpage.h#L151-L164,L216]] + `BTPageOpaqueData` 16 B [[raw/postgres-12/src/include/access/nbtree.h|nbtree.h#L55-L66]] + 4 B line pointer per tuple, 8 KB pages.
- Match the `pgstatindex` formula exactly. `pgstatindex` defines density as `100 * (max_avail − free_space) / max_avail`, where `max_avail` is the per-leaf-page usable area `BLCKSZ − SizeOfPageHeaderData − MAXALIGN(sizeof(BTPageOpaqueData))` = 8152 bytes [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#L296-L298,L347-L349]]. Header and special bytes are *outside* the reckoning, not part of the numerator.

The estimate is mean-field: it assigns the same average tuple size to every leaf and spreads `reltuples` uniformly. It tracks `pgstatindex` within a few percentage points on healthy indexes and correctly surfaces classic post-VACUUM bloat. It cannot reveal per-page variance.

```sql
-- Estimate avg_leaf_density of a B-tree index without reading any index pages.
-- Set the index here (schema-qualified or bare):
WITH params AS (SELECT 'public.my_index'::regclass AS idx),

ix AS (
    SELECT /* wiki_pg12_avg_leaf_density_zero_io */
           c.oid AS index_oid, n.nspname AS schema_name, c.relname AS index_name,
           c.relpages, c.reltuples, i.indrelid,
           i.indpred IS NOT NULL AS is_partial,
           i.indkey
      FROM params p
      JOIN pg_class      c ON c.oid = p.idx AND c.relkind = 'i'
      JOIN pg_namespace  n ON n.oid = c.relnamespace
      JOIN pg_index      i ON i.indexrelid = c.oid
),
tab AS (
    SELECT /* wiki_pg12_avg_leaf_density_zero_io */
           ix.index_oid, tn.nspname AS tschema, tc.relname AS tname
      FROM ix
      JOIN pg_class     tc ON tc.oid = ix.indrelid
      JOIN pg_namespace tn ON tn.oid = tc.relnamespace
),
attrs AS (
    SELECT /* wiki_pg12_avg_leaf_density_zero_io */
           ix.index_oid,
           a.attnotnull,
           COALESCE(s.avg_width, NULLIF(t.typlen, -1), 16) AS w
      FROM ix
      CROSS JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY AS k(attnum, ord)
      JOIN pg_attribute a ON a.attrelid = ix.indrelid AND a.attnum = k.attnum
      JOIN pg_type      t ON t.oid = a.atttypid
      JOIN tab          tb ON tb.index_oid = ix.index_oid
      LEFT JOIN pg_stats s
             ON s.schemaname = tb.tschema
            AND s.tablename  = tb.tname
            AND s.attname    = a.attname
     WHERE k.attnum <> 0    -- expression columns (indkey = 0); see Open Questions
),
size_est AS (
    SELECT /* wiki_pg12_avg_leaf_density_zero_io */
           index_oid,
           bool_or(NOT attnotnull)        AS has_nullable,
           sum( ((w + 7) / 8) * 8 )::int  AS sum_aligned_width    -- per-attr MAXALIGN(8)
      FROM attrs
     GROUP BY index_oid
),
calc AS (
    SELECT /* wiki_pg12_avg_leaf_density_zero_io */
           ix.schema_name, ix.index_name, ix.is_partial,
           ix.relpages, ix.reltuples,
           -- IndexInfoFindDataOffset(): hoff = 8 (no nulls) | 16 (any null in tuple).
           -- index_form_tuple wraps the whole tuple in a final MAXALIGN(8).
           ( ( (CASE WHEN se.has_nullable THEN 16 ELSE 8 END
                 + se.sum_aligned_width) + 7 ) / 8 ) * 8 AS tuple_size,
           GREATEST(ix.relpages - 1, 1)::numeric         AS leaf_pages_est
      FROM ix JOIN size_est se ON se.index_oid = ix.index_oid
)
SELECT /* wiki_pg12_avg_leaf_density_zero_io */
       schema_name || '.' || index_name AS index,
       is_partial,
       relpages,
       reltuples,
       tuple_size                       AS est_index_tuple_bytes,
       -- pgstatindex's max_avail per leaf is 8192 - 24 - 16 = 8152 bytes.
       -- pgstatindex's free_space subtracts sizeof(ItemIdData)=4 (PageGetFreeSpace),
       -- so used_bytes per leaf = max_avail - free_space ~= 4 + line_pointers + tuples.
       ROUND(
         100.0 * (
             4 * leaf_pages_est                          -- PageGetFreeSpace -ItemIdData bias
           + reltuples::numeric * (4 + tuple_size)       -- 4B line pointer + tuple body
         ) / (leaf_pages_est * 8152.0)
       , 2) AS avg_leaf_density_pct
  FROM calc;
```

Run `ANALYZE <table>;` first so `relpages`, `reltuples`, and `pg_stats.avg_width` are fresh — that is the only I/O the approach incurs, and it touches the heap, not the index.

## Detailed Answer

### What avg_leaf_density actually measures

`pgstatindex` walks every non-meta block, classifies each leaf, and accumulates two totals per leaf [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#L271-L308]]:

```c
max_avail   = BLCKSZ - (BLCKSZ - phdr->pd_special + SizeOfPageHeaderData);
            = pd_special - SizeOfPageHeaderData
free_space  = PageGetFreeSpace(page);     // pd_upper - pd_lower - sizeof(ItemIdData)
```

Then density is `100 * (max_avail − free_space) / max_avail` per the result-build block at [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#L347-L349]]:

```c
if (indexStat.max_avail > 0)
    values[j++] = psprintf("%.2f",
        100.0 - (double) indexStat.free_space / (double) indexStat.max_avail * 100.0);
```

Two consequences for the estimator:

1. **Header and special are outside the reckoning.** `max_avail` excludes `SizeOfPageHeaderData` (24 B) and `MAXALIGN(sizeof(BTPageOpaqueData))` (16 B). They are not in the denominator and not in the "used" numerator. The relevant area per leaf is 8192 − 24 − 16 = 8152 bytes.
2. **Live and dead tuples both count as used.** `pgstatindex` does not distinguish them; it sees only `pd_lower`/`pd_upper` and tuple bodies. The estimator is therefore approximating "what's on disk," not "what's logically live."

### B-tree anatomy the estimator reasons about

Index-level layout under the standard 8 KB `BLCKSZ`:

```
                     pg_class.relpages = N
   +-----------+
   | meta page |   page 0, fixed 1 page
   +-----------+
   |  root     |   internal
   +-----------+
   |  internal |
   +-----------+
   |  leaf 1   |   <-- these are what avg_leaf_density measures
   |  leaf 2   |
   |  ...      |
   |  leaf K   |
   +-----------+
```

With B-tree fanout F (~250 typical), `internal_pages ~ leaf_pages / (F-1)`. For all but the smallest indexes, `leaf_pages ~= relpages - 1` (subtract metapage; internal pages contribute under 1%). The SQL uses `GREATEST(relpages - 1, 1)` to concede that bias.

Single leaf-page layout from `PageHeaderData` [[raw/postgres-12/src/include/storage/bufpage.h|bufpage.h#L151-L164]] and `BTPageOpaqueData` [[raw/postgres-12/src/include/access/nbtree.h|nbtree.h#L55-L66]]:

```
   byte 0   +------------------------------+
            |  PageHeaderData    (24 B)    |  outside max_avail
       24   +------------------------------+
            |  ItemId array      4 B each  |  pd_lower advances right
            |  ...                         |
            |                              |
            |        FREE SPACE            |
            |                              |
            |  ...                         |
            |  Index tuples                |  pd_upper advances left
            |    [tuple_n]                 |
            |    [tuple_2]                 |
            |    [tuple_1]                 |
     8176   +------------------------------+
            |  BTPageOpaqueData  (16 B)    |  outside max_avail
     8192   +------------------------------+

   max_avail per leaf  = 8152 bytes (region between the two fixed areas)
   used  per leaf      = 4 * tuples + sum of MAXALIGN(tuple sizes)
                         + 4 (PageGetFreeSpace bias, see below)
   free  per leaf      = pd_upper - pd_lower - 4
```

`PageGetFreeSpace` subtracts `sizeof(ItemIdData) = 4` to be "free for adding a new tuple," so `used = max_avail − free_space` is biased upward by 4 bytes per leaf [[raw/postgres-12/src/backend/storage/page/bufpage.c|bufpage.c#PageGetFreeSpace]]. The estimator matches that bias by adding `4 * leaf_pages` to the numerator.

Single index tuple from `IndexTupleData` [[raw/postgres-12/src/include/access/itup.h|itup.h#L35-L51]]:

```
   +-------------------------------------------+
   | IndexTupleData  (8 B)                     |  t_tid (6) + t_info (2)
   +-------------------------------------------+
   | IndexAttributeBitMapData  (4 B = ceil(    |  PRESENT only when t_info has
   | INDEX_MAX_KEYS / 8))                      |  HasNulls bit set, padded by
   |   -> hoff jumps to 16 after MAXALIGN      |  MAXALIGN to 16-byte hoff
   +-------------------------------------------+
   | Key column 1   (MAXALIGN'ed by typalign)  |
   | Key column 2                              |
   | ...                                       |
   +-------------------------------------------+
```

`INDEX_MAX_KEYS = 32` [[raw/postgres-12/src/include/pg_config_manual.h|pg_config_manual.h#L52]] makes the bitmap a fixed 4 bytes regardless of column count. `IndexInfoFindDataOffset(t_info)` returns `MAXALIGN(8) = 8` when no nulls and `MAXALIGN(8 + 4) = 16` when nulls are present [[raw/postgres-12/src/include/access/itup.h|itup.h#L80-L90]]. The full tuple is then size-rounded by a final `MAXALIGN(size)` in `index_form_tuple` [[raw/postgres-12/src/backend/access/common/indextuple.c#index_form_tuple|indextuple.c#L132-L133]].

The estimator pessimistically assumes `hoff = 16` whenever any indexed column is declared nullable (`pg_attribute.attnotnull = false`), even if no actual NULL ever appears in that tuple. That overestimates tuple size by 8 bytes when the column is nominally nullable but in practice never null — see partial-index Scenario P5 below.

### The estimator's core formula

Roll up the page accounting across the whole index:

```
            4 * L                         <- PageGetFreeSpace -ItemIdData bias
  used  =   + reltuples * (4 + tuple_size)<- line pointer + tuple body
  ----      -------------------------------------------------
  cap        L * 8152                     <- max_avail per leaf

  where L = leaf_pages_est = relpages - 1
        tuple_size = MAXALIGN(hoff + sum(MAXALIGN(col widths)))
        hoff = 16 if any indexed col is nullable, else 8
```

Both sides come straight from catalogs; no index buffer is touched. The numerator does not include the 24 + 16 = 40 bytes of fixed header/special — those bytes are outside `max_avail` in `pgstatindex`'s definition.

### Fragmentation scenarios — why density varies

Diagrams below show one leaf page in each state. `#` = used bytes inside `max_avail`, `.` = free bytes inside `max_avail`, `H` = page header (outside), `S` = btree special area (outside). Header and special bytes are visually present but they do not count toward density.

#### A. Freshly built / just `REINDEX`ed (~90% density)

`CREATE INDEX` packs leaf pages to `fillfactor`. B-tree default is 90 [[raw/postgres-12/src/include/access/nbtree.h|nbtree.h#L169]].

```
  leaf:  H ############################. S
  leaf:  H ############################. S
  leaf:  H ############################. S
                                       ^
                            ~10% deliberate slack for future inserts
```

The estimator hits this case almost exactly: every leaf is uniformly full, and the tuple-size calculation lines up with reality.

#### B. Append-only sequential keys (~90%)

For monotonically increasing keys, `_bt_findsplitloc` arranges to leave the *left* split page at fillfactor when the page is rightmost, so previously rightmost leaves freeze at fillfactor instead of the 50/50 split that random inserts produce [[raw/postgres-12/src/backend/access/nbtree/nbtsplitloc.c#_bt_findsplitloc|nbtsplitloc.c#L97-L101]].

```
  leaf 1:  H ############################. S    <- frozen at fillfactor
  leaf 2:  H ############################. S
  leaf K:  H ##########.................. S    <- current rightmost, filling
```

Estimator slightly overestimates for the rightmost page, but it is one page in many — error negligible.

#### C. Random uniform inserts (~65–75%)

Page splits in the middle of a hot page produce two roughly half-full leaves; over time the tree settles around 65–75% density.

```
  leaf:  H ##################............ S
  leaf:  H ####################.......... S
  leaf:  H ##################............ S
  leaf:  H #####################......... S
```

Estimator still tracks well: `reltuples` already reflects the post-split row count and `relpages` the post-split page count.

#### D. After mass DELETE without VACUUM (still appears dense)

Dead tuples remain physically present; they show up as used bytes both in `pgstatindex` and in this estimator (`reltuples` has not been updated yet — VACUUM/ANALYZE writes it).

```
  leaf:  H DDDDDDDDDDDDDDDDDDDDDDDDDDDDDD. S    <- D = dead, still on page
  leaf:  H DDDDDDDDDDDDDDDDDDDDDDDDDDDDDD. S
```

Reads as ~90% density on both methods. Both report what is on disk, not what is logically reachable.

#### E. After VACUUM following mass DELETE (low density, classic bloat)

`btvacuumscan` calls `_bt_delitems_vacuum`, which calls `PageIndexMultiDelete` to compact dead items off the page [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_delitems_vacuum|nbtpage.c#L986-L1016]]. Crucially, B-tree VACUUM does *not* truncate the index file; it only marks fully-empty pages `BTP_DELETED` and records them in the FSM for future recycling [[raw/postgres-12/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#L1078-L1089]]. There is no `RelationTruncate` on the B-tree path. Result: a sparsely populated index file that retains its old size.

```
  leaf:  H ##.......##............#...... S    <- ~30% used inside max_avail
  leaf:  H ........#####................. S
  leaf:  H #...........................#. S
```

`reltuples` drops sharply but `relpages` stays high. The estimator captures this: the numerator shrinks (fewer tuples) while the denominator stays the same — low density. This is the case where the query is most useful: the "do I need REINDEX?" signal.

#### F. Skewed updates with non-HOT index changes

Index entries are not HOT-eligible; every UPDATE that changes an indexed column adds a new index tuple and (after VACUUM) leaves a dead one behind. Density patterns mirror D/E depending on VACUUM frequency.

#### G. Where the estimator drifts from pgstatindex

```
  Reality:                              Estimator's mental model:
  H ##........###.....#......##. S      H ###########################. S
   <- one bloated leaf                   <- assumes uniform avg

  H ############################. S
   <- one full leaf
```

The estimator is mean-field: it spreads `reltuples` evenly across all leaves. If bloat is highly localized (a few hot pages near-empty, the rest packed), the *aggregate* density still comes out right — that is the property `avg_leaf_density` is designed to surface. What the estimator cannot tell you is the variance across pages; for that, real `pgstatindex` is required.

### Partial-index scenarios

The thing that makes partial indexes tricky is splitting the question into two halves:

| Quantity            | Source                                                      | Reflects predicate? |
|---------------------|-------------------------------------------------------------|---------------------|
| `relpages`          | `pg_class` of the index, written from `RelationGetNumberOfBlocks(rel)` [[raw/postgres-12/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#L1022,L1094]] | Yes — physical pages of the partial index only |
| `reltuples`         | `pg_class` of the index, accumulated as `maxoff - minoff + 1` per leaf in `btvacuumpage` [[raw/postgres-12/src/backend/access/nbtree/nbtree.c#btvacuumpage|nbtree.c#L1335]], or as `tupleFract * totalrows` in ANALYZE [[raw/postgres-12/src/backend/commands/analyze.c|analyze.c#L821-L822]] | Yes — count of rows that passed the predicate |
| `avg_width` per col | `pg_stats` view exposes `pg_statistic.stawidth` [[raw/postgres-12/src/backend/catalog/system_views.sql|system_views.sql#L196]], computed in `compute_*_stats` over the table sample [[raw/postgres-12/src/backend/commands/analyze.c|analyze.c#L1784,L1964,L2344]] | No — full-table average |

Row count and page count are predicate-aware for free; only the per-tuple width estimate can drift.

#### P1. Predicate uncorrelated with width (the common case)

```
  Table users (10M rows, name avg 24 B)
  Partial idx WHERE is_active = true  (1M rows)

  Indexed subset's name-width distribution ~= full table's
  -> estimator uses 24 B, true is ~24 B
  -> density estimate matches pgstatindex within ~2 pp
```

```
  Index pages (real):    Estimator's model:
  H ######...... S       H ######...... S
  H ######...... S       H ######...... S
  H #####....... S       H ######...... S   <- ~uniform, close enough
```

#### P2. Predicate correlated with column width

```
  Table products, name varies wildly by region.
  Partial idx WHERE region = 'JP'   (names avg 12 B in JP, 24 B overall)

  Estimator pulls 24 B from full-table pg_stats
  -> overestimates tuple_size by ~2x on the indexed columns
  -> overestimates density (bytes_used numerator inflated)
```

Mitigation if tighter numbers are needed: replace the `pg_stats` join with `avg(pg_column_size(col))` over the table using the partial predicate. That costs a heap scan but is still vastly cheaper than `pgstatindex`'s full leaf-page scan and stays extension-free.

#### P3. Tiny partial index (a handful of rows)

```
  Partial idx WHERE failed = true   (200 rows)
  relpages = 2  (metapage + 1 leaf)
  -> leaf_pages_est = 1
  -> denominator = 8152, very lumpy
  -> single-tuple alignment errors visible at ~5 pp
```

For indexes with `relpages < ~10`, treat the result as ballpark. Below that scale, `REINDEX` is cheap if bloat is suspected.

#### P4. Soft-delete partial unique index (the textbook good case)

```
  CREATE UNIQUE INDEX ON orders(customer_id)
    WHERE deleted_at IS NULL;
```

- `reltuples` accurately tracks live (non-soft-deleted) rows.
- Width distribution of live rows is usually identical to all rows (deletion is not width-correlated).
- Estimator is essentially as accurate as it would be on a non-partial unique index.

#### P5. Predicate excludes NULLs on a nullable column

If the indexed column is declared nullable but the partial predicate excludes NULLs (`WHERE col IS NOT NULL`), the on-disk leaf tuples never have the `INDEX_NULL_MASK` set, so `hoff = 8` and there is no bitmap [[raw/postgres-12/src/backend/access/common/indextuple.c#index_form_tuple|indextuple.c#L112-L124]]. The estimator budgets `hoff = 16` anyway because it keys on `attnotnull`, not on the partial predicate:

```
  Reality:           Estimator:
  [hdr][key]         [hdr][bitmap_pad][key]
   8 + W              16 + W
```

Effect: small overestimate of tuple size, hence small overestimate of density. A tighter version could parse `pg_index.indpred` for `IS NOT NULL` clauses; for diagnostic use this is over-engineering.

### When to trust the estimate

| Use case                                           | Trust the estimate? |
|----------------------------------------------------|---------------------|
| "Is this index roughly bloated, should I REINDEX?" | Yes — clear signal in scenarios D/E |
| "Show me density across all indexes nightly"       | Yes — pure catalog reads, scales to thousands of indexes |
| "Exact density to 1 pp for capacity planning"      | No — use real `pgstatindex` on a sampled subset |
| "Per-page distribution / find hot bloated pages"   | No — this is mean-field, cannot see variance |
| "Partial index with width-correlated predicate"    | Only after replacing `pg_stats` with predicate-scoped `avg(pg_column_size(...))` |

### Mental model in one line

Catalog stats already encode "how many rows live in how many pages"; multiply the row count by an estimated per-row footprint and compare it to the per-leaf usable area `max_avail`. The whole query is that sentence written out in SQL, with the same `max_avail` denominator that `pgstatindex` uses.

## Source References

- `pgstatindex` density formula: `max_avail = pd_special - SizeOfPageHeaderData` per leaf [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#L296]]; aggregate `100 * (max_avail - free_space) / max_avail` at [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl|pgstatindex.c#L347-L349]]. Live and dead tuples are not distinguished — they all count as occupying the leaf via `PageGetFreeSpace`.
- `PageHeaderData` size 24 B and `SizeOfPageHeaderData = offsetof(PageHeaderData, pd_linp)` [[raw/postgres-12/src/include/storage/bufpage.h|bufpage.h#L151-L164,L216]].
- `BTPageOpaqueData` size 16 B (4 + 4 + 4 + 2 + 2) [[raw/postgres-12/src/include/access/nbtree.h|nbtree.h#L55-L66]]. `MAXALIGN(16) = 16` on 64-bit.
- `IndexTupleData` 8 B header (`t_tid` 6 + `t_info` 2) [[raw/postgres-12/src/include/access/itup.h|itup.h#L35-L51]].
- `IndexAttributeBitMapData` is a fixed `(INDEX_MAX_KEYS + 7) / 8` bytes regardless of natts [[raw/postgres-12/src/include/access/itup.h|itup.h#L55-L58]]; `INDEX_MAX_KEYS = 32` [[raw/postgres-12/src/include/pg_config_manual.h|pg_config_manual.h#L52]] so the bitmap is 4 bytes.
- `IndexInfoFindDataOffset(t_info)` returns 8 when `INDEX_NULL_MASK` is clear, else `MAXALIGN(8 + 4) = 16` [[raw/postgres-12/src/include/access/itup.h|itup.h#L80-L90]]. The flag is set per-tuple iff any attribute in that tuple is NULL [[raw/postgres-12/src/backend/access/common/indextuple.c#index_form_tuple|indextuple.c#L112-L124]]. The whole tuple ends with a final `size = MAXALIGN(size)` [[raw/postgres-12/src/backend/access/common/indextuple.c#index_form_tuple|indextuple.c#L132-L133]].
- `BTREE_DEFAULT_FILLFACTOR = 90` [[raw/postgres-12/src/include/access/nbtree.h|nbtree.h#L169]].
- Rightmost-split optimization that freezes left page at fillfactor when inserting at the right edge [[raw/postgres-12/src/backend/access/nbtree/nbtsplitloc.c#_bt_findsplitloc|nbtsplitloc.c#L97-L101]].
- `index_update_stats` writes `relpages = RelationGetNumberOfBlocks(rel)` and `reltuples = passed value` in-place to `pg_class`, with no transactional update [[raw/postgres-12/src/backend/catalog/index.c#index_update_stats|index.c#L2761-L2786]].
- VACUUM's index path: `lazy_cleanup_index` calls `index_vacuum_cleanup` then `vac_update_relstats(indrel, stats->num_pages, stats->num_index_tuples, ...)` [[raw/postgres-12/src/backend/access/heap/vacuumlazy.c#lazy_cleanup_index|vacuumlazy.c#L1798-L1815]].
- B-tree's per-leaf live-tuple count: `stats->num_index_tuples += maxoff - minoff + 1` in `btvacuumpage` [[raw/postgres-12/src/backend/access/nbtree/nbtree.c#btvacuumpage|nbtree.c#L1335]]. `stats->num_pages = num_pages = RelationGetNumberOfBlocks(rel)` [[raw/postgres-12/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#L1022,L1094]]. For a partial index this counts only post-predicate rows because only those are inserted into the index file.
- ANALYZE's index path: `tupleFract = numindexrows / numrows`; `totalindexrows = ceil(tupleFract * totalrows)` written via `vac_update_relstats` [[raw/postgres-12/src/backend/commands/analyze.c|analyze.c#L612-L628,L821-L822]].
- `pg_stats.avg_width` aliases `pg_statistic.stawidth` [[raw/postgres-12/src/backend/catalog/system_views.sql|system_views.sql#L196]], computed as `total_width / nonnull_cnt` over the table sample, not predicate-scoped [[raw/postgres-12/src/backend/commands/analyze.c|analyze.c#L1784,L1964,L2344]].
- B-tree VACUUM compacts pages via `PageIndexMultiDelete` in `_bt_delitems_vacuum` [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_delitems_vacuum|nbtpage.c#L986-L1016]] but does not call `RelationTruncate`. Recyclable pages are recorded in the FSM for future split reuse [[raw/postgres-12/src/backend/access/nbtree/nbtree.c#btvacuumscan|nbtree.c#L1078-L1089]]. Of the in-tree index AMs, only SP-GiST truncates during vacuum [[raw/postgres-12/src/backend/access/spgist/spgvacuum.c|spgvacuum.c#L882]].
- `pg_index` schema: `indkey` int2vector with 0 marking expression columns, `indpred` is NULL for non-partial indexes [[raw/postgres-12/src/include/catalog/pg_index.h|pg_index.h#L29-L59]].

## Context Reviewed

- `wiki/versions.md` to confirm PG 12 source pin `45b88269...` and legacy status.
- `wiki/v12/index.md` to fit the page into existing coverage.
- `wiki/log.md` recent entries to follow current filing conventions.
- Pinned source under `raw/postgres-12/` via `scripts/source_graph_query --version 12` — 13 raw lookups across `bufpage.h`, `nbtree.h`, `itup.h`, `pg_config_manual.h`, `pg_index.h`, `system_views.sql`, `pgstatindex.c`, `index.c`, `vacuumlazy.c`, `analyze.c`, `nbtree.c`, `nbtpage.c`, `nbtsplitloc.c`, `indextuple.c`.

## Related Pages

- [[v12/questions/reindex-concurrently-disk-space|REINDEX CONCURRENTLY disk space requirements (unverified)]] — sizing for the operation that resolves the bloat this query detects.
- [[v12/index|PostgreSQL 12.2 landing page]].

## Follow-Up Questions

- How does the estimate need to change for PostgreSQL 13+ where B-tree deduplication packs multiple TIDs under one key? The mean-field tuple-size assumption breaks down when posting-list compression is in play.
- Equivalents for non-B-tree access methods: GIN posting trees and entry trees, GiST, BRIN summary pages, hash buckets — each has a different leaf concept and different fixed overheads. Note that SP-GiST is the only AM that truncates its file during VACUUM, so its `relpages` semantics differ.
- A predicate-scoped width version that replaces the `pg_stats` join with `avg(pg_column_size(col))` over the indexed table filtered by `pg_index.indpred`. What is the I/O cost vs. accuracy gain for partial indexes with width-correlated predicates?
- A variance estimator: can the catalog tell us anything about per-page density spread, or is `pgstattuple_approx` (which still requires the extension) the cheapest route?
- Cost comparison vs. `pgstattuple_approx` and full `pgstatindex` on a representative table set, in pages read and wall-clock.

## Open Questions

- The estimator skips index expressions (`indkey` entries with `attnum = 0`). For an expression index, the column-width fallback path silently produces zero contribution. Either reject expression indexes with a clear error or compute expression width from `pg_index.indexprs` and a `pg_node_tree` decode — to be decided. The fixed 4-byte `IndexAttributeBitMapData` size is `INDEX_MAX_KEYS = 32` bits, so the null-bitmap budget is independent of natts; this is settled at the catalog level.
- Included columns (`INCLUDE`) in PG 11+ are stored at all attnum positions in `indkey` between 1 and `indnatts`; `indnkeyatts` distinguishes key from payload [[raw/postgres-12/src/include/catalog/pg_index.h|pg_index.h#L33-L34]]. The SQL above treats them uniformly as keys, which is correct for size purposes; INCLUDE columns occupy storage in the leaf tuple just like keys.
- The `((w + 7) / 8) * 8` rule assumes 64-bit MAXALIGN. On 32-bit builds (rare in production but still possible), MAXALIGN is 4. The query should branch on `current_setting('block_size')`-equivalent for alignment, or accept a small bias on 32-bit.
- The "internal pages are <1%" approximation needs a tighter bound for tall trees (very wide keys, low fanout). A worst-case-fanout-aware variant would subtract more than one page from `relpages`.
- The accuracy band ("within ~3–7 pp on healthy B-trees") is a hand estimate, not a measured one. A test harness comparing this estimator against `pgstatindex` across a representative index set would give defensible numbers.
- Behavior under non-default `BLCKSZ` (a compile-time option): the literal `8152` and the implicit 8192 in the query need to be parameterized via `current_setting('block_size')` for portability.
- The HasNulls bit is set per-tuple in `index_form_tuple` based on the actual NULL pattern in that row, so a nullable column with no NULLs in the data sees `hoff = 8`, not 16. The estimator pessimistically uses 16 whenever any indexed column is declared nullable, overestimating tuple size by 8 bytes per tuple in the (common) case where nullable columns have few or no nulls. A tighter version could weight by `pg_stats.null_frac`.
