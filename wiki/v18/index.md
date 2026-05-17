# PostgreSQL 18

## Source Pin

- Branch: `REL_18_STABLE`
- Commit: `6cb307251c5c6261286c1566496920976640108e`
- Status: `primary`
- Source path: `raw/postgres-18/`
- Added: 2026-04-30

## Coverage

Behavioral claims cite the matching pinned checkout under `raw/postgres-18/`.

## Questions

- [[v18/questions/avg-leaf-density-during-vacuum|Computing and Storing avg_leaf_density During (Auto)VACUUM of a B-Tree Index (unverified)]] - Design for computing `pgstatindex`-style `avg_leaf_density` inside the existing B-tree VACUUM leaf scan and storing it with minimal extra I/O.
