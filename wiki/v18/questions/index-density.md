# Index Density with I/O Fraction

**version:** v18  
**status:** filed  
**date:** 2026-04-30

## Question

How to calculate `avg_leaf_density` for a B-tree index similar to `pgstattuple` output, but as a fraction of I/O using only PostgreSQL 18 core features (no additional dependencies)?

## Answer

### Core Formula

Use `pgstattuple` module (contrib) with the Mackert and Lohman I/O model from `costsize.c`:

```sql
SELECT 
    -- Physical leaf density (empty pages / total leaf pages)
    (COALESCE(empty_pages, 0) :: float8 / NULLIF(leaf_pages + empty_pages, 0)) AS avg_leaf_density,
    
    -- I/O fraction using effective_cache_size (Mackert & Lohman formula)
    (SELECT 
        CASE 
            WHEN T <= b THEN 
                LEAST((2.0 * T * tuples_fetched) / (2.0 * T + tuples_fetched), T)
            ELSE
                CASE 
                    WHEN tuples_fetched <= (2.0 * T * b) / (2.0 * T - b) THEN
                        (2.0 * T * tuples_fetched) / (2.0 * T + tuples_fetched)
                    ELSE
                        b + (tuples_fetched - (2.0 * T * b) / (2.0 * T - b)) * (T - b) / T
                END
        END
    FROM (
        SELECT 
            GREATEST(1.0, relpages) AS T,
            (effective_cache_size * relpages)::double precision / 
                GREATEST(1.0, relpages + index_pages) AS b,
            1.0 AS tuples_fetched,
            relpages AS index_pages
        FROM pg_class
        WHERE relkind = 'i' AND oid = 'your_index_name'::regclass
    ) AS params
    ) AS io_fraction;
```

### Key Insights

#### 1. pgstattuple Provides Index Statistics

**Source:** `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:77-92`

The `BTIndexStat` structure contains:
- `leaf_pages` - number of leaf pages in the B-tree index
- `empty_pages` - number of deleted/ignored pages (P_IGNORE state)
- `internal_pages` - internal (non-leaf) pages
- `deleted_pages` - pages marked as deleted (P_ISDELETED)
- `fragments` - fragmentation count (lines 315-320)

**Source:** `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:280-328`

The function scans ALL physical pages in the index (except metapage) and counts each page type. It does NOT filter based on index predicates.

#### 2. Correlation Factor Is NOT for Indexes

**Source:** `raw/postgres-18/src/include/catalog/pg_statistic.h:212-222`

```c
/* A "correlation" slot describes the correlation between the physical order
 * of table tuples and the ordering of data values of this column... */
#define STATISTIC_KIND_CORRELATION  3
```

The `STATISTIC_KIND_CORRELATION` statistic is for **table columns**, not indexes. It measures:
- Correlation between physical tuple order and data value ordering
- Range from +1 to -1
- Used for join selectivity estimation

There is **no equivalent index-level correlation statistic** in `pg_statistic`.

#### 3. I/O Estimation Formula in costsize.c

**Source:** `raw/postgres-18/src/backend/optimizer/path/costsize.c:870-961`

Function `index_pages_fetched()` implements the Mackert and Lohman approximation:

> "We use an approximation proposed by Mackert and Lohman, 'Index Scans Using a Finite LRU Buffer: A Validated I/O Model', ACM Transactions on Database Systems, Vol. 14, No. 3, September 1989, Pages 401-424."

The formula estimates pages fetched after accounting for cache effects:

```
PF = min(2TNs/(2T+Ns), T)           when T <= b
     = 2TNs/(2T+Ns)                 when T > b and Ns <= 2Tb/(2T-b)
     = b + (Ns - 2Tb/(2T-b))*(T-b)/T  when T > b and Ns > 2Tb/(2T-b)

where:
  T = # pages in table
  N = # tuples in table
  s = selectivity = fraction of table to be scanned
  b = # buffer pages available (pro-rated effective_cache_size)
```

The function is called from:
- `raw/postgres-18/src/backend/optimizer/path/costsize.c:690,714,730` - index path costing
- `raw/postgres-18/src/backend/utils/adt/selfuncs.c:7207,8572,8577,8628` - other selectivity estimations

### Partial Index Caveats

#### The Problem

**Source:** `raw/postgres-18/src/include/catalog/pg_index.h:60-61`

```c
pg_node_tree indpred;   /* expression tree for predicate, if a partial
                          * index; else NULL */
```

Partial indexes have a `WHERE` predicate, but:

1. **Physical storage doesn't change** - PostgreSQL allocates pages regardless of predicate
2. **Many pages may be empty** - pages reserved for rows that don't match the predicate
3. **pgstattuple sees ALL physical pages** - it doesn't know about the predicate

#### Example Scenario

```sql
CREATE INDEX users_adults_idx ON users(id) 
WHERE age > 18;
```

With 100,000 users, only 20,000 adults:

| Metric | pgstattuple Shows | Interpretation |
|--------|-------------------|----------------|
| `leaf_pages` | ~2000 | Physical storage allocated |
| `empty_pages` | ~1500 | Pages reserved but unused (age ≤ 18) |
| `avg_leaf_density` | ~0.57 | **Misleading!** |

The actual **logical density** should reflect that only 20% of rows are indexed, but `avg_leaf_density` shows physical page utilization.

#### Recommendation for Partial Indexes

Don't use `avg_leaf_density` for partial indexes. Instead:

```sql
-- Check if index is partial
SELECT 
    c.relname,
    i.indpred IS NOT NULL AS is_partial_index
FROM pg_class c
JOIN pg_index i ON c.oid = i.indexrelid
WHERE c.oid = 'your_index_name'::regclass;
```

For partial indexes, use pgstattuple metrics for:
- **Fragmentation detection**: `fragments` count
- **Physical utilization**: `empty_pages` vs `leaf_pages`  
- **Bloat detection**: `max_avail` and `free_space`

### Alternative: System Catalog Only

Without pgstattuple (requires superuser):

```sql
SELECT 
    relpages,
    reltuples,
    -- Very rough density estimate (not as accurate)
    CASE 
        WHEN reltuples > 0 AND relpages > 0 
        THEN LEAST(1.0, reltuples::float8 / (relpages * 1000.0))
        ELSE NULL
    END AS rough_density_estimate
FROM pg_class 
WHERE relkind = 'i' AND oid = 'your_index_name'::regclass;
```

### Wiki Status

This question page was created to document:
- Index density calculation methods
- I/O estimation using Mackert & Lohman formula
- Partial index behavior with pgstattuple
- Relationship between pgstattuple and pg_statistic

**Related open questions in `wiki/v18/index.md`:**

> "Which lower-level storage paths should be traced after the DML code paths: heap insert, heap update, heap delete, WAL emission, or **index maintenance**?"

This question addresses index maintenance and statistics, which are foundational for understanding index density and optimization.

## Citations

- `raw/postgres-18/contrib/pgstattuple/pgstatindex.c:264-328` - index statistics structure and page scanning
- `raw/postgres-18/src/include/catalog/pg_statistic.h:212-222` - STATISTIC_KIND_CORRELATION definition
- `raw/postgres-18/src/backend/optimizer/path/costsize.c:870-961` - index_pages_fetched() implementation
- `raw/postgres-18/src/include/catalog/pg_index.h:60-61` - partial index predicate field
- `wiki/v18/index.md:56` - open question about index maintenance coverage
