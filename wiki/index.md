# Wiki Index

This is the global catalog for the PostgreSQL engine wiki.

## Entry Points

- [[versions]] - PostgreSQL version index and source pin manifest.
- [[overview]] - Cross-version architecture overview.
- [[log]] - Chronological activity log.


## Version-Specific Pages

### PostgreSQL 18

- [[v18/index]] - Primary version landing page. Source checkout pinned to `REL_18_STABLE` commit `6cb307251c5c6261286c1566496920976640108e`.
- [[v18/questions/avg-leaf-density-during-vacuum|Computing and Storing avg_leaf_density During (Auto)VACUUM of a B-Tree Index (unverified)]] - How to compute `pgstatindex`-style `avg_leaf_density` during B-tree VACUUM with minimal extra I/O and where to store it.



### PostgreSQL 17.10

- [[v17/index]] - Active version landing page. Source checkout pinned to `REL_17_STABLE` commit `54eeefaedbee0385529f3edf321bb99e49232aaa`.



### PostgreSQL 12.2

- [[v12/index]] - Legacy version landing page. Source checkout pinned to `REL_12_STABLE` commit `45b88269a353ad93744772791feb6d01bc7e1e42`.
- [[v12/questions/fk-join-optimization-two-tables|Foreign-Key Join Optimization for Two-Table Joins (unverified)]] - How the v12 planner uses foreign-key constraints when joining two tables.



## Maintenance Tooling

- `scripts/recent_log` - recent wiki activity.
- `scripts/wiki_lint` - wiki health checks.

## Maintenance Notes

- Update this page whenever a wiki page is created or substantially changed.
- Keep version-specific entries tagged with their PostgreSQL major version.
- Prefer links to version landing pages, such as `vNN/index`, once versions exist.
