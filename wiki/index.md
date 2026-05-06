# Wiki Index

This is the global catalog for the PostgreSQL engine wiki.

## Entry Points

- [[versions]] - PostgreSQL version index and source pin manifest.
- [[overview]] - Cross-version architecture overview.
- [[log]] - Chronological activity log.
- [[operations/agent]] - Project-local Hermes install and start/stop runbook for the wiki maintainer agent.

## Version-Specific Pages

### PostgreSQL 18

- [[v18/index]] - Primary version landing page. Source checkout pinned to `REL_18_STABLE` commit `6cb307251c5c6261286c1566496920976640108e`; project-context pack generated under `.wiki-runtime/context/postgres-18/`.



### PostgreSQL 12.2

- [[v12/index]] - Legacy version landing page. Source checkout pinned to `REL_12_STABLE` commit `45b88269a353ad93744772791feb6d01bc7e1e42`; project-context pack generated under `.wiki-runtime/context/postgres-12/`.
- [[v12/questions/bgwriter-tuning-recommendations|Bgwriter tuning recommendations (unverified)]] - Source-grounded direction-of-change matrix for the four PG 12 bgwriter GUCs (`bgwriter_delay`, `bgwriter_lru_maxpages`, `bgwriter_lru_multiplier`) across the main tuning scenarios, with verified `pg_stat_bgwriter` counter wiring for iterative numeric tuning.
- [[v12/questions/enable-io-timing-measurements-production|Enable I/O timing measurements on production]] - Production procedure for enabling PG 12 `track_io_timing`, including host timing preflight, reload/session semantics, tagged SQL sampling, `pg_stat_database`, optional `pg_stat_statements`, and `EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)` interpretation.



## Maintenance Tooling

- `scripts/recent_log` - recent wiki activity.
- `scripts/wiki_lint` - wiki health checks.
- `scripts/source_lookup` - project-local PostgreSQL source lookup; requires `--version NN`.
- `scripts/source_deps` - context-pack include/dependency lookup for direct includes, reverse include users, transitive include edges, and compile-unit flags; requires `--version NN`.
- `scripts/test_source_tools` - end-to-end synthetic fixture tests for `scripts/source_lookup` and `scripts/source_deps`.
- `scripts/source_context` - regenerate per-version project-context packs under `.wiki-runtime/context/postgres-NN/`; requires `--version NN` or explicit `--all`.
- `scripts/version_diff` - source path comparison across project-local PostgreSQL checkouts.
- `scripts/llama_server` - start, stop, status, and logs for the local llama.cpp OpenAI-compatible server.
- `scripts/hermes_sessions` - list and clear project-local Hermes session files and database rows.

## Maintenance Notes

- Update this page whenever a wiki page is created or substantially changed.
- Keep version-specific entries tagged with their PostgreSQL major version.
- Prefer links to version landing pages, such as `vNN/index`, once versions exist.
