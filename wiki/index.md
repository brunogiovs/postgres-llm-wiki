# Wiki Index

This is the global catalog for the PostgreSQL engine wiki.

## Entry Points

- [[versions]] - PostgreSQL version index and source pin manifest.
- [[overview]] - Cross-version architecture overview.
- [[log]] - Chronological activity log.


## Version-Specific Pages

### PostgreSQL 18

- [[v18/index]] - Primary version landing page. Source checkout pinned to `REL_18_STABLE` commit `6cb307251c5c6261286c1566496920976640108e`; Graphify graph artifacts live under `.wiki-runtime/graph/postgres-18/`.



### PostgreSQL 12.2

- [[v12/index]] - Legacy version landing page. Source checkout pinned to `REL_12_STABLE` commit `45b88269a353ad93744772791feb6d01bc7e1e42`; Graphify graph artifacts live under `.wiki-runtime/graph/postgres-12/`.
- [[v12/questions/avg_leaf_density_minimal_io_query|Estimate avg_leaf_density with minimal I/O (unverified)]] - PostgreSQL 12 btree leaf-density estimate review, with `pgstatindex()`, C sampling, and `pageinspect` boundaries.



## Maintenance Tooling

- `scripts/recent_log` - recent wiki activity.
- `scripts/wiki_lint` - wiki health checks.
- `scripts/version_diff` - source path comparison across project-local PostgreSQL checkouts.
- `scripts/llama_server` - start, stop, status, and logs for the local llama.cpp OpenAI-compatible server.
- `scripts/hermes_sessions` - list and clear project-local Hermes session files and database rows.

## Maintenance Notes

- Update this page whenever a wiki page is created or substantially changed.
- Keep version-specific entries tagged with their PostgreSQL major version.
- Prefer links to version landing pages, such as `vNN/index`, once versions exist.
