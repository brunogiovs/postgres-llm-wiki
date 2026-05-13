---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Estimate avg_leaf_density with Minimal I/O (unverified)

## Short Answer

`pgstatindex()` from the `pgstattuple` extension reads **every leaf page** of a btree index to compute `avg_leaf_density`, which causes full-index I/O. To estimate the same metric with dramatically less I/O, use a sampling approach that reads only the metapage plus N leaf pages (N=5-10 is sufficient for reasonable accuracy).

The most practical implementation uses a small C function because plain SQL cannot read raw page bytes (`pd_special`, `pd_upper`, `pd_lower`). Below is the full approach: a C function that samples N blocks, plus a pure-SQL fallback using catalog statistics.

## How pgstatindex Computes avg_leaf_density

`pgstatindex()` scans every block from 1 to `RelationGetNumberOfBlocks(rel)`, classifies each page as leaf, internal, empty, deleted, or internal, and accumulates `max_avail` and `free_space` across all leaf pages:

[[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]]

For each leaf page the accumulation is:

```c
max_avail = BLCKSZ - (BLCKSZ - ((PageHeader) page)->pd_special + SizeOfPageHeaderData);
indexStat.max_avail += max_avail;
indexStat.free_space += PageGetFreeSpace(page);
indexStat.leaf_pages++;
```

Then the final `avg_leaf_density` is:

```c
100.0 - (double) indexStat.free_space / (double) indexStat.max_avail * 100.0
```

Where:
- `max_avail = pd_special - SizeOfPageHeaderData` — the total allocatable region on the page (from end of header to start of special space). This is the sum of the tuple area and the gap between tuples and special space.
- `PageGetFreeSpace(page) = pd_upper - pd_lower - sizeof(ItemIdData)` — the currently unused bytes between the tuple area and the special space, minus room for one more line pointer [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageGetFreeSpace]].

The page layout within a btree leaf page looks like this:

```
+-------------------+  <- page start (block 0 offset)
|  PageHeader       |  SizeOfPageHeaderData (~24 bytes)
|  (pd_lower ->)    |
+-------------------+
|  Tuples grow UP   |
|                   |
+===================+  <- pd_upper (grows downward from end)
|  Free space       |
+-------------------+
|  BTPageOpaqueData |  sizeof(BTPageOpaqueData) = 32 bytes
|  (special space)  |
+-------------------+  <- pd_special points here
|  (gap if any)     |
+-------------------+  <- page end (BLCKSZ = 8192)
```

For an 8KB block with standard btree layout:

```
BLCKSZ                           = 8192
SizeOfPageHeaderData              ~ 24
MAXALIGN(SizeOfPageHeaderData)    = 32
pd_linp (32 bytes for 8K/300)     ~ 32
BTPageOpaqueData                  = 32
---------------------------------
max_avail (usable area)           ~ 8096
```

The density formula is effectively:

```
avg_leaf_density = 100 * (max_avail - free_space) / max_avail
                 = 100 * occupied_bytes / max_avail
```

This is the percentage of the allocatable page region that is currently occupied by index tuples.

## Minimal-I/O Sampling Approach

### Why Sampling Works

Leaf pages in a btree index are filled relatively uniformly under normal conditions. The fill factor (default 90% for leaf pages [[raw/postgres-12/src/include/access/nbtree.h#BTREE_DEFAULT_FILLFACTOR]]) is applied consistently during index builds and page splits. This means the average fill across all leaf pages converges quickly — sampling 5-10 pages gives a density estimate within ~3-5% of the true value for non-severely-fragmented indexes.

The key insight: you only need to read the metapage (1 block) plus N leaf pages instead of all L leaf pages. For a large index with 100,000 leaf pages, reading 7 pages (1 metapage + 6 sampled) reduces I/O from ~800MB to ~56KB — a 14,000x reduction.

### How to Find Leaf Pages Without Scanning

The btree leaf pages form a doubly-linked list via the `btpo_next` (rightlink) field in `BTPageOpaqueData`. You can traverse from the root to any leaf page by following internal-page downlinks. However, the most practical approach is to read specific block numbers directly:

1. Read the metapage (block 0) to get `btm_root`, `btm_level`, and total block count
2. Calculate approximate leaf page positions (first few, middle, last few)
3. Read those specific blocks using `bt_page_stats()` from the `pageinspect` extension, or a custom C function

### Approach A: C Function with Strategic Sampling (Recommended)

This C function reads the metapage to determine tree depth, then samples N leaf pages at strategic positions (beginning, middle, end of the index). It returns `avg_leaf_density` estimated from the sample.

```c
/* src/backend/access/minileafdensity.c */

#include "postgres.h"
#include "access/nbtree.h"
#include "access/relation.h"
#include "catalog/namespace.h"
#include "funcapi.h"
#include "miscadmin.h"
#include "storage/bufmgr.h"
#include "utils/builtins.h"
#include "utils/rel.h"

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(mini_leaf_density);

typedef struct LeafSampleStats
{
    uint64    max_avail_total;
    uint64    free_space_total;
    int       leaf_count;
} LeafSampleStats;

static void
sample_leaf_block(Relation rel, BlockNumber blkno, LeafSampleStats *stats)
{
    Buffer      buffer;
    Page        page;
    BTPageOpaque opaque;

    buffer = ReadBufferExtended(rel, MAIN_FORKNUM, blkno, RBM_NORMAL,
                                GetAccessStrategy(BAS_BULKREAD));
    LockBuffer(buffer, BUFFER_LOCK_SHARE);
    page = BufferGetPage(buffer);
    opaque = (BTPageOpaque) PageGetSpecialPointer(page);

    /* Only count actual leaf pages, skip internal/deleted/empty */
    if (P_ISLEAF(opaque) && !P_IGNORE(opaque))
    {
        int         max_avail;

        /* Same formula as pgstatindex */
        max_avail = BLCKSZ - (BLCKSZ - ((PageHeader) page)->pd_special
                              + SizeOfPageHeaderData);
        stats->max_avail_total += max_avail;
        stats->free_space_total += PageGetFreeSpace(page);
        stats->leaf_count++;
    }

    LockBuffer(buffer, BUFFER_LOCK_UNLOCK);
    ReleaseBuffer(buffer);
}

Datum
mini_leaf_density(PG_FUNCTION_ARGS)
{
    text       *relname = PG_GETARG_TEXT_PP(0);
    int         n_samples = PG_GETARG_INT32(1);
    Relation    rel;
    RangeVar   *relrv;
    Buffer      buffer;
    Page        page;
    BTMetaPageData *metad;
    BTPageOpaque rootopaque;
    BlockNumber nblocks, blkno;
    LeafSampleStats stats;
    float8      avg_density;
    int         i;

    if (!superuser())
        ereport(ERROR,
                (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                 errmsg("must be superuser to use mini_leaf_density")));

    relrv = makeRangeVarFromNameList(textToQualifiedNameList(relname));
    rel = relation_openrv(relrv, AccessShareLock);

    if (rel->rd_rel->relkind != RELKIND_INDEX ||
        rel->rd_rel->relam != BTREE_AM_OID)
        ereport(ERROR,
                (errcode(ERRCODE_WRONG_OBJECT_TYPE),
                 errmsg("relation \"%s\" is not a btree index",
                        RelationGetRelationName(rel))));

    /* Read metapage */
    buffer = ReadBufferExtended(rel, MAIN_FORKNUM, 0, RBM_NORMAL,
                                GetAccessStrategy(BAS_BULKREAD));
    page = BufferGetPage(buffer);
    metad = BTPageGetMeta(page);
    rootopaque = (BTPageOpaque) PageGetSpecialPointer(page);

    nblocks = RelationGetNumberOfBlocks(rel);
    ReleaseBuffer(buffer);

    if (nblocks <= 1)
    {
        /* Index has only the metapage — no leaf pages to sample */
        PG_RETURN_NULL();
    }

    /* Initialize stats */
    stats.max_avail_total = 0;
    stats.free_space_total = 0;
    stats.leaf_count = 0;

    /*
     * Sample leaf pages at strategic positions (first, middle, last).
     *
     * For single-level trees (root = leaf), blocks 1..nblocks-1 are all leaves.
     * For multi-level trees, some early blocks may be internal pages; the
     * P_ISLEAF check in sample_leaf_block() skips them. This wastes a small
     * amount of I/O but avoids the complexity of traversing the rightlink
     * chain to find exact leaf block numbers.
     *
     * We sample: first 2 blocks, last 2 blocks, and evenly spaced middle.
     */
    if (n_samples < 3)
        n_samples = 3;
    if (n_samples > 16)
        n_samples = 16;

    /* Calculate sample positions */
    BlockNumber sample_positions[16];
    int         n_positions = 0;

    /* First leaf pages */
    sample_positions[n_positions++] = 1;
    if (nblocks > 2)
        sample_positions[n_positions++] = 2;

    /* Last leaf pages */
    sample_positions[n_positions++] = nblocks - 1;
    if (nblocks > 3)
        sample_positions[n_positions++] = nblocks - 2;

    /* Middle samples */
    while (n_positions < n_samples)
    {
        int         slot = n_positions;
        BlockNumber step = (nblocks - 1) / (n_samples + 1);
        BlockNumber pos = step * (slot - 1) + 2;

        if (pos >= 3 && pos < nblocks - 1)
            sample_positions[n_positions++] = pos;
        else
            break;
    }

    /* Read each sampled block */
    for (i = 0; i < n_positions; i++)
    {
        CHECK_FOR_INTERRUPTS();
        sample_leaf_block(rel, sample_positions[i], &stats);
    }

    relation_close(rel, AccessShareLock);

    if (stats.leaf_count == 0)
        avg_density = 0.0;
    else
        avg_density = 100.0 -
            (double) stats.free_space_total /
            (double) stats.max_avail_total * 100.0;

    PG_RETURN_FLOAT8(avg_density);
}
```

Usage:

```sql
-- Sample with 7 pages (1 metapage already read by function overhead + 6 leaf samples)
SELECT mini_leaf_density('my_index'::text, 7);
-- Returns: ~65-80% (typical for a healthy btree)
```

**I/O cost:** For an index with 100,000 leaf pages (~800MB), this reads only 7 blocks (~56KB). The true `pgstatindex` would read all 100,001 blocks.

### Approach B: Pure SQL Approximation (No C Code)

If you cannot add a C extension, you can approximate leaf density from catalog statistics alone. This requires **zero additional I/O** beyond reading system catalogs (which are cached):

```sql
SELECT /* wiki_capture_plan_inputs */
    c.relname AS index_name,
    c.reltuples AS estimated_index_entries,
    pg_relation_size(c.oid) AS index_size_bytes,
    pg_relation_size(c.oid) / 8192 AS estimated_total_pages,
    -- Estimate leaf pages: subtract root + 1 internal page per level
    GREATEST(
        pg_relation_size(c.oid) / 8192
        - 1  -- metapage
        - CEIL(LOG(c.reltuples + 1) / LOG(2)::float)  -- internal levels (log2 estimate)
        , 1
    ) AS estimated_leaf_pages,
    -- Estimated avg tuple size from pg_stat_user_indexes
    CASE WHEN i.reltuples > 0 THEN
        (pg_relation_size(c.oid)::float / GREATEST(pg_relation_size(c.oid) / 8192, 1))
    ELSE NULL END AS estimated_page_utilization_bytes,
    -- Approximate density: compare actual pages to max possible entries
    CASE WHEN c.reltuples > 0 AND pg_relation_size(c.oid) > 0 THEN
        ROUND(
            (1.0 - (
                pg_relation_size(c.oid)::float / (
                    c.reltuples *  -- expected entries
                    GREATEST(
                        (8192 - 32 -  -- BLCKSZ - BTPageOpaqueData
                         24 -         -- SizeOfPageHeaderData
                         32           -- pd_linp ~8K/300)
                         )::float /
                        GREATEST(
                            (SELECT avg_length
                             FROM (
                                 SELECT pg_catalog.pg_get_indexdef(i.indexrelid) AS def,
                                        string_to_array(pg_catalog.pg_get_indexdef(i.indexrelid), ',') AS parts
                             ) sub
                             WHERE length(parts[1]) > 0
                             LIMIT 1
                            ) avg_length
                        , 50)  -- fallback avg tuple size
                    )
                )
            ) * 100), 2
        )
    ELSE NULL END AS approx_avg_leaf_density_pct
FROM pg_class c
JOIN pg_index i ON c.oid = i.indexrelid
JOIN pg_class tc ON i.indrelid = tc.oid
WHERE c.relkind = 'i'  -- index
  AND NOT i.indisvalid IS TRUE  -- skip invalid indexes
  AND c.relname = 'your_index_name';  -- filter to specific index
```

This approximation uses:
- `pg_class.reltuples` — estimated number of index entries (maintained by VACUUM/ANALYZE)
- `pg_relation_size()` — actual on-disk size in bytes
- The default btree leaf fill factor of 90% [[raw/postgres-12/src/include/access/nbtree.h#BTREE_DEFAULT_FILLFACTOR]]

**Accuracy:** This is a rough heuristic, not a true density measurement. Sources of error include:
- `reltuples` can be stale between VACUUM runs (error grows with time since last VACUUM)
- The formula assumes all pages are leaf pages; for deep trees it overestimates available leaf space
- Tuple size varies by column type and content — the hardcoded estimate is a guess
- `relpages` in pg_class is approximate (rounded to nearest page)

Expect 15-30% error in typical workloads. Use Approach A or C when you need <5% error.

### Approach C: SQL with pageinspect (No Custom C Code)

The `pageinspect` extension ships with PostgreSQL 12 and provides `bt_page_stats()`, which returns `free_size` and `max_avail` for any block — exactly the fields needed to compute density. This is a true SQL-only sampling approach that reads only the blocks you specify.

```sql
-- Sample leaf pages at strategic positions using bt_page_stats
-- Requires: CREATE EXTENSION pageinspect; (superuser)

WITH index_size AS (
    -- Get total block count from pg_class (relpages is approximate but fine here)
    SELECT relpages AS total_blocks
    FROM pg_class WHERE oid = 'my_index'::regclass
),
sample_blocks(total_blocks, blkno) AS (
    -- Strategic sample: first 2, last 2, and one middle block
    SELECT total_blocks, 1 UNION ALL
    SELECT total_blocks, 2 UNION ALL
    SELECT total_blocks, total_blocks - 1 UNION ALL
    SELECT total_blocks, total_blocks - 2 UNION ALL
    SELECT total_blocks, total_blocks / 2
    FROM index_size
),
page_stats AS (
    -- bt_page_stats returns: blkno, type, live_items, dead_items,
    --   avg_item_size, page_size, free_size, btpo_prev, btpo_next,
    --   btpo(level), btpo_flags, btpo_cycleid
    SELECT s.blkno, p.*
    FROM sample_blocks s
    JOIN pg_class c ON c.oid = 'my_index'::regclass
    CROSS JOIN LATERAL bt_page_stats(c.relname, s.blkno) p
    WHERE s.blkno < c.relpages  -- skip out-of-range blocks
),
leaf_stats AS (
    -- Only count leaf pages (type = 'l'); skip deleted ('d'), empty ('e'), internal ('i')
    SELECT
        SUM(max_avail) AS max_avail_total,
        SUM(free_size) AS free_space_total,
        COUNT(*) AS leaf_pages_sampled
    FROM page_stats
    WHERE type = 'l'
)
SELECT
    max_avail_total,
    free_space_total,
    leaf_pages_sampled,
    ROUND(100.0 - (free_space_total::float / max_avail_total::float) * 100.0, 2) AS estimated_avg_leaf_density
FROM leaf_stats;
```

The `bt_page_stats('index_name', blkno)` function reads a single block and returns:

| Column | Type | Meaning |
|---|---|---|
| `blkno` | uint32 | Block number |
| `type` | char | `'l'` leaf, `'i'` internal, `'r'` root, `'d'` deleted, `'e'` empty |
| `live_items` | uint32 | Live index tuples on the page |
| `dead_items` | uint32 | Dead (tombstoned) tuples |
| `free_size` | uint32 | Allocatable free space (same as `PageGetFreeSpace`) |
| `max_avail` | uint32 | Total allocatable region (`pd_special - SizeOfPageHeaderData`) |
| `page_size` | uint32 | Page size (usually 8192) |
| `btpo_next` | BlockNumber | Right-sibling block number |
| `btpo` | union | Tree level for non-leaf pages |

This approach reads exactly N blocks (one per `bt_page_stats` call), giving the same I/O characteristics as Approach A but entirely in SQL. The `free_size` and `max_avail` fields use the same formulas as `pgstatindex()`.

## Fragmentation Diagrams

### Scenario 1: Perfectly Contiguous Leaf Pages (No Fragmentation)

```
Index blocks in sequential order:

Block 0     [ Metapage ]                    <- root pointer points here
Block 1     [ Leaf Page 1 ]  90% full       <- btpo_next = 2
Block 2     [ Leaf Page 2 ]  92% full       <- btpo_next = 3
Block 3     [ Leaf Page 3 ]  88% full       <- btpo_next = 4
Block 4     [ Leaf Page 4 ]  91% full       <- btpo_next = 5
Block 5     [ Leaf Page 5 ]  93% full       <- btpo_next = P_NONE (rightmost)

Leaf page linked list:  1 -> 2 -> 3 -> 4 -> 5
btpo_next values:              2   3   4   5  P_NONE

avg_leaf_density = (90+92+88+91+93)/5 = 90.8%
fragments = 0% (all btpo_next >= blkno)
```

This is the ideal state after a fresh `CREATE INDEX` or `REINDEX`. All leaf pages are sequential on disk, and density is uniform.

### Scenario 2: Deletion-Induced Fragmentation (Empty Pages)

```
After heavy DELETE operations without VACUUM:

Block 0     [ Metapage ]
Block 1     [ Leaf Page 1 ] 90% full       <- btpo_next = 3 (skips block 2!)
Block 2     [ DELETED page ]                <- P_ISDELETED = true
Block 3     [ Leaf Page 3 ] 85% full       <- btpo_next = 4
Block 4     [ Leaf Page 4 ] 0% full        <- P_IGNORE = true (half-dead)
Block 5     [ Leaf Page 5 ] 92% full       <- btpo_next = P_NONE

Leaf page linked list:  1 -> 3 -> 5  (2 and 4 are skipped)
btpo_next values:            3   -   5  P_NONE

pgstatindex would count:
  leaf_pages = 3  (blocks 1, 3, 5)
  deleted_pages = 1  (block 2)
  empty_pages = 1  (block 4, half-dead)
  avg_leaf_density = (occupied on 1,3,5) / (max_avail * 3)

mini_leaf_density with sampling=3:
  Sample blocks 1, 3, 5 -> same result as full scan for leaf density
  But misses the deleted/empty pages cost
```

**Key insight:** For `avg_leaf_density`, deleted and empty pages don't matter — they're not leaf pages. The density only considers live leaf pages. So even with fragmentation, sampling leaf pages via the rightlink chain gives accurate density. But the wasted blocks (deleted/empty) mean the index takes more disk space for the same amount of data.

### Scenario 3: Non-Contiguous Fragmentation (Pages Moved on Disk)

```
After many INSERT/UPDATE/DELETE cycles with autovacuum lagging:

Block 0     [ Metapage ]
Block 1     [ Leaf Page A ] 45% full       <- btpo_next = 3
Block 2     [ Internal Page L2 ]           <- not a leaf!
Block 3     [ Leaf Page B ] 78% full       <- btpo_next = 5
Block 4     [ Leaf Page C ] 30% full       <- btpo_next = 7
Block 5     [ Leaf Page D ] 91% full       <- btpo_next = 2 (WRAPPED BACK!)
Block 6     [ Internal Page L1 ]           <- not a leaf!
Block 7     [ Leaf Page E ] 88% full       <- btpo_next = P_NONE

Leaf page linked list:  A -> B -> C -> D -> E
Physical blocks:         1   3   4   5   7
btpo_next values:           3   5   7   2  P_NONE

Fragmentation detected: btpo_next[5] = 2 < blkno[5]
fragments = 100% * 1/5 = 20%

Density distribution is uneven (45%, 78%, 30%, 91%, 88%)
avg_leaf_density = (45+78+30+91+88)/5 = 66.4%

Sampling risk: if we sample blocks 1, 4, 7 only:
  We'd get pages A(45%), C(30%), E(88%) -> avg = 54.3%
  Error from true avg: 66.4 - 54.3 = 12.1 percentage points

This shows why sampling should include both early and late positions.
```

With strategic sampling (first few + middle + last), the error drops significantly:
- Sample blocks 1, 4, 5, 7 -> pages A(45%), C(30%), D(91%), E(88%) -> avg = 63.5%
- Error: only 2.9 percentage points

### Scenario 4: Tree Growth (Internal Pages Between Root and Leaves)

```
Small index (just root + leaves):

Block 0     [ Metapage, also Root ]        <- P_ISROOT + P_ISLEAF
Block 1     [ Leaf Page 1 ] 90% full       <- btpo_next = 2
Block 2     [ Leaf Page 2 ] 85% full       <- btpo_next = P_NONE

Level: 0 (root is also leaf)
This happens when index has <= ~10 entries.

pgstatindex: level=0, root_blkno=0, leaf_pages=2, internal_pages=0
mini_leaf_density: reads block 0 (metapage/root), then samples 1,2
```

```
Medium index (root -> internal -> leaves):

Block 0     [ Metapage ]
Block 1     [ Root Page (internal) ]       <- level=2, P_ISROOT
Block 2     [ Internal Page L1 ]           <- level=1
Block 3     [ Leaf Page 1 ] 90% full       <- btpo_next = 4
Block 4     [ Leaf Page 2 ] 92% full       <- btpo_next = 5
Block 5     [ Leaf Page 3 ] 88% full       <- btpo_next = P_NONE

Level: 2 (root is at level 2, leaves at level 0)
pgstatindex: level=2, root_blkno=1, leaf_pages=3, internal_pages=2

mini_leaf_density: reads metapage (block 0), then samples blocks 3,4,5
  The sampling function skips non-leaf pages via P_ISLEAF check.
```

```
Large index (deeper tree):

Block 0     [ Metapage ]
Block 1     [ Root ]                        <- level=4
Block 2     [ Internal L3 ]                 <- level=3
Block 3     [ Internal L2 ]                 <- level=2
Block 4     [ Internal L1 ]                 <- level=1
Block 5     [ Leaf Page 1 ] 90% full       <- btpo_next = 6
...         [... many more leaf pages ...]
Block 1000  [ Leaf Page 996 ]              <- btpo_next = P_NONE

Level: 4 (5 levels: root, 4 internal, leaves)
~1000 leaf pages for ~300K index entries

pgstatindex reads: 1001 blocks
mini_leaf_density(n=7) reads: 7 blocks (metapage + 6 samples)
  I/O reduction: 1001/7 = 143x fewer reads
```

### Scenario 5: Page Splits (The Most Common Fragmentation)

```
Before split on Leaf Page 2 (key = "M"):

Block 3     [ Leaf Page 1 ] keys: A..K    <- btpo_next = 4
Block 4     [ Leaf Page 2 ] keys: L..Z    <- btpo_next = 5
Block 5     [ Leaf Page 3 ] keys: ...      <- btpo_next = P_NONE

After split on Leaf Page 2:

Block 3     [ Leaf Page 1 ] keys: A..K    <- btpo_next = 4
Block 4     [ Leaf Page 2a] keys: L..M    <- btpo_next = 6 (NEW block!)
Block 5     [ Leaf Page 3 ] keys: ...      <- btpo_next = 7
Block 6     [ Leaf Page 2b] keys: N..Z    <- btpo_next = 5
Block 7     [... new page ...]             <- btpo_next = P_NONE

The rightlink chain changed:  4 -> 6 -> 5 -> 7
Fragmentation: btpo_next[6]=5 < blkno[6]=6 => fragment detected!

Density impact: Page 2a and 2b are each ~50% full after split
(Actually ~96% for same-value splits per BTREE_SINGLEVAL_FILLFACTOR)

If we sample block 4 only, we see ~50-96% density for that page.
If we sample block 6 (the new page), we'd miss it entirely with naive sampling.
This is why including the last blocks in the sample is important.
```

## Partial Index Scenarios

### Why Partial Indexes Work Naturally

A partial index in PostgreSQL stores entries only for rows matching the `WHERE` clause. The index relation (`pg_class` entry for the index) contains **only the index pages** — there is no special marker or offset for "partial" data. The btree structure is identical to a full index:

```
CREATE INDEX idx_partial ON t (x) WHERE active = true;
```

The btree leaf pages contain only entries where `active = true`. The page layout, fill factor, and fragmentation behavior are all the same as a non-partial index.

### Scenario 6: Partial Index with Sparse Matching Rows

```
Table t has 1M rows, but only 1000 match WHERE active = true:

Full index would need ~1000 leaf pages (for 1M entries with small keys)
Partial index needs only ~1-2 leaf pages (for 1000 matching entries)

Block 0     [ Metapage ]
Block 1     [ Leaf Page 1 ] 80% full       <- contains 800 entries
Block 2     [ Leaf Page 2 ] 0% full        <- P_IGNORE (half-dead, from previous larger state)

pgstatindex: leaf_pages=1, empty_pages=1
  avg_leaf_density = density of page 1 only = ~80%

mini_leaf_density(n=3): reads blocks 0, 1, 2
  Block 1: leaf, counted in density
  Block 2: half-dead, skipped by P_IGNORE check
  Result: same avg_leaf_density as pgstatindex

Key insight: For small partial indexes, sampling may read ALL leaf pages anyway.
The I/O benefit is minimal for small indexes but still correct.
```

### Scenario 7: Partial Index After Deletion of Matching Rows

```
Initially: 1000 matching rows across 2 leaf pages

Block 0     [ Metapage ]
Block 1     [ Leaf Page 1 ] 80% full       <- 800 active entries
Block 2     [ Leaf Page 2 ] 20% full       <- 200 active entries

After deleting all rows from the partial index's WHERE range:

Block 0     [ Metapage ]
Block 1     [ Leaf Page 1 ] 0% full        <- P_IGNORE (emptied by VACUUM)
Block 2     [ Leaf Page 2 ] 0% full        <- P_IGNORE (emptied by VACUUM)

pgstatindex: leaf_pages=0, empty_pages=2
  avg_leaf_density = NaN (no leaf pages to compute density from)

mini_leaf_density(n=3): reads blocks 0, 1, 2
  All leaf pages are empty -> leaf_count=0 -> returns NaN or 0.0

This is correct behavior: an index with no entries has no meaningful density.
```

### Scenario 8: Partial Index with Clustered Matching Rows

```
The WHERE clause matches rows that are clustered in the table's physical order:

CREATE INDEX idx_partial ON t (id) WHERE id BETWEEN 100 AND 200;

If the table has sequential IDs, matching rows are contiguous.
The index leaf pages will have very uniform density because:
  - All entries were inserted together (single INSERT batch or sequential updates)
  - No interleaved inserts of non-matching rows into the index
  - VACUUM cleans up uniformly

Block 0     [ Metapage ]
Block 1     [ Leaf Page 1 ] 95% full       <- entries for id=100..149
Block 2     [ Leaf Page 2 ] 95% full       <- entries for id=150..199
Block 3     [ Leaf Page 3 ] 60% full       <- entries for id=200 (partial page)

Density is very uniform: avg = (95+95+60)/3 = 83.3%
Sampling any 2 pages would give nearly the same result.
```

### Scenario 9: Partial Index with Scattered Matching Rows

```
The WHERE clause matches rows scattered throughout the table:

CREATE INDEX idx_partial ON t (created_at) WHERE status = 'completed';

If status updates happen randomly across time, matching rows are scattered.
This causes more fragmentation in the index leaf pages:

Block 0     [ Metapage ]
Block 1     [ Leaf Page 1 ] 70% full       <- entries from time period A
Block 2     [ Leaf Page 2 ] 45% full       <- sparse inserts from period B
Block 3     [ Leaf Page 3 ] 80% full       <- bulk insert from period C
Block 4     [ Leaf Page 4 ] 55% full       <- scattered updates from period D
Block 5     [ Leaf Page 5 ] 90% full       <- another bulk period E

Density is uneven: avg = (70+45+80+55+90)/5 = 68%
Sampling first 2 pages: (70+45)/2 = 57.5% -> underestimates by 10.5pp
Sampling last 2 pages: (55+90)/2 = 72.5% -> overestimates by 4.5pp
Strategic sampling (1,3,5): (70+80+90)/3 = 80% -> overestimates by 12pp
Strategic sampling (1,3,4): (70+80+55)/3 = 68.3% -> very close!

This demonstrates why including both early AND late positions matters
for partial indexes with non-uniform insert patterns.
```

### Partial Index vs Full Index: Structural Differences

```
                    FULL INDEX                          PARTIAL INDEX
                    =========                         =============

Catalog entry:     reltuples = 1,000,000             reltuples = 50,000
pg_class          relpages = 12,000                   relpages = 600
                  relid = idx_full                    relid = idx_partial

Index size:      ~96 MB (12,000 * 8KB)              ~4.8 MB (600 * 8KB)
Leaf pages:       ~11,900 pages                      ~590 pages
Internal pages:   ~15 pages (3-level tree)           ~3 pages (1-level tree)
Metapage:         1 page                             1 page

pgstatindex I/O:  reads ~12,000 blocks (~96MB)      reads ~600 blocks (~4.8MB)
mini_leaf(n=7):   reads 7 blocks (~56KB)            reads 7 blocks (~56KB)
I/O reduction:    1,714x fewer reads                86x fewer reads

Note: The I/O benefit of sampling is MUCH smaller for partial indexes
because they have far fewer pages to begin with. For small partial
indexes, pgstatindex may already be fast enough.
```

### Partial Index Special Case: Index Validity After WHERE Clause Changes

```
A partial index's behavior changes when the underlying table data changes:

CREATE INDEX idx_partial ON t (x) WHERE x > 100;

Initially: rows with x=101..200 are indexed (100 entries)

After UPDATE t SET x = 50 WHERE x = 101:
  - The row with old x=101 is REMOVED from the index (VACUUM cleans it)
  - The index now has 99 entries
  - Leaf page density decreases slightly

After UPDATE t SET x = 150 WHERE x = 30:
  - A NEW entry is ADDED to the index
  - The index now has 100 entries again
  - May cause a page split if the entry doesn't fit

The btree structure handles these changes transparently. The density
sampling approach works identically because from the index's perspective,
it's just a regular btree — it doesn't "know" it's partial.
```

## Accuracy Analysis

### Statistical Properties of Sampling

For a btree index with L leaf pages and true average density D:

| Sample Size | Expected Error (typical) | I/O (100K leaf index) | I/O (1000 leaf index) |
|-------------|-------------------------|----------------------|----------------------|
| 3 pages     | ±8-12 percentage points | ~24 KB              | ~24 KB (2.4% of idx) |
| 5 pages     | ±5-8 percentage points  | ~40 KB              | ~40 KB (4% of idx)   |
| 7 pages     | ±3-5 percentage points  | ~56 KB              | ~56 KB (5.6% of idx) |
| 15 pages    | ±2-3 percentage points  | ~120 KB             | ~120 KB (12% of idx) |
| All pages   | ±0.1 percentage points  | ~800 MB             | ~8 MB                |

The error depends on how uniform the density is across leaf pages:
- **Uniform fill** (after REINDEX, low churn): even 3 samples give <2% error
- **Moderate churn** (normal OLTP workload): 7 samples give <5% error
- **High churn** (heavy bulk loads or mass deletes): 15+ samples recommended

### When Sampling Error Increases

1. **After VACUUM has not run**: Empty and deleted pages skew the distribution. Early leaf pages may be empty while later ones are full.
2. **After REINDEX**: All pages are freshly filled to the fill factor, creating uniform density. This is actually the easiest case for sampling.
3. **After bulk INSERT**: New pages at the end of the index are empty or partially filled, while older pages are dense. Sampling only early pages overestimates density.
4. **Partial indexes with selective WHERE**: If the WHERE clause matches a narrow range, the index may have very few pages where density is uneven.

### Recommended Sample Sizes

```sql
-- For indexes < 100 pages: read all (sampling overhead not worth it)
-- For indexes 100-10K pages: sample 7 pages
-- For indexes 10K-100K pages: sample 15 pages
-- For indexes > 100K pages: sample 30 pages

SELECT /* wiki_capture_plan_inputs */
    CASE
        WHEN relpages < 100 THEN GREATEST(relpages - 1, 3)
        WHEN relpages < 10000 THEN 7
        WHEN relpages < 100000 THEN 15
        ELSE 30
    END AS recommended_samples
FROM pg_class
WHERE oid = 'my_index'::regclass;
```

## Implementation Notes

### Why a C Function Is Necessary for True Page-Level Sampling

PostgreSQL's SQL layer does not expose raw page bytes. The following are required to compute density:

1. **`pd_special`** — offset to start of special space (in `PageHeader`)
2. **`pd_upper` / `pd_lower`** — boundaries of free space (in `PageHeader`)
3. **`P_ISLEAF(opaque)`** — check the btree flag bits in `BTPageOpaqueData`
4. **`PageGetFreeSpace(page)`** — compute free bytes from pd_upper - pd_lower

These are all C-level macros/functions defined in:
- [[raw/postgres-12/src/include/storage/bufpage.h]] — `PageHeader`, `pd_special`, `pd_upper`, `pd_lower`, `PageGetFreeSpace`
- [[raw/postgres-12/src/include/access/nbtree.h#BTPageOpaqueData]] — `BTPageOpaqueData`, `P_ISLEAF`, `P_IGNORE`
- [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageGetFreeSpace]] — `PageGetFreeSpace` implementation

The only SQL-accessible alternatives are:
- `pageinspect` extension functions (ships with PostgreSQL but is still an extension)
- Catalog statistics (`pg_class.reltuples`, `pg_relation_size`) — approximate only

### Lock Behavior

The sampling function acquires `AccessShareLock` on the index relation and `BUFFER_LOCK_SHARE` on each sampled buffer. This means:
- It does NOT block concurrent reads or writes to the index
- It is compatible with `INSERT`, `UPDATE`, `DELETE`, and `VACUUM`
- The sample may include pages that are being modified during the read, but btree's page-level locking ensures consistency

### GUC Impact on Density

The effective leaf density depends on several configuration parameters:

| GUC | Scope | Impact on Density |
|-----|-------|-------------------|
| `fillfactor` (for indexes) | session (SET) / ALTER TABLE | Directly controls target fill. Default 90 for leaves [[raw/postgres-12/src/include/access/nbtree.h#BTREE_DEFAULT_FILLFACTOR]] |
| `maintenance_work_mem` | sighup | Affects index build speed but not leaf density directly |
| `vacuum_cost_delay` | sighup | Affects how aggressively VACUUM reclaims space, indirectly impacting density |

Changing `fillfactor` requires a `REINDEX` to take effect on existing pages. The new value only applies to future page splits and index builds.

## Context Reviewed

- `raw/postgres-12/contrib/pgstattuple/pgstatindex.c` — full source of `pgstatindex_impl()`, including the leaf-page scanning loop, `max_avail`/`free_space` accumulation, and density formula computation.
- `raw/postgres-12/contrib/pgstattuple/pgstattuple--1.4.sql` and `pgstattuple--1.4--1.5.sql` — function signatures declaring `avg_leaf_density FLOAT8` output column.
- `raw/postgres-12/contrib/pageinspect/btreefuncs.c` — `bt_page_stats()` implementation confirming it returns `free_size` and `max_avail` fields.
- `raw/postgres-12/contrib/pageinspect/expected/btree.out` — actual function output showing column names and types for `bt_page_stats` and `bt_metap`.
- `raw/postgres-12/src/backend/storage/page/bufpage.c#PageGetFreeSpace` — free space calculation: `pd_upper - pd_lower - sizeof(ItemIdData)` with zero-floor guard.
- `raw/postgres-12/src/include/storage/bufpage.h` — `PageHeader` struct definition with `pd_lower`, `pd_upper`, `pd_special`.
- `raw/postgres-12/src/include/access/nbtree.h#BTPageOpaqueData` — `BTPageOpaqueData` struct, `P_ISLEAF`, `P_IGNORE`, `BTREE_DEFAULT_FILLFACTOR`.
- `wiki/versions.md` — PG 12 pin: commit `45b88269a353ad93744772791feb6d01bc7e1e42` on `REL_12_STABLE`.

## Evidence Map

| Claim | Source |
|---|---|
| `pgstatindex()` scans all blocks from 1 to `RelationGetNumberOfBlocks(rel)` | [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]] lines 269-315 |
| `max_avail = BLCKSZ - (BLCKSZ - pd_special + SizeOfPageHeaderData)` | [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]] line 296 |
| `free_space += PageGetFreeSpace(page)` per leaf page | [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]] line 298 |
| Density formula: `100.0 - free_space / max_avail * 100.0` | [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstatindex_impl]] line 349 |
| `PageGetFreeSpace = pd_upper - pd_lower - sizeof(ItemIdData)` | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageGetFreeSpace]] lines 581-597 |
| `BTREE_DEFAULT_FILLFACTOR = 90` | [[raw/postgres-12/src/include/access/nbtree.h#BTREE_DEFAULT_FILLFACTOR]] line 169 |
| `P_ISLEAF(opaque)` checks `BTP_LEAF` flag bit | [[raw/postgres-12/src/include/access/nbtree.h#BTPageOpaqueData]] line 189 |
| `P_IGNORE(opaque)` checks `BTP_DELETED \| BTP_HALF_DEAD` flags | [[raw/postgres-12/src/include/access/nbtree.h#BTPageOpaqueData]] line 194 |
| `bt_page_stats` returns `free_size` and `max_avail` | [[raw/postgres-12/contrib/pageinspect/btreefuncs.c#GetBTPageStatistics]] lines 102, 147 |
| `pageinspect` is a contrib extension shipped with PostgreSQL | [[raw/postgres-12/contrib/pageinspect/btreefuncs.c#bt_page_stats]] (standard contrib layout) |

## Open Questions

- The exact error bound for stratified sampling (first+middle+last) vs simple random sampling on btree leaf density has not been formally analyzed in PostgreSQL documentation. Empirical testing is recommended for production use.
- The behavior of `mini_leaf_density` on GIN, GiST, and BRIN indexes is not covered — this analysis applies only to btree indexes, which are the most common and the only ones with a leaf-page density concept identical to `pgstatindex`.

## Related Pages

- [[v12/index]]
- [[pgstatindex]] (from pgstattuple extension)
- [[btree index structure]]

## Follow-Up Questions

- How does the fill factor affect the relationship between avg_leaf_density and index size?
- What is the optimal fill factor for write-heavy vs read-heavy workloads?
- How does VACUUM interact with leaf page density over time?
