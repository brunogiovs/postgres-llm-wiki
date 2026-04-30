---
type: subsystem
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# Analyzer

## Role

The analyzer transforms a raw parse tree into a [[shared/concepts/query-tree|Query]] tree. In PostgreSQL 18, `pg_analyze_and_rewrite_fixedparams`, `pg_analyze_and_rewrite_varparams`, and `pg_analyze_and_rewrite_withcb` call the corresponding `parse_analyze_*` function before invoking query rewrite.

`src/backend/parser/analyze.c` describes the subsystem as transforming raw parse trees into query trees. It also documents an important behavioral split: optimizable statements are semantically analyzed and suitable locks are obtained on referenced tables, while most utility commands are placed into a dummy `CMD_UTILITY` `Query` node without the same transformation.

## Major Entry Points

| Symbol | File | Purpose |
|---|---|---|
| `pg_analyze_and_rewrite_fixedparams` | `src/backend/tcop/postgres.c` | Top-level wrapper for parse analysis with known parameter types. |
| `pg_analyze_and_rewrite_varparams` | `src/backend/tcop/postgres.c` | Top-level wrapper when parameter types may be inferred from context. |
| `pg_analyze_and_rewrite_withcb` | `src/backend/tcop/postgres.c` | Top-level wrapper using a parser setup callback. |
| `parse_analyze_fixedparams` | `src/backend/parser/analyze.c` | Creates a `ParseState`, transforms the raw tree, optionally applies fixed parameter typing, and returns a [[shared/concepts/query-tree|Query]]. |
| `parse_analyze_varparams` | `src/backend/parser/analyze.c` | Variant that can infer and update parameter types. |
| `parse_analyze_withcb` | `src/backend/parser/analyze.c` | Variant that delegates parameter resolution to a callback. |
| `transformTopLevelStmt` | `src/include/parser/analyze.h` | Declared top-level raw-statement transformer used by parse analysis. |
| `post_parse_analyze_hook` | `src/backend/parser/analyze.c` and `src/include/parser/analyze.h` | Hook called at the end of parse analysis when installed. |

## Core Data Structures

- `ParseState` - analysis context created by `make_parsestate` in `parse_analyze_*`.
- [[shared/concepts/query-tree|Query]] - analyzed query tree returned by the analyzer.
- `QueryEnvironment` - optional environment passed through the parse-analysis entry points.
- `JumbleState` - created when query ID generation is enabled in `parse_analyze_*`.

## Related Concepts

- Raw parse tree
- [[shared/concepts/query-tree|Query]] tree
- `ParseState`
- Parameter typing
- Query ID jumbling
- Table locks during parse analysis

The core `Query` tree is now documented as a shared concept; remaining items should be promoted when they recur across more traces.

## Important Code Paths

- [[v18/code-paths/simple-select-query]] - Raw parse tree to `Query` for a simple `SELECT`.
- [[v18/code-paths/insert-path]] - `T_InsertStmt` through `transformInsertStmt`.
- [[v18/code-paths/update-path]] - `T_UpdateStmt` through `transformUpdateStmt`.
- [[v18/code-paths/delete-path]] - `T_DeleteStmt` through `transformDeleteStmt`.
- Utility command handling: later investigation; `analyze.c` says most utility commands are hung off a dummy `CMD_UTILITY` query.

## Differences Across Supported Versions

Only PostgreSQL 18 is currently supported.

## Source References

- `raw/postgres-18/src/backend/tcop/postgres.c:pg_analyze_and_rewrite_fixedparams`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_analyze_and_rewrite_varparams`
- `raw/postgres-18/src/backend/tcop/postgres.c:pg_analyze_and_rewrite_withcb`
- `raw/postgres-18/src/backend/parser/analyze.c:parse_analyze_fixedparams`
- `raw/postgres-18/src/backend/parser/analyze.c:parse_analyze_varparams`
- `raw/postgres-18/src/backend/parser/analyze.c:parse_analyze_withcb`
- `raw/postgres-18/src/include/parser/analyze.h`
- `raw/postgres-18/src/backend/parser/README`

## Open Questions

- Which analyzer transform functions are traversed by a minimal `SELECT`?
- Where are target-list and range-table entries finalized for the simple `SELECT` path?
- Which locks are acquired during parse analysis for each DML statement type?
