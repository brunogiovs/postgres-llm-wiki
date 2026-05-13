# Wiki Log

Append one entry after every scaffold change, version lifecycle event, ingest, trace, lint pass, or filed answer.

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
