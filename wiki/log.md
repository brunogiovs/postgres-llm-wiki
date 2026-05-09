# Wiki Log

Append one entry after every scaffold change, version lifecycle event, ingest, trace, lint pass, or filed answer.

## [2026-05-09] filed v12 | Estimate avg_leaf_density without pgstattuple

- Filed `wiki/v12/questions/avg-leaf-density-zero-io-estimate.md` (agent-verified) for a zero-index-I/O catalog-only estimator that reproduces `pgstatindex`'s `avg_leaf_density` for B-tree indexes, including partial indexes, in PostgreSQL 12.
- Verified `pgstatindex` density formula via `pgstatindex_impl` in `contrib/pgstattuple/pgstatindex.c`: `max_avail = pd_special - SizeOfPageHeaderData` per leaf (L296), aggregate `100 * (max_avail - free_space) / max_avail` (L347-L349). Header (24 B) and BTPageOpaque (16 B) are *outside* `max_avail`, not part of the numerator — corrected an earlier draft formula that included them as "used."
- Confirmed page-layout constants: `PageHeaderData` 24 B per `bufpage.h#L151-L164,L216`; `BTPageOpaqueData` 16 B (`btpo_prev` 4 + `btpo_next` 4 + `btpo` union 4 + `btpo_flags` 2 + `btpo_cycleid` 2) per `nbtree.h#L55-L66`; `BTREE_DEFAULT_FILLFACTOR = 90` per `nbtree.h#L169`. Per-leaf usable area is 8152 bytes on default `BLCKSZ`.
- Confirmed `IndexTupleData` 8 B per `itup.h#L35-L51`; `IndexAttributeBitMapData` is a fixed `(INDEX_MAX_KEYS + 7) / 8` = 4 bytes regardless of natts (`INDEX_MAX_KEYS = 32` per `pg_config_manual.h#L52`); `IndexInfoFindDataOffset` returns 8 (no nulls) or 16 (any null) per `itup.h#L80-L90`; `index_form_tuple` ends with `size = MAXALIGN(size)` per `indextuple.c#L132-L133`.
- Confirmed partial-index handling: VACUUM's `lazy_cleanup_index` writes `vac_update_relstats(indrel, stats->num_pages, stats->num_index_tuples, ...)` per `vacuumlazy.c#L1798-L1815`; B-tree's `btvacuumpage` accumulates live tuples as `maxoff - minoff + 1` per `nbtree.c#L1335`; ANALYZE's index path uses `tupleFract = numindexrows / numrows` per `analyze.c#L821-L822`. Both VACUUM and ANALYZE produce post-predicate `relpages` and `reltuples` for partial indexes. `pg_stats.avg_width` is computed table-wide, not predicate-scoped, per `system_views.sql#L196` and `analyze.c#L1784,L1964,L2344` — flagged as the only partial-index accuracy risk.
- Recorded that B-tree VACUUM does *not* truncate the index file: `_bt_delitems_vacuum` only compacts pages via `PageIndexMultiDelete` per `nbtpage.c#L986-L1016`, and recyclable pages are recorded in the FSM per `nbtree.c#L1078-L1089`. Of in-tree index AMs, only SP-GiST calls `RelationTruncate` during vacuum per `spgvacuum.c#L882`. Corrected an earlier draft that conflated B-tree behavior with heap right-edge truncation.
- Production-bound SQL embeds the `/* wiki_pg12_avg_leaf_density_zero_io */` inline tag on every leading verb. Open Questions retain expression-index handling, 32-bit MAXALIGN portability, non-default `BLCKSZ`, the per-tuple HasNulls vs. column-nullable mismatch, and a measured accuracy band.
- Front matter set to `verified: false` / `verified_by_agent: claude-opus-4-7 2026-05-09T00:00:00Z`. Title, `wiki/index.md`, and `wiki/v12/index.md` link text use the agent-reviewed (no `(unverified)`) form.

## [2026-05-09] review v12 | Foreign key join optimization

- Re-reviewed `wiki/v12/questions/foreign-key-join-optimization.md` against the pinned `raw/postgres-12/` checkout (`45b88269...`) via `scripts/source_graph_query --version 12`.
- Verified `get_relation_foreign_keys()` at `plancat.c#L476` (FK collection, inheritance-parent skip at `L498`); `match_foreign_keys_to_quals()` at `initsplan.c#L2413` (EC match via `match_eclasses_to_foreign_key_col` then loose-qual fallback over `con_rel->joininfo`); `get_foreign_key_join_selectivity()` at `costsize.c#L4709` with the `1.0 / Max(ref_rel->tuples, 1.0)` payoff at `L4900`, the JOIN_SEMI/JOIN_ANTI `ref_rel->rows / ref_tuples` branch at `L4888`, and the restrictlist `list_delete_cell()` removal at `L4816`; `calc_joinrel_size_estimate()` call site at `costsize.c#L4589`.
- Tightened the "FK-matched clauses removed" citation from the imprecise `costsize.c#4765` (worklist shallow-copy guard) to the L4759-L4821 removal block, with the failed-removal punt at L4842 also captured.
- Replaced "via equivalence classes or direct qual matching" with the source term of art ("loose quals"), and broadened the inner-join scope statement to include JOIN_LEFT/JOIN_FULL since the same `1/tuples` formula applies to all non-semi/anti joins.
- Promoted the inheritance Open Question into a dedicated `## Inheritance Interaction` section grounded in the `plancat.c#L498-L499` parent skip, the `initsplan.c#L2445-L2447` `RELOPT_BASEREL` requirement, and the `costsize.c#L4862-L4870` XXX comment about FK-covers-children estimation.
- Set `verified_by_agent: claude-opus-4-7 2026-05-09T00:00:00Z`; human `verified: false` preserved. Dropped "(unverified)" from the title and from `wiki/index.md` and `wiki/v12/index.md` link text.

## [2026-05-09] filed v12 | REINDEX CONCURRENTLY disk space requirements

- Filed `wiki/v12/questions/reindex-concurrently-disk-space.md` (unverified) for the disk-space cost of `REINDEX INDEX CONCURRENTLY` on a 10 GB heap with a 5 GB B-tree index.
- Mapped the six phases of `ReindexRelationConcurrently()` to disk impact: phase 1 catalog `_ccnew` row, phase 2 `index_concurrently_build()` → `btbuild()` → `_bt_leafbuild()` build with `tuplesort_performsort()` and `_bt_blwritepage()` WAL via `log_newpage`, phase 3 `validate_index()` heap rescan and TID `tuplesort_begin_datum`, phase 4 `index_concurrently_swap()` `indisvalid` flip, phase 5 dead-mark, phase 6 `performMultipleDeletions(... PERFORM_DELETION_CONCURRENT_LOCK ...)` drop.
- Verified that `index_concurrently_create_copy()` passes `indexRelation->rd_rel->reltablespace` into `index_create()`, so the new file lands in the same tablespace as the old; old and new index files coexist on disk from phase 2 through phase 6.
- Recorded `btws_use_wal = XLogIsNeeded() && RelationNeedsWAL(wstate.index)` in `_bt_leafbuild()`, so WAL volume is roughly the index size on a normal `wal_level >= replica` primary.
- Sizing recipe: ≥ 2× index size free on the index's tablespace (≈10 GB for a 5 GB index), ≥ 1× index size free on `pg_wal` above normal headroom (≈5 GB), and up to ~5 GB temp space for the build sort if `maintenance_work_mem` cannot hold it. Heap is read but not rewritten.
- GUC reload semantics: `temp_tablespaces`, `maintenance_work_mem`, `statement_timeout`, `lock_timeout` all `PGC_USERSET`, so `SET LOCAL` before `REINDEX CONCURRENTLY` needs no restart or reload.
- Front matter set to `verified: false` / `verified_by_agent: not yet`; visible title and link text use `(unverified)`.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md` to link the new page and reflect coverage.

## [2026-05-08] question v12 | Foreign key join optimization

- Filed `wiki/v12/questions/foreign-key-join-optimization.md` with comprehensive analysis of how foreign key constraints influence query planner join optimization in PostgreSQL 12.
- Analysis covers FK constraint collection during planning, matching join conditions to FK relationships, selectivity estimation using FK semantics (1/referenced-table-size for inner joins), removal of FK-matched clauses from restrictlists, and special handling for semi/anti joins.
- Cited `get_relation_foreign_keys()` in `plancat.c`, `match_foreign_keys_to_quals()` in `initsplan.c`, `get_foreign_key_join_selectivity()` in `costsize.c`, and `match_eclasses_to_foreign_key_col()` in `equivclass.c`.
- Front matter set to `verified: false` / `verified_by_agent: not yet`.
- Updated `wiki/index.md` and `wiki/v12/index.md` to link the new page.

## [2026-05-08] question v12 | NULL inequality comparison behavior

- Filed `wiki/v12/questions/null-inequality-comparison-behavior.md` explaining why `SELECT * FROM users WHERE status_id <> 1` excludes rows where `status_id` is NULL.
- Behavior grounded in PostgreSQL's NULL comparison semantics (any comparison with NULL yields NULL) and WHERE clause NULL handling (NULL treated as FALSE) in the expression evaluator.
- Cited `EEOP_QUAL` in `execExprInterp.c` for WHERE qualification logic.
- Front matter set to `verified: false` / `verified_by_agent: claude-opus-4-7 2026-05-08T20:00:00Z`.
- Updated `wiki/index.md` and `wiki/v12/index.md` to link the new page.

## [2026-05-08] question v12 | Foreign key join optimization

- Filed `wiki/v12/questions/foreign-key-join-optimization.md` with source-grounded analysis of how foreign key constraints affect query planner join optimization in PostgreSQL 12.
- Analysis covers selectivity estimation via `eqjoinsel()`, join ordering in `join_search()`, and runtime enforcement through triggers.
- Foreign keys do not provide special optimization hints; planner uses column statistics only.
- Cited `pg_constraint` catalog, `eqjoinsel()` in `selfuncs.c`, and `joinpath.c` for join planning.
- Front matter set to `verified: false` / `verified_by_agent: not yet`.
- Updated `wiki/index.md` and `wiki/v12/index.md` to link the new page.

## [2026-05-08] question v12 | Two-table vs jsonb item attributes

- Filed `wiki/v12/questions/two-table-vs-jsonb-item-attributes.md` with comprehensive pros/cons analysis of normalized `item` + `item_attributes` tables versus single `item` table with `jsonb` attributes column.
- Analysis covers schema flexibility, data integrity, performance, indexing, and migration considerations based on PostgreSQL 12's jsonb capabilities.
- Added section on jsonb update performance implications: full value reconstruction costs, TOAST overhead for small changes, GIN index maintenance costs, and MVCC/WAL impact.
- Cited jsonb implementation (`jsonb.c`, `jsonb.h`), operators/functions from test suite, GIN indexing support (`jsonb_gin.c`), and `setPath()` function behavior.
- Front matter set to `verified: false` / `verified_by_agent: not yet`.
- Updated `wiki/index.md` and `wiki/v12/index.md` to link the new page.

## [2026-05-08] question v12 | Query planner settings inventory and non-default sampling

- Filed `wiki/v12/questions/query-planner-settings-non-default-and-inventory.md` with a `pg_settings` query that flags non-default planner GUCs across the four `Query Tuning / *` categories (including the partitioned-table GUCs `enable_partitionwise_join`, `enable_partitionwise_aggregate`, `enable_partition_pruning`, and `constraint_exclusion`), plus a per-GUC inventory of every planner setting with defaults, ranges, enum options, and how each affects the planner.
- Categories pinned via `config_group_names[]` at `guc.c#L681-L690`; `pg_settings` view shape via `system_views.sql#L512-L513` and the `pg_show_all_settings` declaration in `pg_proc.dat`. All planner GUCs are `PGC_USERSET`, so the page records that no planner setting requires restart.
- Front matter set to `verified: false` / `verified_by_agent: not yet`; visible title and link text use `(unverified)`.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md` to link the new page and reflect coverage.

## [2026-05-08] review v12 | Bgwriter tuning and Checkpoint monitoring scenarios

- Re-reviewed `wiki/v12/questions/bgwriter-tuning-recommendations.md` and `wiki/v12/questions/checkpoint-monitoring-optimization-scenarios.md` against the pinned `raw/postgres-12/` checkout (`45b88269...`) via `scripts/source_graph_query --version 12`.
- Bgwriter verification: the four GUCs (defaults/ranges/`PGC_SIGHUP`) in `guc.c#L2728-L2757` and `guc.c#L3351-L3359`; `DEFAULT_BGWRITER_FLUSH_AFTER`/`WRITEBACK_MAX_PENDING_FLUSHES` in `pg_config_manual.h#L153-L163`; `BackgroundWriterMain` loop and `HIBERNATE_FACTOR` in `bgwriter.c#L73`/`L240-L373`; `BgBufferSync` (`bgwriter_lru_multiplier`, `bgwriter_lru_maxpages`, `m_maxwritten_clean`, `m_buf_written_clean`) in `bufmgr.c#L2200-L2300`; checkpoint-write accumulator in `bufmgr.c#L1991-L1994`; backend-write/fsync counter wiring in `checkpointer.c#ForwardSyncRequest` and `AbsorbSyncRequests`; `pg_stat_bgwriter` SQL functions in `pgstatfuncs.c#L1605-L1670`; view definition in `system_views.sql#L935-L947`; bgwriter doc paragraphs in `config.sgml#L2025-L2160`.
- Checkpoint verification: `checkpoint_timeout`, `checkpoint_completion_target`, `checkpoint_flush_after`, `checkpoint_warning`, `max_wal_size`, `min_wal_size`, `log_checkpoints` GUCs in `guc.c`; `XLogCheckpointNeeded` and `CalculateCheckpointSegments` in `xlog.c#L2255-L2361`; `CheckPointWarning` use site with the `CheckPointTimeout < CheckPointWarning` skip in `checkpointer.c#L440-L463`; `pgstat_reset_shared_counters` cluster-wide reset in `pgstat.c#L1320-L1352`; `pg_settings` view as `SELECT * FROM pg_show_all_settings()` in `system_views.sql#L512-L513`; checkpoint section text in `wal.sgml#L460-L609`.
- Tone pass on the bgwriter page: dropped two AGENTS.md self-references (the wiki should not cite its own meta-instructions) and tightened the closing session-timeout sentence into one-claim-per-sentence form.
- Set `verified_by_agent: claude-opus-4-7 2026-05-08T00:00:00Z` on both pages and dropped "(unverified)" from page titles, `wiki/index.md`, and `wiki/v12/index.md`. Human `verified: false` preserved on both.

## [2026-05-08] tone v12 | Enable I/O timing measurements on production

- Tone pass on `wiki/v12/questions/enable-io-timing-measurements-production.md` against AGENTS.md "Tone And Readability" rules.
- Replaced the Answer-section opening: dropped the redundant "Assumption: ..." line (front matter already pins the commit), turned the long compound recommendation into a 5-step numbered TL;DR, and split the restart/reload semantics from the cost/output-surfaces paragraph.
- Tightened the Section 1 observation-window guidance to name a concrete floor ("at least several minutes") rather than the vague "long enough to smooth stats-collector delay."
- Split semicolon run-ons in the `pg_settings`/`pg_file_settings` description, the session-scope explanation, the `delta_blk_read_time` interpretation, and the multi-clause `pg_stat_statements` upgrade-chain paragraph into one-claim-per-sentence form.
- Cut filler line "Those two streams feed two surfaces:" to a more concrete lead, and the redundant "The resulting numbers are PostgreSQL block I/O call timings" intro under "What PG12 Measures."
- Every pre-existing citation preserved across the rewrites.
- Updated `verified_by_agent: claude-opus-4-7 2026-05-08T17:52:54Z`.

## [2026-05-08] review v12 | Enable I/O timing measurements on production refresh

- Re-reviewed `wiki/v12/questions/enable-io-timing-measurements-production.md` against the pinned `raw/postgres-12/` checkout (`45b88269...`) via `scripts/source_graph_query --version 12`. Re-verified `track_io_timing` (`PGC_SUSET`, default off), `ReadBuffer_common`/`FlushBuffer` timing wrapping `smgrread`/`smgrwrite`, `pg_stat_get_db_blk_read_time`/`write_time` µs→ms conversion, `BufferUsage` shape, `pg_reload_conf` SIGHUP, `ALTER SYSTEM` semantics, `pg_stat_database` columns (no `blks_written`), and `pg_stat_statements` `_PG_init` shared-preload gating.
- Fixed misleading phrasing on the pg_stat_statements upgrade chain: the 1.4 → 1.5, 1.5 → 1.6, and 1.6 → 1.7 incrementals do not modify `blk_read_time`/`blk_write_time` (only `pg_stat_statements_reset()` grants and signature change); reworded to clarify the columns come from the 1.4 base file and survive the upgrade chain unchanged. Added incremental-script citations.
- Completed the `ALTER SYSTEM` restriction note to "transaction block or function" per `alter_system.sgml`.
- Updated `verified_by_agent: claude-opus-4-7 2026-05-08T17:46:35Z`; human `verified: false` unchanged.

## [2026-05-08] review v12 | Enable I/O timing measurements on production

- Re-reviewed `wiki/v12/questions/enable-io-timing-measurements-production.md` against the pinned `raw/postgres-12/` checkout (`45b88269...`). All behavioral claims verified through `scripts/source_graph_query --version 12` against `guc.c`, `bufmgr.c`, `pgstat.c`, `pgstatfuncs.c`, `system_views.sql`, `signalfuncs.c`, `utility.c`, `explain.c`, and `contrib/pg_stat_statements/`.
- Added a note that `pg_stat_statements.control` pins `default_version = '1.7'` and that the 1.4 → 1.5 → 1.6 → 1.7 upgrade scripts do not change the view shape, so the `blk_read_time` / `blk_write_time` columns work regardless of installed version. Added the control file to the Evidence Map.
- Tightened the Section 5 write-time interpretation to point at concrete write-count sources (`EXPLAIN ... BUFFERS`, `pg_stat_statements`, and `pg_stat_bgwriter` columns `buffers_clean`, `buffers_backend`, `buffers_checkpoint`).
- Set `verified_by_agent: claude-opus-4-7 2026-05-08T16:52:54Z`; human `verified: false` unchanged.

## [2026-05-08] filed v12 | Planning metrics and generic/custom replanning visibility

- Filed `wiki/v12/questions/planning-metrics-generic-custom-replans.md` (unverified) for PG 12 planning visibility and generic/custom prepared-plan monitoring.
- Covered `EXPLAIN EXECUTE` as the source-documented per-sample classifier, `EXPLAIN` planning time, `pg_prepared_statements` column limits, `pg_stat_statements` execution-only counters in PG 12, `log_planner_stats`, `auto_explain`, and plan-cache invalidation boundaries.
- Verified that PG 12 keeps `generic_cost`, `total_custom_cost`, and `num_custom_plans` in `CachedPlanSource`, but exposes no built-in SQL counter for generic/custom transitions.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.

## [2026-05-08] update v12 | Inheritance no-pruning force_generic_plan impact

- Expanded `wiki/v12/questions/inheritance-partition-no-pruning-overhead.md` with a dedicated `force_generic_plan` analysis.
- Clarified that `force_generic_plan` can reduce repeated planning overhead for saved prepared statements when all representative parameters still produce the same all-child plan, but it cannot reduce executor visits to surviving inheritance children.
- Added source backing for `choose_custom_plan()`, `GetCachedPlan()`, `BuildCachedPlan()`, `CheckCachedPlan()`, `AcquireExecutorLocks()`, `PARAM_FLAG_CONST`, parameter substitution, and the PG 12 `plancache` regression case.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.

## [2026-05-08] update v12 | Plan cache mode CheckCachedPlan analysis

- Expanded `wiki/v12/questions/plan-cache-mode-production-impact.md` with a comprehensive `CheckCachedPlan()` deep dive.
- Covered `GetCachedPlan()` call order, `CachedPlanSource` / `CachedPlan` state, role-dependent invalidation, executor-lock acquisition and race recheck, transient-plan `TransactionXmin` invalidation, relcache/syscache invalidation callbacks, `ReleaseGenericPlan()`, and operational consequences for generic-plan reuse.
- Added guidance that planner-cost GUC experiments against existing generic plans should deallocate/reprepare or use `DISCARD PLANS`, since valid generic plans are not rejected merely because cost GUCs changed.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.

## [2026-05-08] filed v12 | Plan cache mode production impact

- Filed `wiki/v12/questions/plan-cache-mode-production-impact.md` (unverified) with a source-grounded PG 12 analysis of `plan_cache_mode` in production.
- Covered `auto`, `force_custom_plan`, and `force_generic_plan`, including plan-cache decision thresholds, custom/generic pros and cons, prepared-statement and PL/pgSQL/SPI/extended-protocol boundaries, invalidation edge cases, and a production probe pattern.
- Added a slow-random-I/O section tying plan-cache mode risk to PG 12 planner cost constants, index/seq scan costing, `random_page_cost`, `effective_cache_size`, and `effective_io_concurrency`.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.

## [2026-05-08] tooling | no-LLM Graphify generation default

- Changed `scripts/source_graph` so graph generation uses Graphify's local AST-only update path by default and no longer requires an LLM backend/API key.
- Kept LLM-backed semantic extraction available behind explicit `--semantic --backend ...` flags.
- Generated the PostgreSQL 12 AST-only graph under `.wiki-runtime/graph/postgres-12/` and checked it with `scripts/source_graph_check --version 12`.
- Verified graph querying with `scripts/source_graph_query --version 12 explain executor_execmain_executorrun`.
- Updated docs and tests for the no-LLM default graph generation path.

## [2026-05-08] tooling v12 | Graphify CLI compatibility

- Updated `scripts/source_graph` to invoke the installed Graphify CLI with `graphify update <source> --force` by default; semantic `graphify extract` is opt-in via `--semantic --backend ...`. Tool status now records the resolved binary path or `missing` rather than parsing `graphify --help`.
- `scripts/source_graph` now moves `graphify-out/` contents up into the version graph directory and removes the now-empty `graphify-out/`, eliminating the duplicate on-disk copy that previously doubled graph state.
- Added Graphify backend/model pass-through options for extraction.
- Reran `scripts/source_graph --version 12 --refresh`; the wrapper now reaches Graphify extraction, but `graph.json` remains deferred because no LLM API key/backend is configured.

## [2026-05-08] tooling | source graph query cleanup

- Trimmed `scripts/source_graph_query` so raw symbol searches prefer the pinned checkout's tracked Git file set before falling back to filesystem search tools.
- Added test coverage that untracked files under `raw/postgres-NN/` do not leak into source symbol results.
- Removed generated legacy source-context/build runtime directories and old source-context tool logs.
- Ran `scripts/test_source_tools` and `scripts/wiki_lint`; both passed.

## [2026-05-08] tooling | graph-only source navigation cutover

- Removed the legacy source-context and source-lookup scripts (`source_context`, `source_context_check`, `source_deps`, and `source_lookup`) from the active tool surface.
- Reworked `scripts/source_graph_query` as the graph-only source query entrypoint, with raw source subcommands for symbol search, file slices, source history, direct includes, and reverse include scans.
- Made graph query subcommands force `graph.json` generation through `scripts/source_graph --version NN --refresh` when the graph is absent.
- Replaced the old context-pack tests and active docs with graph-only source navigation guidance.

## [2026-05-07] tooling | Graphify source graph wrappers

- Added `scripts/source_graph`, `scripts/source_graph_query`, and `scripts/source_graph_check` as version-pinned wrappers for optional Graphify graph generation, query/path/explain lookup, and graph sanity checks under `.wiki-runtime/graph/postgres-NN/`.
- Added synthetic test coverage with a fake `graphify` CLI for missing-tool handling, graph artifact copying, query wrappers, source-pin checks, and wrong-version graph references.
- Updated `AGENTS.md`, `README.md`, `postgresql-engine-wiki-plan.md`, `wiki/index.md`, `wiki/overview.md`, `wiki/versions.md`, and version landing pages so Graphify is documented as an orientation layer while raw source citations remain mandatory evidence.

## [2026-05-07] tooling v12 | source context check false-positive cleanup

- Fixed `scripts/source_context` so compile-database include dependency generation deduplicates source files that resolve through build-tree symlinks to the same raw checkout path.
- Fixed `scripts/source_context_check` reference scanning so configured install prefixes and compiler diagnostic `path:line:column` text do not appear as missing project artifacts; issue counts now include suppressed diagnostics.
- Regenerated the PostgreSQL 12 context pack with focused callgraphs restored and reran `scripts/source_context_check --version 12`; the check now exits successfully with only raw-dependency coverage warnings.
- Fixed the WAL high-throughput question's visible unverified title hint and `## Source References` section after `scripts/wiki_lint` flagged the missing source-reference section.

## [2026-05-07] filed v12 | WAL directory high throughput low latency disk improvements

- Filed `wiki/v12/questions/wal-high-throughput-low-latency-disk-improvements.md` analyzing how fast WAL storage improves PostgreSQL 12 operations.
- Grounded the answer in pinned source for `XLogFlush()` during commits, `CreateCheckPoint()` WAL flushing, `XLogBackgroundFlush()` background writing, and `issue_xlog_fsync()` segment switches.
- Cited WAL write operations (`pg_pwrite()`, `WAIT_EVENT_WAL_WRITE`) and sync operations (`pg_fsync()`, `WAIT_EVENT_WAL_SYNC`).
- Updated `wiki/index.md` and `wiki/v12/index.md`.

## [2026-05-07] filed v12 | Separate WAL disk full and replication slots

- Filed `wiki/v12/questions/wal-separate-disk-full-replication-slots.md` for PostgreSQL 12 WAL-on-separate-disk behavior when the WAL filesystem fills.
- Grounded the answer in pinned source for replication-slot `restart_lsn` retention, checkpoint WAL cleanup boundaries, full `pg_wal` PANIC behavior, WAL-before-data enforcement, slot persistence under `pg_replslot`, and `pg_replication_slots` monitoring.
- Added a production-safe retained-WAL diagnostic query with inline trace tag and session-scoped timeouts.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.

## [2026-05-07] filed v12 | Azure disk configuration recommendations

- Filed `wiki/v12/questions/azure-disk-configuration-recommendations.md` (unverified) for prompt-provided Azure Ultra Disk, Premium SSD v2, Premium SSD, Standard SSD, and Standard HDD options.
- Grounded PG 12 recommendations in pinned source for planner storage costs, `effective_io_concurrency`, checkpoint/WAL pacing, bgwriter/writeback, temp spill placement, durability settings, `pg_settings`, `pg_stat_database`, and `pg_stat_bgwriter`.
- Added production-safe SQL snippets with inline trace tags and session timeouts, plus context-reviewed/evidence-map/open-question sections.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.

## [2026-05-07] review v12 | Bgwriter backend-write-share thresholds

- Expanded `wiki/v12/questions/bgwriter-tuning-recommendations.md` with a source-grounded explanation of `buffers_backend / (buffers_clean + buffers_backend + buffers_checkpoint)`.
- Added practical backend-write-share heuristic bands (`0%`-`2%`, `>2%`-`5%`, `>5%`-`10%`, `>10%`-`20%`, `>20%`-`40%`, `>40%`) and per-band actions for `bgwriter_lru_maxpages`, `bgwriter_lru_multiplier`, and `bgwriter_delay`.
- Added `buffers_checkpoint` counter wiring, refreshed context-reviewed/evidence-map notes, and fixed production SQL snippets to use inline trace tags on every statement.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md` coverage text.

## [2026-05-07] update v12 | Checkpoint configuration inventory query

- Updated `wiki/v12/questions/checkpoint-monitoring-optimization-scenarios.md` to fold the follow-up into the `## Question` section and add a production-safe `pg_settings` query for checkpoint-related configuration inventory.
- Checked the query columns against the PG 12 `pg_settings` view and catalog docs, and checked adjacent GUCs for direct checkpoint control, WAL volume after checkpoints, and WAL retention/archive pressure.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md` to mention the added `pg_settings` inventory query.

## [2026-05-07] filed v12 | Checkpoint monitoring and optimization scenarios

- Filed `wiki/v12/questions/checkpoint-monitoring-optimization-scenarios.md` (unverified) covering PG 12 checkpoint monitoring through `pg_stat_bgwriter` and `log_checkpoints`, source-grounded checkpoint/WAL GUC tuning, reload semantics, and deployment scenarios for fast local disks and cloud block storage.
- Checked source paths for timed and WAL-caused checkpoint triggers, checkpoint write/sync phases, `checkpoint_completion_target` pacing, WAL retention/recycling, `pg_stat_bgwriter` view wiring, `pg_stat_reset_shared('bgwriter')`, `pg_reload_conf()`, and SQL timeout GUCs.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md` with visible `(unverified)` link text and coverage notes.
- Open questions: the pinned PG 12 source does not contain AWS/Azure-specific disk behavior or universal numeric checkpoint target values.

## [2026-05-07] review v12 | track_io_timing boundary in disk I/O review

- Extended `wiki/v12/questions/disk-io-before-after-query-plan-execution.md` with a precise PostgreSQL 12 `track_io_timing` boundary analysis.
- Verified the `ReadBuffer_common` `smgrread` timer, `FlushBuffer` `smgrwrite` timer, relation-extension exclusion, temp `BufFile` block counters without timing, WAL write/sync separation, foreground/parallel/background instrumentation boundaries, and `pg_stat_database` / `EXPLAIN` / `pg_stat_statements` exposure paths.
- Refreshed `verified_by_agent: gpt-5 2026-05-07T02:01:08Z` and updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.
- Ran `scripts/wiki_lint`; result: `0 error(s), 0 warning(s)`.

## [2026-05-07] review v12 | Disk I/O before/after query planning and execution

- Re-reviewed `wiki/v12/questions/disk-io-before-after-query-plan-execution.md` against pinned PostgreSQL 12 sources and `.wiki-runtime/context/postgres-12/`.
- Rewrote the answer around query lifecycle boundaries, catalog and relcache access, planner relation-size probes, shared-buffer hits versus storage reads, DML writes, hint bits, temp spills, WAL flushes, bgwriter/checkpointer writes, and DDL/maintenance file operations.
- Set `verified_by_agent: gpt-5 2026-05-07T01:34:17Z`, removed the stale visible `(unverified)` title hint, and updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.
- Ran `scripts/wiki_lint`; result: `0 error(s), 0 warning(s)`.

## [2026-05-06] lint | wiki health check

- Ran `scripts/wiki_lint` after filing the PostgreSQL 12 inheritance partition no-pruning overhead question.
- Result: `0 error(s), 0 warning(s)`.

## [2026-05-06] filed v12 | Inheritance partition no-pruning overhead

- Filed `wiki/v12/questions/inheritance-partition-no-pruning-overhead.md` for a PostgreSQL 12 traditional-inheritance query that must visit roughly 300 children because no pruning is possible.
- Covered source-grounded overhead reducers and overhead adders: `constraint_exclusion`, generic/custom plan choice, child indexes and stats, planner cost knobs, parallel append, JIT, partitionwise options, `track_io_timing`, `auto_explain`, and executor/planner stats logging.
- Verified the inheritance expansion, constraint-exclusion, append execution, declarative partition pruning boundary, GUC contexts, and instrumentation paths against pinned `raw/postgres-12/` sources and `.wiki-runtime/context/postgres-12/`; set `verified_by_agent: gpt-5 2026-05-06T22:40:55Z`.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.

## [2026-05-06] review v12 | Re-review I/O timing measurements procedure

- Re-reviewed `wiki/v12/questions/enable-io-timing-measurements-production.md` against pinned `raw/postgres-12/` sources and `.wiki-runtime/context/postgres-12/` pack.
- Confirmed GUC definition, timing instrumentation sites in buffer manager, stats collection and exposure paths, and reload/session semantics.
- Updated `verified_by_agent: Cline 2026-05-06T20:33:00Z`.

## [2026-05-06] tooling v12 | Add contrib compile capture to source context

- Updated `scripts/source_context` so Bear captures the normal PostgreSQL build and then appends a `make -C contrib` capture when the checkout has contrib sources.
- Refreshed `.wiki-runtime/context/postgres-12/`; `compile_commands.json` now includes `contrib/pg_stat_statements/pg_stat_statements.c`.
- Updated `wiki/v12/questions/enable-io-timing-measurements-production.md`, `wiki/v12/index.md`, and `wiki/versions.md` to remove the stale compile-unit gap, record the expanded context coverage, and drop a stale coverage note for a removed v12 corruption catalog.

## [2026-05-06] remove v12 | Corruption log entries with data checksums disabled

- Removed `wiki/v12/questions/corruption-log-entries.md` per user request.
- Updated `wiki/index.md` and `wiki/v12/index.md` to remove links.

## [2026-05-06] filed v12 | Enable I/O timing measurements on production

- Filed `wiki/v12/questions/enable-io-timing-measurements-production.md` with a PostgreSQL 12 production procedure for enabling `track_io_timing`, including `pg_test_timing` preflight, `ALTER SYSTEM` + `pg_reload_conf()` rollout, session-only fallback, tagged SQL sampling, `pg_stat_database` deltas, optional `pg_stat_statements`, and `EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)` drill-down guidance.
- Verified GUC scope and restart/reload/session semantics against `guc.c`, `guc.h`, `catalogs.sgml`, `alter_system.sgml`, and `signalfuncs.c`; verified timing collection through `bufmgr.c`, `pgstat.h`, `pgstat.c`, `pgstatfuncs.c`, `system_views.sql`, `instrument.c`, `explain.c`, and `pg_stat_statements.c`.
- Set `verified: false` and `verified_by_agent: gpt-5 2026-05-06T20:05:37Z`; updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md`.

## [2026-05-06] cleanup v12 | Remove generated question HTML

- Removed `convert_md_to_html.py`.
- Removed generated question HTML files under `wiki/v12/questions/`.

## [2026-05-06] html v12 | Generated HTML for PostgreSQL 12 questions

- Generated HTML versions of `wiki/v12/questions/bgwriter-tuning-recommendations.md` and `wiki/v12/questions/corruption-log-entries.md` using a Python script that converts Markdown to HTML with Obsidian-style link support.
- HTML files include proper `<a href>` links for source citations and wiki links, following AGENTS.md Obsidian-style link conventions.
- Added basic CSS styling for readability, including table formatting and code blocks.

## [2026-05-06] filed v12 | Bgwriter tuning recommendations

- Filed `wiki/v12/questions/bgwriter-tuning-recommendations.md` (unverified) covering the four PG 12 bgwriter GUCs (`bgwriter_delay`, `bgwriter_lru_maxpages`, `bgwriter_lru_multiplier`, `bgwriter_flush_after`): defaults, ranges, `PGC_SIGHUP` reload semantics, and a source-grounded direction-of-change matrix across default / write-heavy / read-mostly / disable / Linux flush-after / non-Linux / flush-after-regression scenarios.
- Verified `pg_stat_bgwriter` counter wiring end-to-end against the pinned source: view definition in `system_views.sql`, SQL functions in `pgstatfuncs.c`, accumulators in `bufmgr.c` (`m_buf_written_clean`, `m_maxwritten_clean`) and `checkpointer.c` (`num_backend_writes`, `num_backend_fsync`), and aggregator in `pgstat.c`.
- Source backing for direction-of-change drawn from `doc/src/sgml/config.sgml` bgwriter subsection (L2030-L2158) and the GUC entries in `src/backend/utils/misc/guc.c` and `src/include/pg_config_manual.h`.
- Set `verified: false` and `verified_by_agent: not yet`; titled and linked with `(unverified)` hint per AGENTS.md. Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md` coverage text.
- Open questions: PG 12 source does not encode numeric per-scenario recommendations beyond the documented defaults; `HIBERNATE_FACTOR = 50` is a non-GUC compile-time constant; `bgwriter_flush_after` effectiveness on non-Linux Unix variants is not characterized by the v12 tree.

## [2026-05-06] docs | project plan source-tool sync

- Updated `postgresql-engine-wiki-plan.md` to reflect the implemented source-context packs, project-local source tooling, explicit source-tool version pins, synthetic tests, and current `AGENTS.md` maintenance rules.

## [2026-05-06] tooling | explicit source-tool version pins

- Made `scripts/source_lookup` and `scripts/source_deps` require `--version NN` instead of defaulting to the primary PostgreSQL version.
- Made `scripts/source_context` require an explicit scope through `--version NN` or `--all`.
- Added synthetic source-tool tests for omitted version pins and updated `AGENTS.md`, `wiki/index.md`, `wiki/overview.md`, and implementation notes to state the hard rule.

## [2026-05-06] tooling | unverified document title hints

- Updated `AGENTS.md` so any unverified managed wiki document, including question pages, must show an `(unverified)` hint in its visible title and index or landing-page link text without adding extra question front-matter fields.

## [2026-05-06] tooling | source script instruction coverage

- Expanded `AGENTS.md` source-tooling guidance to cover the current `source_lookup`, `source_deps`, `source_context`, `source_update`, `test_source_tools`, and `version_diff` command surfaces, including regex lookup, path/log slices, JSON dependency output, full compile commands, textual context fallback, refresh/dry-run/all context generation, and branch/commit checkout overrides.

## [2026-05-06] tooling | source lookup synthetic end-to-end tests

- Added `tests/test_source_tools.py`, which builds a temporary synthetic wiki, `raw/postgres-99/` checkout, git history, and `.wiki-runtime/context/postgres-99/` pack to exercise `scripts/source_lookup` and `scripts/source_deps` as subprocess CLIs.
- Added `scripts/test_source_tools` as the one-command test runner and listed it in `AGENTS.md` and `wiki/index.md`.

## [2026-05-06] delete v12 | track_io_timing measurement question

- Deleted `wiki/v12/questions/measure-io-overhead-with-track-io-timing.md` as requested.
- Removed links from `wiki/index.md` and `wiki/v12/index.md`.
- Updated coverage notes in `wiki/v12/index.md` and `wiki/versions.md`.

## [2026-05-06] tooling | source dependency context lookup

- Added `scripts/source_deps`, a read-only helper over `.wiki-runtime/context/postgres-NN/include-deps.txt` and `compile_commands.json` for direct include lookup, reverse include users, compile-unit context, and bounded transitive include traversal.
- Updated `AGENTS.md` and `wiki/index.md` so future agents discover the dependency lookup workflow before falling back to ad hoc searches.
- Fixed the v12 question source-reference heading and landing-page link shape so `scripts/wiki_lint` recognizes the existing evidence and inbound link.

## [2026-05-05] maintenance v12 | removed unverified stray question page

- Deleted `wiki/v12/questions/measure-io-overhead.md`. The file appeared untracked in the working tree during the `track_io_timing` question session and contained claims contradicting the pinned v12 source: it asserted `track_io_timing` does not exist in PG 12 (it does, declared `PGC_SUSET` at `raw/postgres-12/src/backend/utils/misc/guc.c#L1402`), cited `raw/postgres-12/src/include/utils/guc_tables.h` (a file that does not exist on this checkout), claimed `log_min_duration_statement` is `PGC_SUSET` (it is `PGC_SUSET`), and linked to `wiki/v12/concepts/` pages that do not exist.
- The verified replacement was `v12/questions/measure-io-overhead-with-track-io-timing`, filed earlier that day and later deleted on 2026-05-06.

## [2026-05-05] verify v12 | track_io_timing production measurement procedure

- Set `verified_by_agent: Cline 2026-05-05T22:10:00Z` on `v12/questions/measure-io-overhead-with-track-io-timing` after re-checking all claims against the pinned `raw/postgres-12/` source.

## [2026-05-05] question v12 | track_io_timing production measurement procedure

- Filed `v12/questions/measure-io-overhead-with-track-io-timing` covering host clock-source qualification with `pg_test_timing`, cluster-wide enable via `ALTER SYSTEM` + `pg_reload_conf()`, delta sampling from `pg_stat_database` and `pg_stat_statements`, and per-plan drill-down via `EXPLAIN (ANALYZE, BUFFERS)`.
- GUC scope verified `PGC_SUSET` against `raw/postgres-12/src/backend/utils/misc/guc.c` and `src/include/utils/guc.h`; instrumentation sites verified in `src/backend/storage/buffer/bufmgr.c` and `src/backend/commands/explain.c`. Counter exposure verified in `src/backend/utils/adt/pgstatfuncs.c`, `src/backend/catalog/system_views.sql`, and `contrib/pg_stat_statements/pg_stat_statements.c`.
- Updated `wiki/index.md` and `wiki/v12/index.md` to link the new question.
- Removed stale `## Diagrams` / `#### Diagrams` sections from `wiki/v12/index.md` and `wiki/index.md`; the linked files were deleted in the prior diagram cleanup commit but the links were left behind.

## [2026-05-05] maintenance | removed all diagrams and cleaned up log.md

- Removed all diagram files and directories (`wiki/diagrams/`, `wiki/v12/diagrams/`)
- Cleaned up `wiki/log.md` by removing malformed entries and obsolete diagram-related log entries

## [2026-05-06] filed v12 | Database corruption log entries catalog

- Filed `wiki/v12/questions/corruption-log-entries.md` with comprehensive catalog of 39 PostgreSQL 12 log messages indicating potential database corruption, each with explanation and confidence score (0-100%) for corruption likelihood.
- Updated `wiki/index.md` and `wiki/v12/index.md` with links to the new question page.
- Sourced from grep searches across `raw/postgres-12/` for corruption-related error messages, verified with `scripts/source_lookup`.

## [2026-05-06] review v12 | Corruption log entries catalog

- Re-reviewed `wiki/v12/questions/corruption-log-entries.md` against pinned `raw/postgres-12/` sources and the v12 context pack.
- Rewrote the catalog around source-visible `ERRCODE_DATA_CORRUPTED`, `ERRCODE_INDEX_CORRUPTED`, checksum, invalid-page, WAL-validation, relation-map, replication-state, and low-confidence internal-state messages.
- Set `verified_by_agent: gpt-5 2026-05-06T12:59:39Z`; kept human `verified: false`.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md` to remove unverified title/link hints and reflect the reviewed coverage.

## [2026-05-06] docs | source-context tool testing requirements

- Updated `postgresql-engine-wiki-plan.md` with high-level testing requirements derived from `tests/test_source_tools.py`.
- Captured expected coverage for explicit source-tool scopes, lookup behavior, dependency queries, output contracts, path safety, missing-pack errors, context-pack generation, compile database handling, textual fallback, and source-context producer/consumer compatibility.

Use this prefix shape:

```md
## [YYYY-MM-DD] <kind> v<NN> | <subject>
```

## [2026-05-06] review v12 | Corruption log entries deep inquiry refresh

- Re-reviewed `wiki/v12/questions/corruption-log-entries.md` against the pinned PostgreSQL 12 source checkout and `.wiki-runtime/context/postgres-12/` pack.
- Added missing source-visible families for `pageinspect` heap tuple decoding, additional WAL reader/decoder failures, logical replication state-file short reads, and `pg_resetwal` control-file warnings.
- Added `## Context Reviewed`, `## Evidence Map`, and `## Open Questions` to document the review envelope; refreshed `verified_by_agent: gpt-5 2026-05-06T18:16:24Z`.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md` coverage text.

## [2026-05-06] docs | deep inquiry context requirements

- Updated `postgresql-engine-wiki-plan.md` and `AGENTS.md` so all questions default to a deep inquiry context envelope before drafting.
- Added requirements to inspect source neighborhoods, callers, callees, includes, compile units, tests, docs, catalogs, grammar, history, version boundaries, and context-pack gaps.
- Added question-page expectations for `## Context Reviewed` and `## Evidence Map` so future answers expose both evidence coverage and remaining gaps.

## [2026-05-06] review v12 | Checksum-disabled corruption log entries catalog

- Reworked `wiki/v12/questions/corruption-log-entries.md` for PostgreSQL 12 clusters with data checksums disabled.
- Moved data-page checksum and basebackup checksum-failure messages into an excluded enabled-checksum-only section, verified from `DataChecksumsEnabled()`, `PageIsVerified()`, basebackup gating, and `pg_checksums` mode checks.
- Added checksum-disabled-relevant TOAST, B-tree half-dead internal page, control-file utility, and low-confidence internal-state messages with source citations and confidence scores.
- Updated `wiki/index.md`, `wiki/v12/index.md`, and `wiki/versions.md` coverage text.

## [2026-05-07] tooling | raw-rooted source context sanity checker

- Added `scripts/source_context_check`, a version-pinned context-pack sanity checker that starts from raw PostgreSQL source artifacts, walks live C/header include dependencies, cross-checks the raw-derived graph against `.wiki-runtime/context/postgres-NN/include-deps.txt`, scans context artifacts for missing or wrong-version project references, validates manifest/build-config/compile-db/callgraph consistency, and exercises the source navigation commands.
- Added synthetic regression coverage for the checker, including raw dependency traversal and missing pack-coverage reporting.
- Updated `AGENTS.md`, `wiki/index.md`, and `postgresql-engine-wiki-plan.md` so maintainers discover the new workflow.
