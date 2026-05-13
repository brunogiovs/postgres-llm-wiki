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

In PostgreSQL 12 the planner does **not** use foreign-key (FK) constraints to choose a different join algorithm or rewrite away inner joins. FK information is consumed in three narrow places, only one of which is FK-specific:

1. **Join row-count estimation.** When the join's equality clauses match an FK, [`get_foreign_key_join_selectivity`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4694) replaces the per-clause independence estimate with `1 / referenced_table_tuples`. This is the FK-specific path.
2. **Outer-join removal** by [`join_is_removable`](raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#L149), driven by uniqueness of the inner side (unique indexes/keys), not by the FK itself.
3. **Semi-join → inner-join reduction** by [`reduce_unique_semijoins`](raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#L498), again uniqueness-driven, not FK-driven.

There is no FK-driven join-order change, no FK-driven algorithm choice (nested-loop / hash / merge), and no inner-join elimination. The FK affects the plan only through the cardinality estimate that path generation consumes.

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

`get_relation_info` calls [`get_relation_foreign_keys`](raw/postgres-12/src/backend/optimizer/util/plancat.c#L466), which walks `RelationGetFKeyList(relation)` and creates one `ForeignKeyOptInfo` per `(referencing rel, referenced RTE)` pair seen in the query's range table. The result is appended to `root->fkey_list`.

Short-circuits inside [`get_relation_foreign_keys`](raw/postgres-12/src/backend/optimizer/util/plancat.c#L476):

- Skip if `rel->reloptkind != RELOPT_BASEREL`.
- Skip if `list_length(rtable) < 2` (single-table queries cannot benefit).
- Skip inheritance parents.
- Skip self-referential FKs.

The data structure is [`ForeignKeyOptInfo`](raw/postgres-12/src/include/nodes/pathnodes.h#L838): per-column arrays for `conkey`, `confkey`, `conpfeqop`, plus the match bookkeeping (`nmatched_ec`, `nmatched_rcols`, `nmatched_ri`, `eclass[]`, `rinfos[]`) that gets filled in later.

#### 2. Match FK columns to query equalities

After equivalence-class (EC) generation and after join removal, [`query_planner` calls `match_foreign_keys_to_quals`](raw/postgres-12/src/backend/optimizer/plan/planmain.c#L250). The function lives in [`initsplan.c#match_foreign_keys_to_quals`](raw/postgres-12/src/backend/optimizer/plan/initsplan.c#L2399).

For each FK, for each FK column it tries:

- [`match_eclasses_to_foreign_key_col`](raw/postgres-12/src/backend/optimizer/path/equivclass.c#L2018): scan `root->eq_classes` for an EC containing both Vars whose `ec_opfamilies` matches the FK's `conpfeqop`. On a hit, set `eclass[colno]` and bump `nmatched_ec`.
- Otherwise, scan `con_rel->joininfo` for a "loose" binary `OpExpr` of the right shape (skipping `outerjoin_delayed` clauses) — used under outer joins where the equality cannot be promoted to an EC. Hits go into `rinfos[colno]` with `nmatched_rcols` / `nmatched_ri`.

Pruning rules:

- An FK is dropped if either side is not a `RELOPT_BASEREL` (covers inheritance otherrels and rels removed by join removal). See [`initsplan.c`](raw/postgres-12/src/backend/optimizer/plan/initsplan.c#L2436-L2451).
- After scanning, FKs with no matched columns are discarded.

#### 3. Apply FK selectivity in `calc_joinrel_size_estimate`

Every joinrel under consideration runs through [`calc_joinrel_size_estimate`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4554), which calls [`get_foreign_key_join_selectivity`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4589) before the normal `clauselist_selectivity`. The FK function peels matching clauses out of `restrictlist` and returns `fkselec` as a substitute estimate; remaining clauses still feed `clauselist_selectivity` to produce `jselec`.

Algorithm in [`get_foreign_key_join_selectivity`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4709):

1. Skip the FK unless its `con_relid` and `ref_relid` straddle `outer_relids` and `inner_relids`.
2. For semi/anti joins, skip the FK if the referenced table is on the LHS, or the inner is more than one base rel.
3. Walk `restrictlist`. A clause matches an FK column if either:
   - its `parent_ec` equals `fkinfo->eclass[i]`, or
   - it is `list_member_ptr(fkinfo->rinfos[i], rinfo)`.

   Matches move into `removedlist`.
4. Sanity guard: if `length(removedlist) != fkinfo->nmatched_ec + fkinfo->nmatched_ri`, restore the clauses and skip this FK to avoid double-counting (e.g., two FKs sharing one EC). See [`costsize.c`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4824-L4843).
5. Selectivity:
   - `JOIN_INNER` / `JOIN_LEFT` / `JOIN_FULL`: `fkselec *= 1.0 / Max(ref_rel->tuples, 1.0)`. See [`costsize.c`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4878-L4889).
   - `JOIN_SEMI` / `JOIN_ANTI` (only when the referenced table is the inner singleton): `fkselec *= ref_rel->rows / Max(ref_rel->tuples, 1.0)`. See [`costsize.c`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4861-L4877).

The final inner-join cardinality in [`calc_joinrel_size_estimate`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4660-L4690) is:

$$
\text{nrows} = \text{outer\_rows} \cdot \text{inner\_rows} \cdot \text{fkselec} \cdot \text{jselec}
$$

clamped by `clamp_row_est`.

#### 4. Why this matters

For single-column FKs with current statistics, the FK estimate is usually close to what `eqjoinsel` would give from referenced-side MCVs / n-distinct. The dramatic improvement is for **multi-column FKs**, where `clauselist_selectivity` would multiply per-column selectivities under the independence assumption. The header comment of [`get_foreign_key_join_selectivity`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4694-L4708) calls this out explicitly.

Caveats encoded in the same function:

- **NULL referencing columns are not derated.** May slightly overshoot when many FK columns are NULL.
- **Inheritance / partitioning.** The FK is treated as covering all children of an inheritance parent — fine on the referencing side, knowingly imperfect on the referenced side.

### Where FKs do not influence the plan

- **Join order / algorithm.** `add_paths_to_joinrel`, `make_join_rel`, GEQO and the dynamic-programming join search never read `fkey_list`. They see only the row-count estimate.
- **Inner-join elimination.** PostgreSQL 12 has no "trusted FK ⇒ drop the parent table" optimization. The join is executed even when the parent's columns are not referenced.
- **Outer-join removal.** [`join_is_removable`](raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#L149) succeeds on `LEFT JOIN customers ON c.id = o.customer_id` because `customers.id` is a unique key (PK), via `rel_supports_distinctness` / `rel_is_distinct_for`. The FK constraint is not consulted.
- **Semi-join reduction.** [`reduce_unique_semijoins`](raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#L498) likewise uses `innerrel_is_unique`, not FKs.
- The only call from join-removal back to FK code is the comment that [`match_foreign_keys_to_quals` will later prune dead FKs](raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#L443), not the other way around.

### Optimizer pass ordering

From [`query_planner` in planmain.c](raw/postgres-12/src/backend/optimizer/plan/planmain.c#L200-L260):

1. `generate_base_implied_equalities` — finalize ECs.
2. `remove_useless_joins` — uniqueness-driven outer-join removal.
3. `reduce_unique_semijoins` — semi → inner where safe.
4. `match_foreign_keys_to_quals` — annotate and prune `root->fkey_list` (deferred until after join removal so dead rels' FKs are skipped).
5. Path generation in `make_one_rel`; every joinrel ultimately calls `calc_joinrel_size_estimate` → `get_foreign_key_join_selectivity`.

### Worked example (single-column FK, inner join)

Schema: `customers(id PK)` with N₁ rows; `orders(customer_id NOT NULL REFERENCES customers(id))` with N₂ rows.

- After [`get_relation_foreign_keys`](raw/postgres-12/src/backend/optimizer/util/plancat.c#L466): one entry, `con_relid = orders`, `ref_relid = customers`, `nkeys = 1`.
- After [`match_foreign_keys_to_quals`](raw/postgres-12/src/backend/optimizer/plan/initsplan.c#L2399): `c.id = o.customer_id` is in an EC with the right opfamily, so `eclass[0]` is set and `nmatched_ec = 1`.
- In [`calc_joinrel_size_estimate`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4554) for `{orders, customers}`:
  - `get_foreign_key_join_selectivity` removes the clause and returns `fkselec = 1.0 / N₁`.
  - `jselec = 1.0`.
  - `JOIN_INNER`: `nrows = N₂ * N₁ * (1/N₁) * 1.0 = N₂` (then `clamp_row_est`).

The cardinality fingerprint of the FK is therefore `nrows ≈ N₂` regardless of column-stat quality.

Multi-column FKs traverse the same code; multiple per-column matches are required and `fkselec` stays at `1/N₁` rather than the product of per-column selectivities — that is the substantive win over `clauselist_selectivity`.

## Context Reviewed

- [`raw/postgres-12/src/include/nodes/pathnodes.h#ForeignKeyOptInfo`](raw/postgres-12/src/include/nodes/pathnodes.h#L838-L865)
- [`raw/postgres-12/src/backend/optimizer/util/plancat.c#get_relation_foreign_keys`](raw/postgres-12/src/backend/optimizer/util/plancat.c#L466-L562)
- [`raw/postgres-12/src/backend/optimizer/plan/initsplan.c#match_foreign_keys_to_quals`](raw/postgres-12/src/backend/optimizer/plan/initsplan.c#L2399-L2500)
- [`raw/postgres-12/src/backend/optimizer/path/equivclass.c#match_eclasses_to_foreign_key_col`](raw/postgres-12/src/backend/optimizer/path/equivclass.c#L2018-L2105)
- [`raw/postgres-12/src/backend/optimizer/path/costsize.c#calc_joinrel_size_estimate`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4554-L4690)
- [`raw/postgres-12/src/backend/optimizer/path/costsize.c#get_foreign_key_join_selectivity`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4694-L4905)
- [`raw/postgres-12/src/backend/optimizer/plan/planmain.c`](raw/postgres-12/src/backend/optimizer/plan/planmain.c#L200-L260)
- [`raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#join_is_removable`](raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#L149-L290) and [`reduce_unique_semijoins`](raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#L498-L600)

## Evidence Map

| Claim | Source |
|---|---|
| FK info attached during base-rel info collection | [`plancat.c#L445`](raw/postgres-12/src/backend/optimizer/util/plancat.c#L445) |
| Skip when single-RTE / non-baserel / inheritance parent | [`plancat.c#L489-L500`](raw/postgres-12/src/backend/optimizer/util/plancat.c#L489-L500) |
| One `ForeignKeyOptInfo` per matching RTE pair, self-FKs skipped | [`plancat.c#L530-L562`](raw/postgres-12/src/backend/optimizer/util/plancat.c#L530-L562) |
| FK-to-clause matching uses EC then loose `joininfo` scan | [`initsplan.c#L2459-L2500`](raw/postgres-12/src/backend/optimizer/plan/initsplan.c#L2459-L2500) |
| EC matching requires opfamily match | [`equivclass.c#L2086-L2099`](raw/postgres-12/src/backend/optimizer/path/equivclass.c#L2086-L2099) |
| `get_foreign_key_join_selectivity` removes matched clauses, returns substitute | [`costsize.c#L4694-L4905`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4694-L4905) |
| Inner / left / full FK selectivity = `1 / ref_tuples` | [`costsize.c#L4878-L4889`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4878-L4889) |
| Semi / anti FK selectivity = `ref_rel->rows / ref_tuples` | [`costsize.c#L4861-L4877`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4861-L4877) |
| Sanity guard against double-counting when FKs share EC | [`costsize.c#L4824-L4843`](raw/postgres-12/src/backend/optimizer/path/costsize.c#L4824-L4843) |
| FK matching ordered after join removal | [`planmain.c#L229-L250`](raw/postgres-12/src/backend/optimizer/plan/planmain.c#L229-L250) |
| Outer-join removal uses uniqueness, not FK | [`analyzejoins.c#L149-L290`](raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#L149-L290) |
| Semi → inner reduction uses uniqueness, not FK | [`analyzejoins.c#L498-L600`](raw/postgres-12/src/backend/optimizer/plan/analyzejoins.c#L498-L600) |

## Open Questions

- Whether `eqjoinsel` is ever consulted for an FK-matched clause: the matched clauses are removed from `restrictlist` before `clauselist_selectivity` runs, so the FK estimate appears to fully replace them, but a complete trace of `clauselist_selectivity` callers from `calc_joinrel_size_estimate` has not been done.
- Whether any later v12 minor releases added FK-driven uniqueness shortcuts to `join_is_removable` / `innerrel_is_unique`. This page is pinned to commit `45b88269a353ad93744772791feb6d01bc7e1e42` (12.2) and was not checked against the full `REL_12_STABLE` history.
- NULL-fraction derating in multi-column FKs is intentionally omitted; the magnitude of the resulting overestimate has not been quantified here.

## Related Pages

- [[v12/index]]
- [[versions]]
