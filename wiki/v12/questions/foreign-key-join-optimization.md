---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: claude-opus-4-7 2026-05-09T00:00:00Z
---

# How are foreign key joins optimized by the query planner in PostgreSQL 12?

PostgreSQL 12's query planner uses foreign key constraint information to improve join selectivity estimation when join conditions match foreign key relationships. This provides more accurate cost estimates than relying solely on column statistics, especially for multi-column foreign keys where the independence assumption fails.

## Context Reviewed

The question examines how foreign key constraints influence query planner optimization for join operations, specifically selectivity estimation and cost calculation.

## Evidence Map

Foreign key information is collected during planning via `get_relation_foreign_keys()` in `plancat.c`, which creates `ForeignKeyOptInfo` structures for FKs referencing some other RTE in the query [[raw/postgres-12/src/backend/optimizer/util/plancat.c#L476|plancat.c#get_relation_foreign_keys]].

Join conditions are matched to FK constraints through `match_foreign_keys_to_quals()` in `initsplan.c`. Each FK column is first matched against equivalence classes via `match_eclasses_to_foreign_key_col()`; columns that fail EC matching fall back to scanning `con_rel->joininfo` for "loose" quals — binary `OpExpr` clauses that aren't `outerjoin_delayed` [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#L2413|initsplan.c#match_foreign_keys_to_quals]].

When FK-matched clauses are found, `get_foreign_key_join_selectivity()` in `costsize.c` estimates selectivity using FK semantics rather than statistics. For `JOIN_INNER`, `JOIN_LEFT`, and `JOIN_FULL`, selectivity is `1.0 / Max(ref_rel->tuples, 1.0)` (since each referencing row matches exactly one referenced row), avoiding independence assumptions that fail for multi-column FKs [[raw/postgres-12/src/backend/optimizer/path/costsize.c#L4709|costsize.c#get_foreign_key_join_selectivity]] [[raw/postgres-12/src/backend/optimizer/path/costsize.c#L4890|costsize.c#L4890-L4901]].

For `JOIN_SEMI` and `JOIN_ANTI`, the FK only helps when the referenced table is on the inside of the join; selectivity becomes `ref_rel->rows / ref_tuples`, accounting for restriction clauses on the referenced relation that reduce the number of matches the FK otherwise guarantees [[raw/postgres-12/src/backend/optimizer/path/costsize.c#L4872|costsize.c#L4872-L4889]]. When the referenced rel is on the outside, or the inner side is not a single baserel, the FK is ignored.

FK-matched clauses are removed from the restrictlist via `list_delete_cell()` so their per-clause selectivity is not multiplied on top of the FK selectivity [[raw/postgres-12/src/backend/optimizer/path/costsize.c#L4759|costsize.c#L4759-L4821]]. If the planner cannot remove every clause it expected to (e.g. another FK already consumed the same EC-derived clause), it puts them back and skips this FK to avoid double-counting [[raw/postgres-12/src/backend/optimizer/path/costsize.c#L4842|costsize.c#L4842-L4847]].

This optimization is called once per join from `calc_joinrel_size_estimate()`; the resulting `fkselec` multiplies into the row estimate for every join type [[raw/postgres-12/src/backend/optimizer/path/costsize.c#L4589|costsize.c#calc_joinrel_size_estimate]].

## Inheritance Interaction

`get_relation_foreign_keys()` returns immediately for inheritance parents, so no `ForeignKeyOptInfo` is built when the referencing rel is the parent of an inheritance tree [[raw/postgres-12/src/backend/optimizer/util/plancat.c#L498|plancat.c#L498-L499]]. `match_foreign_keys_to_quals()` further requires both `con_rel` and `ref_rel` to be `RELOPT_BASEREL`, which excludes inheritance child otherrels [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#L2445|initsplan.c#L2445-L2447]].

For FKs whose endpoints are themselves inheritance parents at estimation time, `get_foreign_key_join_selectivity()` documents that it estimates as though the FK covers all children. The header comment notes this is reasonable for the referencing side (users typically apply identical constraints across children) but not strictly correct for the referenced side; the planner accepts the imprecision because referencing an inheritance parent is uncommon in practice [[raw/postgres-12/src/backend/optimizer/path/costsize.c#L4862|costsize.c#L4862-L4870]].

## Open Questions

- Are there cases where FK selectivity estimation could be less accurate than statistical methods (e.g. heavily filtered referenced tables where `1/tuples` over-counts matches)?

## Source References

- Source pin: [[raw/postgres-12/]] at commit `45b88269a353ad93744772791feb6d01bc7e1e42`
- FK collection during planning: [[raw/postgres-12/src/backend/optimizer/util/plancat.c|plancat.c]] (`get_relation_foreign_keys`, `ForeignKeyOptInfo` build, inheritance-parent skip)
- Join-clause matching: [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c|initsplan.c]] (`match_foreign_keys_to_quals`, EC vs loose-qual paths, baserel guard)
- EC matching helper: [[raw/postgres-12/src/backend/optimizer/path/equivclass.c|equivclass.c]] (`match_eclasses_to_foreign_key_col`)
- FK selectivity estimation and call site: [[raw/postgres-12/src/backend/optimizer/path/costsize.c|costsize.c]] (`get_foreign_key_join_selectivity`, `calc_joinrel_size_estimate`, restrictlist removal, JOIN_SEMI/JOIN_ANTI branch, inheritance XXX comment)
- `ForeignKeyOptInfo` struct: [[raw/postgres-12/src/include/nodes/pathnodes.h|pathnodes.h]]
- Relcache FK list: [[raw/postgres-12/src/backend/utils/cache/relcache.c|relcache.c]] (`RelationGetFKeyList`)
- Source searches used: `scripts/source_graph_query --version 12 symbol ...` and `scripts/source_graph_query --version 12 file ...` against the pinned checkout
