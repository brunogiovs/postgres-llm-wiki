---
type: subsystem
version: 18
pinned_commit: 6cb307251c5c6261286c1566496920976640108e
verified: true
---

# Parser

## Role

The parser subsystem turns SQL text into raw parse trees. In PostgreSQL 18, the top-level backend wrapper `pg_parse_query` calls `raw_parser(query_string, RAW_PARSE_DEFAULT)` to parse a query string into a list of raw parse trees.

The raw parser is deliberately syntax-level. `src/backend/parser/parser.c` says the grammar is not allowed to perform table access, and the returned structures are raw parse trees that still need parse analysis.

## Major Entry Points

| Symbol | File | Purpose |
|---|---|---|
| `pg_parse_query` | `src/backend/tcop/postgres.c` | Top-level backend wrapper that calls the raw parser for a query string. |
| `raw_parser` | `src/backend/parser/parser.c` | Main raw parser entry point; performs lexical and grammatical analysis and returns raw parse trees. |
| `raw_parser` | `src/include/parser/parser.h` | Public parser API declaration. |
| `base_yylex` | `src/backend/parser/parser.c` | Token filter between the grammar and core lexer. |
| `core_yylex` | `src/backend/parser/scan.l` | Core lexer used by `base_yylex`. |
| `base_yyparse` | generated from `src/backend/parser/gram.y` | Bison parser invoked by `raw_parser`. |

## Core Data Structures

- `RawStmt` - raw statement node produced before parse analysis; referenced by `src/include/parser/analyze.h` as input to parse analysis.
- `RawParseMode` - controls what form of string `raw_parser` accepts; defined in `src/include/parser/parser.h`.
- `yyextra.parsetree` - parser result list returned by `raw_parser` in `src/backend/parser/parser.c`.

## Related Concepts

- Raw parse tree
- Lexer/token stream
- Grammar productions
- `RawStmt`
- `RawParseMode`

These should be expanded only when a later source-backed question or subsystem pass needs the detail.

## Important Code Paths

- [[v18/code-paths/simple-select-query]] - Simple `SELECT` through simple Query protocol.
- [[v18/code-paths/insert-path]] - Simple `INSERT ... VALUES`.
- [[v18/code-paths/update-path]] - Simple `UPDATE`.
- [[v18/code-paths/delete-path]] - Simple `DELETE`.
- PL/pgSQL expression parsing modes: later investigation, because `RawParseMode` supports PL/pgSQL-specific modes in `src/include/parser/parser.h`.

## Differences Across Supported Versions

Only PostgreSQL 18 is currently supported.

## Source References

- `raw/postgres-18/src/backend/tcop/postgres.c:pg_parse_query`
- `raw/postgres-18/src/backend/parser/parser.c:raw_parser`
- `raw/postgres-18/src/backend/parser/parser.c:base_yylex`
- `raw/postgres-18/src/backend/parser/scan.l`
- `raw/postgres-18/src/backend/parser/gram.y`
- `raw/postgres-18/src/backend/parser/README`
- `raw/postgres-18/src/include/parser/parser.h`

## Open Questions

- Which raw parse node types are produced for a minimal `SELECT`?
- Where should the wiki draw the boundary between parser and analyzer pages for files like `parse_expr.c` and `parse_clause.c`?
- Should scanner and grammar internals get separate file pages before a deeper source trace?
