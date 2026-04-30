---
type: subsystem
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# Rewriter

## Role

The rewriter takes analyzed [[shared/concepts/query-tree|Query]] trees and applies PostgreSQL's query rewrite system. In PostgreSQL 18, `pg_rewrite_query` skips rewrite for `CMD_UTILITY` queries and calls `QueryRewrite` for regular queries.

`QueryRewrite` is the primary entry point in `src/backend/rewrite/rewriteHandler.c`. Its comment says it rewrites one query and may return zero, one, or many queries. The function first applies non-`SELECT` rules through `RewriteQuery`, then applies retrieve-instead-retrieve rules through `fireRIRrules`, and finally determines which resulting query may set the command tag.

## Major Entry Points

| Symbol | File | Purpose |
|---|---|---|
| `pg_rewrite_query` | `src/backend/tcop/postgres.c` | Top-level wrapper called after parse analysis. |
| `QueryRewrite` | `src/backend/rewrite/rewriteHandler.c` | Primary rewriter entry point for regular queries. |
| `RewriteQuery` | `src/backend/rewrite/rewriteHandler.c` | Internal recursive rule-application routine. |
| `AcquireRewriteLocks` | `src/backend/rewrite/rewriteHandler.c` | Acquires locks for query trees that did not just come from the parser. |
| `fireRIRrules` | `src/backend/rewrite/rewriteHandler.c` | Applies retrieve-instead-retrieve rules. |
| `QueryRewrite` and `AcquireRewriteLocks` | `src/include/rewrite/rewriteHandler.h` | Public rewriter API declarations. |

## Core Data Structures

- [[shared/concepts/query-tree|Query]] - input and output query tree type for the rewriter.
- `rewrite_event` - local recursion-detection structure in `rewriteHandler.c`.
- `CommonTableExpr` - handled recursively by `RewriteQuery` for data-modifying CTEs.
- `RangeTblEntry` - processed by `AcquireRewriteLocks` when acquiring relation locks and fixing stored rule state.

## Related Concepts

- Query rewrite rules
- [[shared/concepts/query-tree|Query]] tree
- Retrieve-instead-retrieve rule
- View expansion
- Row security
- Command tag ownership

`Query` is now documented as a shared concept; rewrite rules, view expansion, and row security remain future concept candidates.

## Important Code Paths

- [[v18/code-paths/simple-select-query]] - Rewriter position in a simple `SELECT`.
- [[v18/code-paths/insert-path]] - Rewriter position in simple `INSERT`.
- [[v18/code-paths/update-path]] - Rewriter position in simple `UPDATE`.
- [[v18/code-paths/delete-path]] - Rewriter position in simple `DELETE`.
- DML rewrite for `MERGE`: later code-path page.
- View rewrite and row security interactions: later subsystem deep dives.

## Differences Across Supported Versions

Only PostgreSQL 18 is currently supported.

## Source References

- `raw/postgres-18/src/backend/tcop/postgres.c:pg_rewrite_query`
- `raw/postgres-18/src/backend/rewrite/rewriteHandler.c:QueryRewrite`
- `raw/postgres-18/src/backend/rewrite/rewriteHandler.c:RewriteQuery`
- `raw/postgres-18/src/backend/rewrite/rewriteHandler.c:AcquireRewriteLocks`
- `raw/postgres-18/src/include/rewrite/rewriteHandler.h`
- `raw/postgres-18/src/backend/rewrite/rowsecurity.c`

## Open Questions

- What exact rewrite work happens for a simple `SELECT` without views, rules, or row security?
- Which files should own view expansion details: `rewriteHandler.c`, `rewriteManip.c`, or separate file pages?
- How should row security be represented: as part of rewriter, planner, executor, or a cross-cutting concept?
