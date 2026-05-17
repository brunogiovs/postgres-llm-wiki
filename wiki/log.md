# Wiki Log

Append one entry after every scaffold change, version lifecycle event, ingest, trace, lint pass, or filed answer.

## [2026-05-17] lint-fix v12 | add source references

- Added the missing `## Source References` section to [[v12/questions/fk-join-optimization-two-tables|Foreign-Key Join Optimization for Two-Table Joins (unverified)]] so `scripts/wiki_lint` can validate the page.

## [2026-05-17] answer v18 | compute and store avg_leaf_density during (auto)vacuum

- Filed [[v18/questions/avg-leaf-density-during-vacuum|Computing and Storing avg_leaf_density During (Auto)VACUUM of a B-Tree Index (unverified)]].
- Designed accumulation in the `btvacuumpage` `P_ISLEAF` branch via new `BTVacState` sums, derived in `btvacuumscan`, mirroring `pgstatindex_impl` semantics with zero extra page I/O.
- Proposed dual storage: B-tree metapage (piggybacks the existing `_bt_set_cleanup_info` WAL-logged write) and the cumulative statistics system (`PgStat_StatTabEntry` via a `pgstat_report_vacuum`-style reporter), plus skip-scan coverage caveats.
- Cited only `raw/postgres-18/` (commit `6cb307251c5c6261286c1566496920976640108e`); filed `verified_by_agent: not yet`, title carries `(unverified)`.
- Linked from `wiki/v18/index.md` and `wiki/index.md`.

## [2026-05-13] review-fix v12 | foreign-key join optimization question

- Clarified that FK metadata directly affects join row-count estimation, while outer-join removal and semijoin reduction are uniqueness-driven.
- Corrected multicolumn FK matching to state that PostgreSQL 12 retains only fully matched FKs.
- Replaced source citations in [[v12/questions/fk-join-optimization-two-tables|Foreign-Key Join Optimization for Two-Table Joins (unverified)]] with the required `[[raw/postgres-12/...#symbol]]` form.
- Removed the resolved `eqjoinsel` open question after checking the `calc_joinrel_size_estimate` path.

## [2026-05-13] answer v12 | foreign-key join optimization for two-table joins

- Filed [[v12/questions/fk-join-optimization-two-tables|Foreign-Key Join Optimization for Two-Table Joins (unverified)]] covering `get_relation_foreign_keys`, `match_foreign_keys_to_quals`, `match_eclasses_to_foreign_key_col`, `calc_joinrel_size_estimate`, and `get_foreign_key_join_selectivity`.
- Cited only `raw/postgres-12/` (commit `45b88269a353ad93744772791feb6d01bc7e1e42`).
- Filed as `verified_by_agent: not yet`; title carries `(unverified)` per `AGENTS.md`.
- Linked from `wiki/v12/index.md` and `wiki/index.md`.

## [2026-05-13] version-add v17 | added PostgreSQL 17 as active version

- Cloned `REL_17_STABLE` into `raw/postgres-17/` pinned to commit `54eeefaedbee0385529f3edf321bb99e49232aaa` (PostgreSQL 17.10, 3 commits past tag `REL_17_10`).
- Created `wiki/v17/index.md` landing page with status `active`.
- Registered the version in `wiki/versions.md` and `wiki/index.md`.

## [2026-05-13] cleanup | reset wiki content logs

- Removed the remaining filed answer page.
- Removed stale index and coverage references for removed content.
- Cleared older activity entries from this log.

## [2026-05-13] cleanup | removed generated navigation references

- Simplified version coverage and landing pages to point only at pinned raw checkouts.
- Removed generated navigation artifact wording from wiki overview and indexes.
