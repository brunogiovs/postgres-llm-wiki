# PostgreSQL 18

## Source Pin

- Branch: `REL_18_STABLE`
- Commit: `6cb307251c5c6261286c1566496920976640108e`
- Status: `primary`
- Source path: `raw/postgres-18/`
- Added: 2026-04-30

## Coverage

Query lifecycle subsystem spine is initialized. Source-backed pages exist for parser, analyzer, rewriter, planner, executor, and filed PostgreSQL 18 questions. A generated project-context pack exists under `.wiki-runtime/context/postgres-18/`.

## Project Context

- Manifest: `.wiki-runtime/context/postgres-18/manifest.md`
- Generated artifacts: `.wiki-runtime/context/postgres-18/tree-L4.txt`, `.wiki-runtime/context/postgres-18/build-config/`, and `.wiki-runtime/context/postgres-18/external-deps.txt`
- Deferred artifacts: `.wiki-runtime/context/postgres-18/compile_commands.json`, `.wiki-runtime/context/postgres-18/include-deps.txt`, and `.wiki-runtime/context/postgres-18/callgraphs/`

## Subsystems

- [[v18/subsystems/parser]] - Raw SQL parsing into raw parse trees.
- [[v18/subsystems/analyzer]] - Raw parse tree transformation into `Query` trees.
- [[v18/subsystems/rewriter]] - Query rewrite system for analyzed `Query` trees.
- [[v18/subsystems/planner]] - Planning rewritten `Query` trees into `PlannedStmt` / `Plan` trees.
- [[v18/subsystems/executor]] - Running planned query trees through executor state and plan nodes.

## Files

No source file map pages have been created yet.

## Questions

- [[v18/questions/query-plan-interpretation-inputs]] - Inputs needed to interpret a plan, planner choices, and production impact.
- [[v18/questions/prepared-statement-replanning]] - Automatic revalidation/replanning of prepared statements after DDL, index, and statistics changes.
- [[v18/questions/btree-leaf-density-estimate]] - Catalog-only SQL approximating `pgstatindex.avg_leaf_density` with no index I/O; partial- and dedup-aware.
- [[v18/questions/avg-leaf-density-vacuum-stat-table]] - Modify VACUUM/autovacuum to compute and persist `avg_leaf_density` per btree index in a new pgstat kind, riding the existing leaf-page scan.
- [[v18/questions/plan-cache-mode-production-impact]] - Production impact of `plan_cache_mode` (`auto`, `force_generic_plan`, `force_custom_plan`), pros/cons per mode, and which to pick per scenario.
- [[v18/questions/insert-row-disk-writes]] - PG 18 disk writes during row insert txn (WAL sync at commit only, data async).
- [[v18/questions/query-disk-io-with-warm-cache]] - PG 18 pre-execution and execution disk I/O paths and how slow random I/O hurts even with warm shared buffers and OS page cache.

## Open Questions

- Project-context compiler database generation is deferred on this host because `meson` and `bear` are missing.
- Project-context include dependencies are deferred until a compiler database or configured PostgreSQL build headers are available.
- Project-context call/reference graphs are deferred on this host because `cflow`, `doxygen`, and `dot` are missing.
