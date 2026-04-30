# Wiki Index

This is the global catalog for the PostgreSQL engine wiki.

## Entry Points

- [[versions]] - PostgreSQL version index and source pin manifest.
- [[overview]] - Cross-version architecture overview.
- [[log]] - Chronological activity log.
- [[operations/agent]] - Project-local Hermes install and start/stop runbook for the wiki maintainer agent.

## Shared Concepts

- [[shared/concepts/query-tree]] - Analyzed `Query` trees.
- [[shared/concepts/planned-statement]] - Planner output wrapper around plan trees.
- [[shared/concepts/plan-and-planstate]] - Planner `Plan` trees and executor `PlanState` trees.
- [[shared/concepts/path-and-reloptinfo]] - Planner relation and candidate path structures.
- [[shared/concepts/executor-state]] - Query-wide executor state.
- [[shared/concepts/tuple-table-slot]] - Executor row container.
- [[shared/concepts/modifytable]] - DML plan node family.
- [[shared/concepts/portal]] - Execution wrapper used by query processing and cursors.
- [[shared/concepts/querydesc]] - Executor descriptor for one planned statement execution.

## Version-Specific Pages

### PostgreSQL 18

- [[v18/index]] - Primary version landing page. Source checkout pinned to `REL_18_STABLE` commit `6cb307251c5c6261286c1566496920976640108e`.

#### Subsystems

- [[v18/subsystems/parser]] - PG 18 raw SQL parser.
- [[v18/subsystems/analyzer]] - PG 18 parse analyzer.
- [[v18/subsystems/rewriter]] - PG 18 query rewriter.
- [[v18/subsystems/planner]] - PG 18 planner/optimizer entry map.
- [[v18/subsystems/executor]] - PG 18 executor entry map.

#### Code Paths

- [[v18/code-paths/simple-select-query]] - PG 18 simple `SELECT` through simple Query protocol.
- [[v18/code-paths/insert-path]] - PG 18 simple `INSERT ... VALUES`.
- [[v18/code-paths/update-path]] - PG 18 simple `UPDATE`.
- [[v18/code-paths/delete-path]] - PG 18 simple `DELETE`.

## Maintenance Tooling

- `scripts/wiki_agent` - start, stop, status, and logs for the maintainer agent process.
- `scripts/recent_log` - recent wiki activity.
- `scripts/wiki_lint` - wiki health checks.
- `scripts/source_lookup` - project-local PostgreSQL source lookup.
- `scripts/version_diff` - source path comparison across project-local PostgreSQL checkouts.
- `scripts/llama_server` - start, stop, status, and logs for the local llama.cpp OpenAI-compatible server.

## Maintenance Notes

- Update this page whenever a wiki page is created or substantially changed.
- Keep version-specific entries tagged with their PostgreSQL major version.
- Prefer links to version landing pages, such as `vNN/index`, once versions exist.
