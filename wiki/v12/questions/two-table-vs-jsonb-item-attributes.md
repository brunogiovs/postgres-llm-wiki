---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Two-table item/item_attributes vs single table with jsonb item_attributes

## Question

In PostgreSQL 12, what are the comprehensive pros and cons of having two separate tables (`item` and `item_attributes`) versus a single `item` table with `item_attributes` stored as a `jsonb` column?

## Answer

The choice between normalized relational tables and denormalized JSON storage depends on your data access patterns, schema evolution requirements, and performance constraints. Both approaches have distinct trade-offs in PostgreSQL 12.

## Two-Table Approach: item + item_attributes

### Pros

- **Schema enforcement and data integrity**: Strict column types and constraints prevent invalid data entry. Foreign keys, check constraints, and not-null constraints work naturally.
- **Standard SQL querying**: Simple joins and WHERE clauses work efficiently. No need to learn JSON operators.
- **Optimized storage for dense data**: When most items have most attributes, this avoids JSON overhead. Each attribute column can be individually compressed and indexed.
- **Type safety**: PostgreSQL's type system prevents type mismatches. Numeric attributes stay numeric, dates stay dates.
- **Simple indexing**: B-tree, hash, or other standard indexes work directly on attribute columns. Partial indexes can target specific attribute combinations.
- **ACID compliance**: All constraints and triggers work as expected across the normalized schema.

### Cons

- **Schema evolution complexity**: Adding new attributes requires DDL changes (`ALTER TABLE ADD COLUMN`). This blocks concurrent queries during the operation.
- **Sparse data inefficiency**: Items with few attributes waste space storing NULLs in unused columns.
- **Query complexity for dynamic attributes**: Finding items with specific attribute combinations requires joins and dynamic SQL generation.
- **Migration overhead**: Changing attribute definitions (type, constraints) requires data migration scripts.

## Single Table with jsonb Approach

### Pros

- **Schema flexibility**: Add new attributes without DDL changes. Store arbitrary key-value pairs in the jsonb column.
- **Efficient sparse storage**: Only store attributes that exist. No NULL padding for missing attributes.
- **Rich querying capabilities**: PostgreSQL 12's jsonb operators enable complex queries:
  - `->` and `->>` for key access and text extraction
  - `@>` and `<@` for containment checks
  - `?`, `?|`, `?&` for key existence tests
  - `jsonb_object_keys()`, `jsonb_array_length()`, `jsonb_each()` for introspection
- **Advanced indexing**: GIN indexes with `jsonb_ops` operator class support efficient lookups on keys and values. The `jsonb_path_ops` variant optimizes path-specific queries at the cost of general containment queries.
- **Atomic updates**: `jsonb_set()`, `jsonb_insert()`, and `||` operator allow modifying individual keys without rewriting the entire document.
- **Storage efficiency**: jsonb's binary format is more compact than text JSON and supports internal compression.

### Cons

- **No schema enforcement**: Invalid keys, wrong types, or missing required attributes can be stored. Application code must validate jsonb content.
- **Query performance**: JSON operators are slower than direct column access. Complex expressions may not use indexes effectively.
- **Indexing complexity**: GIN indexes are larger and slower to update than B-tree indexes. Reindexing after bulk loads is often necessary.
- **Type loss**: All values become JSON types (string, number, boolean, null). Numeric precision may be lost, dates become strings.
- **Limited constraints**: Check constraints on jsonb columns are possible but complex. Foreign key relationships to jsonb content are impossible.
- **Tool ecosystem**: Many ORMs and reporting tools don't handle jsonb well. Schema introspection tools may not understand the dynamic structure.

## Performance Considerations

### Two-Table Performance
- Excellent for OLTP workloads with predictable queries
- Simple B-tree indexes provide fast equality and range lookups
- Foreign key joins are optimized by PostgreSQL's query planner
- MVCC works efficiently with row-level locking

### jsonb Performance
- Good for OLAP and document-like workloads
- GIN indexes enable fast existence checks and containment queries
- Poor for exact value matches on large datasets without proper indexing
- jsonb operations may trigger full table scans if not indexed

### jsonb Update Performance Implications

When only small parts of jsonb attributes change, PostgreSQL 12 incurs significant performance costs because the entire jsonb value must be rewritten:

- **Full Reconstruction**: Functions like `jsonb_set()` create completely new jsonb binary values even for single-attribute updates. The `setPath()` function rebuilds the entire jsonb structure from scratch [[raw/postgres-12/src/backend/utils/adt/jsonfuncs.c#4679]].

- **TOAST Overhead**: Values exceeding ~2KB trigger TOAST operations where small changes require compressing and storing the entire new jsonb value in a separate TOAST table, involving additional I/O operations [[raw/postgres-12/src/include/access/tuptoaster.h#55]].

- **Index Maintenance**: GIN indexes require complete reindexing of the new value, more expensive than incremental B-tree updates for traditional columns.

- **MVCC/WAL Impact**: Full new jsonb values increase WAL volume and create larger row versions.

Mitigation strategies include using `jsonb_set()` for targeted updates, considering separate columns for frequently updated attributes, and batching multiple changes.

## Migration Between Approaches

Converting from two-table to jsonb requires aggregating attributes into JSON objects. The reverse migration requires parsing jsonb and distributing values across columns.

## Recommendation

Choose the two-table approach when:
- Schema is stable and well-understood
- Data integrity is critical
- Most queries are simple attribute lookups
- You need strong typing and constraints

Choose jsonb when:
- Schema evolves frequently
- Attributes are sparse or user-defined
- Complex nested queries are common
- Document-like storage fits your use case

## Context Reviewed

- PostgreSQL 12 jsonb implementation in `src/backend/utils/adt/jsonb.c` and `src/include/utils/jsonb.h`
- jsonb operators and functions tested in `src/test/regress/sql/jsonb.sql`
- GIN indexing support in `src/backend/utils/adt/jsonb_gin.c` with `jsonb_ops` and `jsonb_path_ops` operator classes
- jsonb storage format provides binary decomposition for efficient access

## Evidence Map

- jsonb type definition and operators: [[raw/postgres-12/src/include/utils/jsonb.h]]
- jsonb implementation: [[raw/postgres-12/src/backend/utils/adt/jsonb.c]]
- jsonb GIN indexing: [[raw/postgres-12/src/backend/utils/adt/jsonb_gin.c]]
- jsonb test coverage: [[raw/postgres-12/src/test/regress/sql/jsonb.sql]]

## Open Questions

- Performance benchmarks comparing the two approaches at scale
- Impact of jsonb compression vs normalized column compression
- Migration strategies for large datasets