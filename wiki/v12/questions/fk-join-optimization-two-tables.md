---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Foreign-Key Join Optimization for Two-Table Joins (unverified)

## Question

In PostgreSQL 12, produce a comprehensive analysis on how foreign key joins are optimized by the query planner in cases of SQL that joins two tables.

## Short Answer

In PostgreSQL 12 the planner does **not** use foreign-key (FK) constraints to choose a different join algorithm or rewrite away inner joins. FK information directly affects one planner decision: join row-count estimation.

When the join's equality clauses match an FK, [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] replaces the per-clause independence estimate with `1 / referenced_table_tuples` for inner, left, and full joins. Related join-removal machinery can remove left joins or reduce semijoins when the inner side is provably unique, but that proof uses unique indexes or subquery distinctness, not FK metadata [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#join_is_removable|join_is_removable]] [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#reduce_unique_semijoins|reduce_unique_semijoins]].

There is no FK-driven join-order change, no FK-driven algorithm choice (nested-loop / hash / merge), and no inner-join elimination. The FK affects the plan only through the cardinality estimate that path generation consumes [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]] [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|get_relation_foreign_keys]].

## Detailed Answer

### Pipeline for a two-table join

For:

```sql
SELECT /* wiki_fk_join_demo */ *
FROM   orders  o
JOIN   customers c ON c.id = o.customer_id;
```

with `orders.customer_id REFERENCES customers(id)`, the planner runs these phases.

#### 1. Build `ForeignKeyOptInfo`s during catalog load

`get_relation_info` calls [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|get_relation_foreign_keys]], which walks `RelationGetFKeyList(relation)` and creates one `ForeignKeyOptInfo` per `(referencing rel, referenced RTE)` pair seen in the query's range table. The result is appended to `root->fkey_list`.

Short-circuits inside [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|get_relation_foreign_keys]]:

- Skip if `rel->reloptkind != RELOPT_BASEREL`.
- Skip if `list_length(rtable) < 2` (single-table queries cannot benefit).
- Skip inheritance parents.
- Skip self-referential FKs.

The data structure is [[raw/postgres-12/src/include/nodes/pathnodes.h#ForeignKeyOptInfo|ForeignKeyOptInfo]]: per-column arrays for `conkey`, `confkey`, `conpfeqop`, plus the match bookkeeping (`nmatched_ec`, `nmatched_rcols`, `nmatched_ri`, `eclass[]`, `rinfos[]`) that gets filled in later.

#### 2. Match FK columns to query equalities

After equivalence-class (EC) generation and after join removal, `query_planner` calls [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]] [[raw/postgres-12/src/backend/optimizer/plan/planmain.c#query_planner|query_planner]].

For each FK, for each FK column it tries:

- [[raw/postgres-12/src/backend/optimizer/path/equivclass.c#match_eclasses_to_foreign_key_col|match_eclasses_to_foreign_key_col]]: scan `root->eq_classes` for an EC containing both Vars whose `ec_opfamilies` matches the FK's `conpfeqop`. On a hit, set `eclass[colno]` and bump `nmatched_ec`.
- Otherwise, scan `con_rel->joininfo` for a "loose" binary `OpExpr` of the right shape (skipping `outerjoin_delayed` clauses) — used under outer joins where the equality cannot be promoted to an EC. Hits go into `rinfos[colno]` with `nmatched_rcols` / `nmatched_ri`.

Pruning rules:

- An FK is dropped if either side is not a `RELOPT_BASEREL` (covers inheritance otherrels and rels removed by join removal) [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]].
- After scanning, an FK is retained only if every FK column matched an EC or loose qual. This means a partially matched multicolumn FK is discarded in PostgreSQL 12 [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]].

#### 3. Apply FK selectivity in `calc_joinrel_size_estimate`

Every joinrel under consideration runs through [[raw/postgres-12/src/backend/optimizer/path/costsize.c#calc_joinrel_size_estimate|calc_joinrel_size_estimate]], which calls [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] before the normal `clauselist_selectivity`. The FK function peels matching clauses out of `restrictlist` and returns `fkselec` as a substitute estimate; remaining clauses still feed `clauselist_selectivity` to produce `jselec`.

Algorithm in [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]]:

1. Skip the FK unless its `con_relid` and `ref_relid` straddle `outer_relids` and `inner_relids`.
2. For semi/anti joins, skip the FK if the referenced table is on the LHS, or the inner is more than one base rel.
3. Walk `restrictlist`. A clause matches an FK column if either:
   - its `parent_ec` equals `fkinfo->eclass[i]`, or
   - it is `list_member_ptr(fkinfo->rinfos[i], rinfo)`.

   Matches move into `removedlist`.
4. Sanity guard: if `length(removedlist) != fkinfo->nmatched_ec + fkinfo->nmatched_ri`, restore the clauses and skip this FK to avoid double-counting, for example when two FKs share one EC [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]].
5. Selectivity:
   - `JOIN_INNER` / `JOIN_LEFT` / `JOIN_FULL`: `fkselec *= 1.0 / Max(ref_rel->tuples, 1.0)` [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]].
   - `JOIN_SEMI` / `JOIN_ANTI` (only when the referenced table is the inner singleton): `fkselec *= ref_rel->rows / Max(ref_rel->tuples, 1.0)` [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]].

The final inner-join cardinality in [[raw/postgres-12/src/backend/optimizer/path/costsize.c#calc_joinrel_size_estimate|calc_joinrel_size_estimate]] is:

$$
\text{nrows} = \text{outer\_rows} \cdot \text{inner\_rows} \cdot \text{fkselec} \cdot \text{jselec}
$$

clamped by `clamp_row_est`.

#### 4. Why this matters

For single-column FKs with current statistics, the FK estimate is usually close to what `eqjoinsel` would give from referenced-side MCVs / n-distinct. The dramatic improvement is for **multi-column FKs**, where `clauselist_selectivity` would multiply per-column selectivities under the independence assumption. The header comment of [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] calls this out explicitly.

Caveats encoded in the same function:

- **NULL referencing columns are not derated.** May slightly overshoot when many FK columns are NULL.
- **Inheritance / partitioning.** The FK is treated as covering all children of an inheritance parent — fine on the referencing side, knowingly imperfect on the referenced side.

### Where FKs do not influence the plan

- **Join order / algorithm.** `add_paths_to_joinrel`, `make_join_rel`, GEQO and the dynamic-programming join search never read `fkey_list`. A source search finds `fkey_list` used for planner initialization, FK collection, FK matching, debug output, and FK selectivity, but not for join path construction or algorithm selection [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]] [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|get_relation_foreign_keys]] [[raw/postgres-12/src/backend/optimizer/plan/planmain.c#query_planner|query_planner]].
- **Inner-join elimination.** PostgreSQL 12 has no "trusted FK ⇒ drop the parent table" optimization. The planner's FK-specific path estimates selectivity; the uniqueness-driven removal path is limited to left joins and semijoins [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#join_is_removable|join_is_removable]] [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#reduce_unique_semijoins|reduce_unique_semijoins]].
- **Outer-join removal.** [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#join_is_removable|join_is_removable]] succeeds on `LEFT JOIN customers ON c.id = o.customer_id` because `customers.id` is a unique key (PK), via `rel_supports_distinctness` / `rel_is_distinct_for`. The FK constraint is not consulted.
- **Semi-join reduction.** [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#reduce_unique_semijoins|reduce_unique_semijoins]] likewise uses `innerrel_is_unique`, not FKs.
- The only reference from join-removal back to FK code is the comment that [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]] will later prune dead FKs, not the other way around [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#remove_leftjoinrel_from_query|remove_leftjoinrel_from_query]].

### Optimizer pass ordering

From [[raw/postgres-12/src/backend/optimizer/plan/planmain.c#query_planner|query_planner]]:

1. `generate_base_implied_equalities` — finalize ECs.
2. `remove_useless_joins` — uniqueness-driven outer-join removal.
3. `reduce_unique_semijoins` — semi → inner where safe.
4. `match_foreign_keys_to_quals` — annotate and prune `root->fkey_list` (deferred until after join removal so dead rels' FKs are skipped).
5. Path generation in `make_one_rel`; every joinrel ultimately calls `calc_joinrel_size_estimate` → `get_foreign_key_join_selectivity`.

### Worked example (single-column FK, inner join)

Schema: `customers(id PK)` with N₁ rows; `orders(customer_id NOT NULL REFERENCES customers(id))` with N₂ rows.

- After [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|get_relation_foreign_keys]]: one entry, `con_relid = orders`, `ref_relid = customers`, `nkeys = 1`.
- After [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]]: `c.id = o.customer_id` is in an EC with the right opfamily, so `eclass[0]` is set and `nmatched_ec = 1`.
- In [[raw/postgres-12/src/backend/optimizer/path/costsize.c#calc_joinrel_size_estimate|calc_joinrel_size_estimate]] for `{orders, customers}`:
  - `get_foreign_key_join_selectivity` removes the clause and returns `fkselec = 1.0 / N₁`.
  - `jselec = 1.0`.
  - `JOIN_INNER`: `nrows = N₂ * N₁ * (1/N₁) * 1.0 = N₂` (then `clamp_row_est`).

The cardinality fingerprint of the FK is therefore `nrows ≈ N₂` regardless of column-stat quality.

Multi-column FKs traverse the same code; multiple per-column matches are required and `fkselec` stays at `1/N₁` rather than the product of per-column selectivities — that is the substantive win over `clauselist_selectivity`.

## Context Reviewed

- [[raw/postgres-12/src/include/nodes/pathnodes.h#ForeignKeyOptInfo|ForeignKeyOptInfo]]
- [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|get_relation_foreign_keys]]
- [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]]
- [[raw/postgres-12/src/backend/optimizer/path/equivclass.c#match_eclasses_to_foreign_key_col|match_eclasses_to_foreign_key_col]]
- [[raw/postgres-12/src/backend/optimizer/path/costsize.c#calc_joinrel_size_estimate|calc_joinrel_size_estimate]]
- [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]]
- [[raw/postgres-12/src/backend/optimizer/plan/planmain.c#query_planner|query_planner]]
- [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#join_is_removable|join_is_removable]] and [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#reduce_unique_semijoins|reduce_unique_semijoins]]

## Evidence Map

| Claim | Source |
|---|---|
| FK info attached during base-rel info collection | [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|get_relation_foreign_keys]] |
| Skip when single-RTE / non-baserel / inheritance parent | [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|get_relation_foreign_keys]] |
| One `ForeignKeyOptInfo` per matching RTE pair, self-FKs skipped | [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|get_relation_foreign_keys]] |
| FK-to-clause matching uses EC then loose `joininfo` scan | [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]] |
| EC matching requires opfamily match | [[raw/postgres-12/src/backend/optimizer/path/equivclass.c#match_eclasses_to_foreign_key_col|match_eclasses_to_foreign_key_col]] |
| Multicolumn FKs must match every column to be retained | [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|match_foreign_keys_to_quals]] |
| `get_foreign_key_join_selectivity` removes matched clauses, returns substitute | [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] |
| Inner / left / full FK selectivity = `1 / ref_tuples` | [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] |
| Semi / anti FK selectivity = `ref_rel->rows / ref_tuples` | [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] |
| Sanity guard against double-counting when FKs share EC | [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|get_foreign_key_join_selectivity]] |
| FK matching ordered after join removal | [[raw/postgres-12/src/backend/optimizer/plan/planmain.c#query_planner|query_planner]] |
| Outer-join removal uses uniqueness, not FK | [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#join_is_removable|join_is_removable]] |
| Semi → inner reduction uses uniqueness, not FK | [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#reduce_unique_semijoins|reduce_unique_semijoins]] |

## Source References

- [[raw/postgres-12/src/include/nodes/pathnodes.h#ForeignKeyOptInfo|pathnodes.h#ForeignKeyOptInfo]] - FK planner metadata stored on `PlannerInfo`.
- [[raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys|plancat.c#get_relation_foreign_keys]] - catalog loading and FK short-circuit rules.
- [[raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals|initsplan.c#match_foreign_keys_to_quals]] - FK-to-join-clause matching and pruning.
- [[raw/postgres-12/src/backend/optimizer/path/equivclass.c#match_eclasses_to_foreign_key_col|equivclass.c#match_eclasses_to_foreign_key_col]] - equivalence-class matching for FK columns.
- [[raw/postgres-12/src/backend/optimizer/path/costsize.c#calc_joinrel_size_estimate|costsize.c#calc_joinrel_size_estimate]] - join cardinality calculation site.
- [[raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity|costsize.c#get_foreign_key_join_selectivity]] - FK selectivity replacement logic.
- [[raw/postgres-12/src/backend/optimizer/plan/planmain.c#query_planner|planmain.c#query_planner]] - planner pass ordering.
- [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#join_is_removable|analyzejoins.c#join_is_removable]] - uniqueness-based left-join removal.
- [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#reduce_unique_semijoins|analyzejoins.c#reduce_unique_semijoins]] - uniqueness-based semijoin reduction.
- [[raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#remove_leftjoinrel_from_query|analyzejoins.c#remove_leftjoinrel_from_query]] - join-removal cleanup that leaves FK pruning to the later FK matching pass.

## Open Questions

- Whether any later v12 minor releases added FK-driven uniqueness shortcuts to `join_is_removable` / `innerrel_is_unique`. This page is pinned to commit `45b88269a353ad93744772791feb6d01bc7e1e42` (12.2) and was not checked against the full `REL_12_STABLE` history.
- NULL-fraction derating in multi-column FKs is intentionally omitted; the magnitude of the resulting overestimate has not been quantified here.

## Related Pages

- [[v12/index]]
- [[versions]]
