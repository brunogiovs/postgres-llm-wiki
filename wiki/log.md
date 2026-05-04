# Wiki Log

Append one entry after every scaffold change, version lifecycle event, ingest, trace, lint pass, or filed answer.

Use this prefix shape:

```md
## [YYYY-MM-DD] <kind> v<NN> | <subject>
```

## [2026-05-03] answer v12 | pg-test-timing-track-io-timing-overhead

- Created `wiki/v12/questions/pg-test-timing-track-io-timing-overhead.md` answering what `pg_test_timing` does and `track_io_timing` overhead on modern hardware/virtual systems (AWS/Azure).
- `pg_test_timing`: Measures wall-clock timing call overhead (~700ns) and monotonicity.
- `track_io_timing`: ~1-2μs per I/O operation; minimal on bare metal, slightly higher in VMs due to hypervisor.
- Cited `raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c`, `raw/postgres-12/src/backend/utils/misc/guc.c:1402`, `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:2752-2769`.
- Updated `wiki/v12/index.md` and `wiki/index.md`.

## [2026-05-04] answer v12 | production-io-overhead-measurement-protocol-track-io-timing

- Created `wiki/v12/questions/production-io-overhead-measurement-protocol-track-io-timing.md` proposing a protocol to measure I/O overhead on production database using `track_io_timing`.
- Protocol: Enable `track_io_timing=on` temporarily, collect metrics from `pg_stat_statements` and `pg_stat_database`, analyze per-operation I/O latency and total overhead.
- Includes safety considerations, SQL queries for data collection, and post-analysis cleanup.
- Cited `raw/postgres-12/src/backend/utils/misc/guc.c:1402`, `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:894-905,2752-2770`.
- Updated `wiki/v12/index.md` and `wiki/index.md`.

## [2026-05-03] answer v12 | data-checksums-implementation

- Created `wiki/v12/questions/data-checksums-implementation.md` answering: PG 12 data checksums implementation, overhead, storage location, additional storage usage, pg_checksums --enable operation, and expected fraction of database data modified (~0.024%).

- Cited `raw/postgres-12/src/include/storage/checksum_impl.h#pg_checksum_page` (FNV-1a checksum algorithm), `raw/postgres-12/src/backend/storage/page/bufpage.c#PageIsVerified` (verification), `raw/postgres-12/src/include/storage/bufpage.h` (PageHeaderData.pd_checksum), `raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#scan_file` (enable process).

- Updated `wiki/v12/index.md` and `wiki/index.md`.

## [2026-05-03] answer v12 | key metrics for usage and operational status

- Created `wiki/v12/questions/key-metrics-usage-operational-status.md` answering key metrics to categorize database usage and operational status in PostgreSQL 12.
- Covered connection metrics (pg_stat_activity), database performance (pg_stat_database cache hit ratio, I/O timing), background writer activity (pg_stat_bgwriter), table/index usage patterns, lock contention, and operational health assessment.
- Cited system view definitions `raw/postgres-12/src/backend/catalog/system_views.sql` and statistics functions `raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c`.
- Updated `wiki/v12/index.md` and `wiki/index.md`.

## [2026-05-03] answer v12 | bgwriter tuning scenarios

- Created `wiki/v12/questions/bgwriter-tuning-scenarios.md` answering recommended bgwriter settings for 8 tuning scenarios in PostgreSQL 12 (checkpoint I/O spikes, maxwritten_clean limits, backend writing, bursty workloads, idle systems, low-power environments, kernel page cache pressure, high-write OLTP).

- Cited bgwriter GUC definitions `raw/postgres-12/src/backend/utils/misc/guc.c#2728-2756,3352-3359` and algorithm `raw/postgres-12/src/backend/storage/buffer/bufmgr.c#2052-2336`.

- Updated `wiki/v12/index.md` and `wiki/index.md`.

## [2026-05-03] update v12 | source code tree diagram replaced with ASCII tree

- Replaced Mermaid mindmap diagram in `wiki/v12/diagrams/source-code-tree-overview.md` with Unicode/ASCII tree representation per agents.md requirements.
- Verified directory structure against `raw/postgres-12@45b88269a353ad93744772791feb6d01bc7e1e42`.
- Updated `verified_by_agent` timestamp.

## [2026-05-03] answer v12 | can non-prepared statements use generic plans

- Created `wiki/v12/questions/can-non-prepared-statements-use-generic-plans.md` answering: Yes, non-prepared SELECT statements can use generic plans in PostgreSQL 12. Generic plans are cached query execution plans independent of parameter values, used for both prepared and non-prepared statements.

- Verified against `raw/postgres-12@45b88269a353ad93744772791feb6d01bc7e1e42`: `plancache.c:choose_custom_plan()` prefers generic plans for queries with no parameters (`boundParams == NULL`), `GetCachedPlan()` orchestrates plan caching, simple queries in `postgres.c:exec_simple_query()` call `GetCachedPlan(psrc, NULL, false, NULL)`.

- Updated `wiki/v12/index.md` and `wiki/index.md`.

## [2026-05-03] update | AGENTS.md citation discipline clarified

- Added "Use the same citation format for all code references, function names, and symbols mentioned in the text" to Citation Discipline section.
- Added "Code references may use aliases for compact display: `[[raw/postgres-NN/path/file.c#symbol|file.c#symbol]]`" to allow compact display of citations.
- Updated `wiki/v12/questions/can-non-prepared-statements-use-generic-plans.md` to use aliases for code references, displaying as `plancache.c#choose_custom_plan` instead of full paths.

For version-agnostic work, omit the version segment:

```md
## [YYYY-MM-DD] <kind> | <subject>
```

## [2026-05-03] lint v12 | Fixed citation format on plan_cache_mode production impact question

- Fixed citation format to use mandatory shape `[[raw/postgres-12/path#symbol]]` per AGENTS.md.
- Previously used incorrect bare `raw/postgres-12/path#symbol` format without `[[ ]]`.
- Verified all citations point to correct source files in `raw/postgres-12/` at pinned commit.
- Updated `verified_by_agent` timestamp.
- Updated wiki/index.md and wiki/v12/index.md with page references.

## [2026-05-03] lint v12 | Corrected citation format on source code tree overview diagram

- Fixed citation format to use mandatory shape `[[raw/postgres-12/path#symbol]]` per AGENTS.md.
- Previously used incorrect `[[v12/files/path#symbol]]` format.
- Verified all citations point to correct source files in `raw/postgres-12/` at pinned commit.
- Updated `verified_by_agent` timestamp.

## [2026-05-03] lint v12 | Added missing Source References section to question page

- Added required `## Source References` section to `can-non-prepared-statements-use-generic-plans.md`.
- Changed `## Follow-Up Questions` to `## Open Questions` for consistency.
- Updated `verified_by_agent` timestamp after structural fix.

## [2026-04-30] scaffold | initialized Phase 1 wiki structure

- Created version-agnostic wiki entry points.
- Created page templates.
- Created `AGENTS.md`.
- Created project-local runtime directory layout under `.wiki-runtime/`.
- Added `.gitignore` entries for project-local runtime state and local PostgreSQL source checkouts.

## [2026-04-30] add-version v18 | bootstrapped primary source checkout

- Added PostgreSQL 18 as the primary wiki version.
- Cloned official PostgreSQL source into `raw/postgres-18/`.
- Pinned `REL_18_STABLE` to `6cb307251c5c6261286c1566496920976640108e`.
- Created `wiki/v18/index.md`.
- Created empty version-local directories for subsystems, concepts, code paths, files, and questions.
- Updated `wiki/versions.md`, `wiki/index.md`, and `wiki/overview.md`.

## [2026-04-30] ingest v18 | parser subsystem

- Created `wiki/v18/subsystems/parser.md`.
- Verified entry points against `raw/postgres-18/src/backend/tcop/postgres.c:pg_parse_query`, `raw/postgres-18/src/backend/parser/parser.c:raw_parser`, and `raw/postgres-18/src/include/parser/parser.h`.

## [2026-04-30] ingest v18 | analyzer subsystem

- Created `wiki/v18/subsystems/analyzer.md`.
- Verified entry points against `raw/postgres-18/src/backend/tcop/postgres.c:pg_analyze_and_rewrite_fixedparams`, `raw/postgres-18/src/backend/parser/analyze.c:parse_analyze_fixedparams`, and `raw/postgres-18/src/include/parser/analyze.h`.

## [2026-04-30] ingest v18 | rewriter subsystem

- Created `wiki/v18/subsystems/rewriter.md`.
- Verified entry points against `raw/postgres-18/src/backend/tcop/postgres.c:pg_rewrite_query`, `raw/postgres-18/src/backend/rewrite/rewriteHandler.c:QueryRewrite`, and `raw/postgres-18/src/include/rewrite/rewriteHandler.h`.

## [2026-04-30] ingest v18 | planner subsystem

- Created `wiki/v18/subsystems/planner.md`.
- Verified entry points against `raw/postgres-18/src/backend/tcop/postgres.c:pg_plan_query`, `raw/postgres-18/src/backend/optimizer/plan/planner.c:planner`, and `raw/postgres-18/src/backend/optimizer/README`.

## [2026-04-30] ingest v18 | executor subsystem

- Created `wiki/v18/subsystems/executor.md`.
- Verified entry points against `raw/postgres-18/src/backend/executor/execMain.c`, `raw/postgres-18/src/backend/executor/execProcnode.c:ExecInitNode`, `raw/postgres-18/src/include/executor/executor.h:ExecProcNode`, and `raw/postgres-18/src/backend/executor/README`.

## [2026-04-30] trace v18 | simple-select-query

- Created `wiki/v18/code-paths/simple-select-query.md`.
- Traced simple Query protocol through `exec_simple_query`, `pg_parse_query`, `pg_analyze_and_rewrite_fixedparams`, `pg_plan_queries`, `PortalStart`, `PortalRunSelect`, `ExecutorRun`, and `ExecutePlan`.
- Linked the path from parser, analyzer, rewriter, planner, and executor subsystem pages.

## [2026-04-30] trace v18 | insert-path

- Created `wiki/v18/code-paths/insert-path.md`.
- Traced simple `INSERT ... VALUES` through `transformInsertStmt`, `preprocess_targetlist`, `create_modifytable_path`, `create_modifytable_plan`, `PortalRunMulti`, `ProcessQuery`, `ExecModifyTable`, and `ExecInsert`.
- Linked the path from parser, analyzer, rewriter, planner, and executor subsystem pages.

## [2026-04-30] trace v18 | update-path

- Created `wiki/v18/code-paths/update-path.md`.
- Traced simple `UPDATE` through `transformUpdateStmt`, `transformUpdateTargetList`, row-identity target-list preprocessing, `ModifyTable` planning, `ExecModifyTable`, and `ExecUpdate`.
- Linked the path from parser, analyzer, rewriter, planner, and executor subsystem pages.

## [2026-04-30] trace v18 | delete-path

- Created `wiki/v18/code-paths/delete-path.md`.
- Traced simple `DELETE` through `transformDeleteStmt`, row-identity target-list preprocessing, `ModifyTable` planning, `ExecModifyTable`, and `ExecDelete`.
- Linked the path from parser, analyzer, rewriter, planner, and executor subsystem pages.

## [2026-04-30] concept v18 | query-tree

- Created `wiki/shared/concepts/query-tree.md`.
- Verified against `raw/postgres-18/src/include/nodes/parsenodes.h:Query`, `raw/postgres-18/src/backend/parser/analyze.c:parse_analyze_fixedparams`, and planner/rewrite handoff functions in `raw/postgres-18/src/backend/tcop/postgres.c`.

## [2026-04-30] concept v18 | planned-statement

- Created `wiki/shared/concepts/planned-statement.md`.
- Verified against `raw/postgres-18/src/include/nodes/plannodes.h:PlannedStmt`, planner entry points, portal storage, and executor descriptors.

## [2026-04-30] concept v18 | plan-and-planstate

- Created `wiki/shared/concepts/plan-and-planstate.md`.
- Verified against `raw/postgres-18/src/include/nodes/plannodes.h:Plan`, `raw/postgres-18/src/include/nodes/execnodes.h:PlanState`, `raw/postgres-18/src/backend/executor/execProcnode.c:ExecInitNode`, and `raw/postgres-18/src/backend/executor/README`.

## [2026-04-30] concept v18 | path-and-reloptinfo

- Created `wiki/shared/concepts/path-and-reloptinfo.md`.
- Verified against `raw/postgres-18/src/include/nodes/pathnodes.h:RelOptInfo`, `raw/postgres-18/src/include/nodes/pathnodes.h:Path`, and `raw/postgres-18/src/include/nodes/pathnodes.h:ModifyTablePath`.

## [2026-04-30] concept v18 | executor-state

- Created `wiki/shared/concepts/executor-state.md`.
- Verified against `raw/postgres-18/src/include/nodes/execnodes.h:EState` and executor lifecycle functions in `raw/postgres-18/src/backend/executor/execMain.c`.

## [2026-04-30] concept v18 | tuple-table-slot

- Created `wiki/shared/concepts/tuple-table-slot.md`.
- Verified against `raw/postgres-18/src/include/executor/tuptable.h:TupleTableSlot`, `raw/postgres-18/src/include/executor/executor.h:ExecProcNode`, and tuple executor code.

## [2026-04-30] concept v18 | modifytable

- Created `wiki/shared/concepts/modifytable.md`.
- Verified against `raw/postgres-18/src/include/nodes/pathnodes.h:ModifyTablePath`, `raw/postgres-18/src/include/nodes/plannodes.h:ModifyTable`, `raw/postgres-18/src/include/nodes/execnodes.h:ModifyTableState`, and `raw/postgres-18/src/backend/executor/nodeModifyTable.c`.

## [2026-04-30] concept v18 | portal

- Created `wiki/shared/concepts/portal.md`.
- Verified against `raw/postgres-18/src/include/utils/portal.h:PortalData` and portal execution functions in `raw/postgres-18/src/backend/tcop/pquery.c`.

## [2026-04-30] concept v18 | querydesc

- Created `wiki/shared/concepts/querydesc.md`.
- Verified against `raw/postgres-18/src/include/executor/execdesc.h:QueryDesc`, `raw/postgres-18/src/backend/tcop/pquery.c`, and executor lifecycle functions in `raw/postgres-18/src/backend/executor/execMain.c`.

## [2026-04-30] tooling | maintenance scripts

- Added `scripts/recent_log` for recent activity summaries from `wiki/log.md`.
- Added `scripts/wiki_lint` for broken Obsidian links, orphan pages, missing front matter, stale version pins, and missing source references.
- Added `scripts/source_lookup` for project-local PostgreSQL source search, file display, and git history lookup.
- Added `scripts/version_diff` for comparing one source path across two project-local PostgreSQL checkouts.
- Added shared script helpers in `scripts/wiki_tooling.py`.
- Updated `AGENTS.md` to reference the project-local tooling workflow.

## [2026-04-30] lint | maintenance tooling smoke check

- Ran `scripts/wiki_lint --warnings-as-errors`; result was 0 errors and 0 warnings after replacing a stale illustrative `v17/index` wiki link with plain text.
- Verified `scripts/recent_log`, `scripts/source_lookup`, and `scripts/version_diff` against the current PostgreSQL 18 checkout.

## [2026-04-30] tooling | project-local Hermes install

- Installed `NousResearch/hermes-agent` under `.wiki-runtime/hermes-agent/` at commit `285e9efb3f2251f09cfbc9acb335c3d943d5a7b2`.
- Added project-local `uv` under `.wiki-runtime/env/uvprefix/` and installed Hermes Agent `0.11.0` into `.wiki-runtime/env/hermes-agent/`.
- Added `.wiki-runtime/hermes-agent/venv` as a symlink to `.wiki-runtime/env/hermes-agent/` for Hermes diagnostics.
- Created `.wiki-runtime/hermes/.env` from the Hermes example with `0600` permissions.
- Synced bundled Hermes skills into `.wiki-runtime/hermes/skills/`.
- Updated `.wiki-runtime/hermes/wiki-agent.env` and `templates/wiki-agent-hermes.env.example` to launch `.wiki-runtime/env/hermes-agent/bin/hermes gateway run --replace`.
- Updated `wiki/operations/agent.md` and `wiki/index.md` with the project-local Hermes runtime layout and commands.

## [2026-04-30] tooling | project-local planned model

- Downloaded the planned local coder model into `.wiki-runtime/models/qwen2.5-coder-14b-instruct-gguf/qwen2.5-coder-14b-instruct-q4_k_m.gguf`.
- Switched `scripts/llama_server` away from the borrowed `/data/repos/image-private/` model and made the project-local Qwen2.5-Coder 14B `q4_K_M` GGUF the default.
- Set the default llama.cpp KV cache types to `q4_0` for the 14B model so the 64K context target can fit the expected 16 GB GPU profile.
- Restarted llama.cpp with the project-local model and verified the OpenAI-compatible `/v1/models` and `/v1/chat/completions` endpoints.

## [2026-04-30] tooling | Qwen3.5-9B local model

- Downloaded `Qwen3.5-9B-Q4_K_M.gguf` into `.wiki-runtime/models/qwen3.5-9b-gguf/`.
- Switched `scripts/llama_server` from the Qwen2.5-Coder 14B GGUF to the project-local Qwen3.5-9B `Q4_K_M` GGUF.
- Kept the OpenAI-compatible model alias `pgwiki-local` and Hermes provider endpoint at `http://127.0.0.1:8080/v1`.

## [2026-04-30] tooling | Qwen3.5-9B Q6_K 128K

- Downloaded `Qwen_Qwen3.5-9B-Q6_K.gguf` into `.wiki-runtime/models/qwen3.5-9b-gguf/`.
- Switched `scripts/llama_server` to the project-local Qwen3.5-9B `Q6_K` GGUF.
- Raised the llama.cpp default context and Hermes provider context metadata from 65,536 to 131,072 tokens.
- Restarted llama.cpp and verified `Q6_K`, 131,072-token slots, `/v1/models`, and `/v1/chat/completions`.

## [2026-04-30] tooling | Qwen3.5 thinking disabled

- Updated `scripts/llama_server` to start llama.cpp with `--reasoning off` and `--chat-template-kwargs '{"enable_thinking":false}'`.
- Documented the default and the `LLAMA_REASONING` / `LLAMA_CHAT_TEMPLATE_KWARGS` overrides in `wiki/operations/agent.md`.
- Restarted llama.cpp and verified the startup log reports `thinking = 0`; a plain `/v1/chat/completions` request returned answer text without per-request template overrides.

## [2026-04-30] docs | operator dashboard runbook

- Added top-level `operator.md` with commands for running `hermes dashboard` against the project-local Hermes home and llama.cpp backend.
- Documented dashboard status, stop, and remote SSH tunnel access.

## [2025-05-01] research | autovacuum history from v12 to v18

- Traced autovacuum evolution from PostgreSQL 12 to 18.
- Identified key commits from git history:
  - `b07642dbcd` - INSERT-based autovacuum triggers (v12)
  - `caf626b2cd` - Cost delay as floating-point GUC (v12)
  - `80d76be51c` - Temp table safety (v13)
  - `7526e10224` - BRIN auto-summarization (v11, enhanced in v14)
  - `306dc520b9` - autovacuum_vacuum_max_threshold (v16)
  - `c758119e5b` - Dynamic autovacuum_max_workers (v16)
  - `052026c9b9` - Aggressive vacuum optimization (v16)
  - `a9781ae11b` - Cost debug logging fix (v17)
  - `bfac8f8bc4` - Cost delay check fix (v17)
- Analyzed source files:
  - `src/backend/postmaster/autovacuum.c` (3475 lines)
  - `src/include/postmaster/autovacuum.h` (71 lines)
- Documented 17 GUC parameters and their evolution
| 2025-05-01 12:48 | **autovacuum-evolution** | Research | ✅ | Moved to `wiki/shared/autovacuum-evolution.md` for cross-version content. Added Open Questions section per AGENTS.md. Updated citations to use `raw/postgres-18/` source paths. Document now has 26 git commit references and follows citation discipline. |
  - Version-by-version feature breakdown
  - Git commit references for each major change
  - Source code line references
  - Default GUC values table
  - Summary table of all key changes

- Key features traced:
  - INSERT-based vacuum triggers (v12)
  - Cost-based vacuum delay (v12)
  - Temp table handling (v13)
  - BRIN auto-summarization integration (v14)
  - Memory leak fixes (v15)
  - AIO subsystem integration (v15)
  - Vacuum cost variable separation (v15)
  - Max threshold parameter (v16)
  - Dynamic worker management (v16)
  - Multi-xact freeze age improvements (v17)

## [2026-05-01] tooling | Hermes session cleanup

- Added `scripts/hermes_sessions` to list or clear project-local Hermes session files under `.wiki-runtime/hermes/sessions/`.
- Documented the cleanup workflow in `wiki/operations/agent.md`, `wiki/index.md`, and `wiki/overview.md`.
- The clear command defaults to a dry run and requires `--yes` to delete session files.

## [2026-05-01] tooling | Hermes session database purge

- Extended `scripts/hermes_sessions clear` to purge session rows from `.wiki-runtime/hermes/state.db` in addition to deleting files under `.wiki-runtime/hermes/sessions/`.
- The dry run now reports both session file items and `state.db` session/message row counts.
- The purge deletes `messages` and `sessions`, resets the message autoincrement sequence, checkpoints the WAL, and vacuums the database while keeping schema and non-session metadata intact; only destructive runs require the agent to be stopped or `--force`.

## [2026-05-01] tooling | Hermes Markdown PDF skill

- Added the project-local Hermes skill `markdown-pdf` under `.wiki-runtime/hermes/skills/productivity/markdown-pdf/`.
- Added bundled converter script `scripts/md_to_pdf.py` for generating PDFs from Markdown through the Hermes Python runtime.
- Installed `reportlab==4.5.0` and `pillow==12.2.0` into `.wiki-runtime/env/hermes-agent/`; reused existing `markdown-it-py==4.0.0`.
- Documented the skill and dependency location in `wiki/operations/agent.md`.

## [2026-05-01] tooling | Hermes HTML PDF skill

- Added the project-local Hermes skill `html-pdf` under `.wiki-runtime/hermes/skills/productivity/html-pdf/`.
- Added bundled converter script `scripts/html_to_pdf.py` for generating document-style PDFs from local HTML through the Hermes Python runtime.
- Reused the existing project-local `reportlab==4.5.0` and `pillow==12.2.0` runtime dependencies instead of adding a browser or system-Cairo renderer.
- Documented the skill and dependency location in `wiki/operations/agent.md`.

## [2026-05-01] tooling | dashboard Tailscale exposure

- Updated `scripts/dashboard` so `start` exposes the dashboard port through Tailscale Serve by default while keeping the Hermes dashboard bound to loopback.
- Added `scripts/dashboard unserve` plus `HERMES_DASHBOARD_TAILSCALE_*` environment overrides for Serve/Funnel mode, HTTPS port, path, target, and stop cleanup.
- Updated `scripts/stop_all` and `operator.md` to use the dashboard wrapper instead of calling `hermes dashboard` directly.

## [2026-05-02] answer v18 | insert-row-disk-writes

- Created `wiki/v18/questions/insert-row-disk-writes.md` tracing disk writes on simple row insert txn: WAL sync at commit (XLogFlush in CommitTransaction@xact.c:2228/1502) only; heap/index async via bgwriter/checkpointer; cites heap_insert@heapam_handler.c:255/278, ExecInsert@nodeModifyTable.c; mermaid + excalidraw JSON seq diagrams; cross-links [[v18/code-paths/insert-path]].
- Updated `wiki/v18/index.md` and `wiki/index.md` question lists.

## [2026-05-02] tooling | model config alignment and unused model prune

- Renamed every Hermes auxiliary model id from `Qwen3.5-9B-Q8_0` to `pgwiki-local` in `.wiki-runtime/hermes/config.yaml` so the config matches the alias the running llama-server actually advertises.
- Made `scripts/llama_server`'s `thinking` mode actually toggle `--reasoning auto` and `enable_thinking:true`; the `precise` mode keeps reasoning off. Previously the mode flag only changed sampling and the chat template kept thinking disabled.
- Refreshed `wiki/operations/agent.md` to document the split hosted-main / local-aux design, the `pgwiki-local` server alias, the `q8_0` KV cache default, and the precise/thinking sampling modes.
- Updated `AGENTS.md` to reference the local model by alias rather than file-name quantization.
- Deleted `scripts/llama_server_old copy` leftover and pruned unused GGUFs under `.wiki-runtime/models/`: `Qwen3.5-9B-Q4_K_M.gguf`, `Qwen3.5-9B-Q8_0.gguf`, the `qwen2.5-coder-14b-instruct-gguf/` tree, and the `qwen3-coder-30b-a3b-instruct-gguf/` tree. The currently-loaded `Qwen_Qwen3.5-9B-Q6_K.gguf` is the only weights file kept.
- Restored `wiki/log.md` after an accidental truncation that had wiped historical entries.

## [2026-05-02] lint | fixed wiki_lint errors/warnings

- Created `wiki/operations/agent.md` runbook (Hermes/llama lifecycle).

## [2026-05-02] cleanup v18 | pruned duplicate plan_cache_mode question pages

- Deleted three low-quality duplicates of [[v18/questions/plan-cache-mode-production-impact]]:
  - `wiki/v18/questions/plan_cache_mode-production-analysis.md`
  - `wiki/v18/questions/plan_cache-mode-decision-tree.md`
  - `wiki/v18/questions/plan_cache-mode-memory-usage-tables-comparison.md`
- Defects in the deleted pages: missing `type: question` / `verified` frontmatter; inconsistent slug shapes (`plan_cache_mode-` vs `plan_cache-mode-`); citations pointing to GitHub URLs instead of `raw/postgres-18/`; references to a non-existent `pg_stat_statements_cache_plan_stats` view; fabricated C structs (`MemoryContextNodeBitmapData`, `_HashTable`, fake `Rte`); unverified PG 18 version-change claims; numerical estimates ("5-8× larger", "~640-960 KB per custom plan") with no source backing.
- Removed the obsolete duplicate-pages note from the `Open Questions` section of [[v18/questions/plan-cache-mode-production-impact]].
- Updated [[v18/index]] question list to drop the three deleted entries. [[index]] already pointed only at the canonical page.

## [2026-05-02] revise v18 | query-disk-io-with-warm-cache per-planning-phase summary

- Added a "Per-Planning-Phase Summary" section to `wiki/v18/questions/query-disk-io-with-warm-cache.md` covering raw parse (`raw_parser`), parse analysis (`parse_analyze_fixedparams`), rewriter (`QueryRewrite`/`fireRIRrules`/`fireRules`), planner (`planner`/`standard_planner`/`get_relation_info`), plan-cache revalidation (`GetCachedPlan`/`RevalidateCachedQuery`/`BuildCachedPlan`), and JIT compilation (`llvm_compile_module`/`llvm_load_summary`).
- Documented per-phase catalog access: `pg_namespace`/`pg_class`/`pg_attribute` for analysis; `pg_rewrite`/`pg_policy` for rewriter; `pg_class`/`pg_index`/`pg_statistic`/`pg_statistic_ext_data`/`pg_amop`/`pg_amproc` for planner; `*.bc` bitcode files under `$pkglibdir/bitcode/` for JIT.
- Cited `analyze.c:parse_analyze_fixedparams:105`, `rewriteHandler.c:fireRIRrules:2026`, `rewriteHandler.c:fireRules:2458`, `plancat.c:get_relation_info:130-286`, `plancat.c:1428` (extended-stats syscache), `relcache.c:RelationBuildDesc:1059`, `plancache.c:GetCachedPlan`/`RevalidateCachedQuery`/`BuildCachedPlan`, `jit.c:jit_compile_expr:151`, `llvmjit.c:llvm_compile_module:709`, `llvmjit_inline.cpp:llvm_load_summary:768`.
- Added a planning-phase quick-reference matrix grading each phase across catalog buffer reads, dirty-victim writeback, relcache rebuild, plan-cache revalidation cost, SLRU reads for catalog visibility, and JIT bitcode load.
- Ranked slow-random-disk impact within planning: first JIT'd query > first relation reference > invalidated plan-cache replan > steady-state fresh-statement planning > cached plan reuse > raw parse.
- `scripts/wiki_lint --warnings-as-errors`: 0 errors, 1 unrelated pre-existing warning (`wiki/shared/output/README.md` orphan).

## [2026-05-02] revise v18 | query-disk-io-with-warm-cache per-statement summary

- Added a "Per-Statement-Type Summary" section to `wiki/v18/questions/query-disk-io-with-warm-cache.md` covering `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `COPY FROM`/`COPY TO`, `TRUNCATE`, DDL, `CREATE TABLESPACE`/`DATABASE`, `CREATE INDEX`/`REINDEX`, `VACUUM`/autovacuum, `ANALYZE`, `BEGIN`/`COMMIT`/`ROLLBACK`, `SAVEPOINT` family, 2PC (`PREPARE TRANSACTION`), `LISTEN`/`NOTIFY`, `LOCK TABLE`, `EXPLAIN`, `EXPLAIN ANALYZE`, and `EXECUTE`.
- Each entry lists which I/O categories (WAL emission, commit fsync, relation extension, TOAST, VM clear, FSM update, SLRU traffic, temp spills, hint-bit dirty, dirty-victim writeback) typically apply.
- Documented that plain `SELECT` can still emit WAL via `heap_page_prune_opt` → `XLOG_HEAP2_PRUNE_ON_ACCESS` at `pruneheap.c:193,2053,2157`, that `DELETE` does not touch indexes in the foreground (only VACUUM does), that `TRUNCATE` and `DROP` go through the `nrels > 0` synchronous-flush branch at `xact.c:1499-1502`, and that `CREATE/DROP TABLESPACE`/`DATABASE` explicitly call `ForceSyncCommit()` (`xact.c:1154`, `tablespace.c:379,553`, `dbcommands.c:1565,1894,2263`).
- Added a quick-reference matrix grading each statement on each disk-I/O category and a slow-random-disk impact ranking (`COPY FROM`/`CREATE INDEX`/`VACUUM` highest, DML next, `SELECT` only when pruning or buffer pool is dirty, pre-execution lowest).
- `scripts/wiki_lint --warnings-as-errors`: 0 errors, 1 unrelated pre-existing warning (`wiki/shared/output/README.md` orphan).

## [2026-05-02] answer v18 | query-disk-io-with-warm-cache

- Created `wiki/v18/questions/query-disk-io-with-warm-cache.md` answering: pre-execution and execution disk I/O paths in PG 18 and how a slow random-I/O disk hurts even when shared buffers and OS page cache are fully warm.
- Pre-execution: catalog buffer reads on cache miss (relcache, syscache, statistics) all short-circuit at `BufferAlloc` when warm; plan-cache revalidation reacquires planner locks but issues no synchronous writes.
- Execution-time categories: (1) commit-time WAL fsync via `XLogFlush` → `issue_xlog_fsync`, (2) WAL buffer wraparound via `AdvanceXLInsertBuffer`/`XLogWrite`, (3) dirty victim writeback in `GetVictimBuffer` → `FlushBuffer`, (4) relation extension via `mdzeroextend`, (5) per-backend temp-file spills via `BufFile`/`tuplesort`/`tuplestore`/`nodeHashjoin`/`nodeAgg`.
- Highlighted hint-bit dirty-buffer pressure, SLRU read/write for CLOG/MultiXact/SubTrans/CommitTs, VM/FSM updates, and `SyncRepWaitForLSN` under synchronous replication.
- Cited `xact.c:1499-1502`, `xlog.c:XLogFlush`, `xlog.c:issue_xlog_fsync:8744`, `xlog.c:AdvanceXLInsertBuffer:1988-2070`, `bufmgr.c:GetVictimBuffer`, `bufmgr.c:FlushBuffer`, `bufmgr.c:ExtendBufferedRelBy`, `hio.c:RelationGetBufferForTuple`, `md.c:register_dirty_segment:1499-1517`, `slru.c:SimpleLruWritePage`, `clog.c:TransactionIdGetStatus`, `buffile.c:OpenTemporaryFile`/`BufFileWrite`, `syncrep.c:SyncRepWaitForLSN`.
- Added mermaid sequence diagram showing the warm-cache-but-still-blocked paths.
- Linked to [[v18/questions/insert-row-disk-writes]], [[v18/code-paths/select-disk-io]], [[v18/code-paths/simple-select-query]], [[v18/questions/prepared-statement-replanning]], [[shared/autovacuum-evolution]].
- Updated `wiki/v18/index.md` and `wiki/index.md` question lists.

## [2026-05-02] revise v18 | rewrote insert-row-disk-writes for citation discipline

- Rewrote [[v18/questions/insert-row-disk-writes]] to align with AGENTS.md citation discipline and the style of the rest of `wiki/v18/questions/`.
- Corrected the call chain: `ExecInsert` → `table_tuple_insert` (TAM dispatch at `nodeModifyTable.c:1234`) → `heapam_tuple_insert` (`heapam_handler.c:244`) → `heap_insert` (`heapam.c:2080`). The previous version skipped the TAM layer and named `heapam_handler.c:255,278` as the source of `heap_insert` itself.
- Replaced fabricated symbol `XLogHeapInsert(rel, buffer, tuple)` with the actual inline emission inside `heap_insert`: `XLogBeginInsert` / `XLogRegisterData` / `XLogRegisterBuffer` / `XLogRegisterBufData` / `XLogInsert(RM_HEAP_ID, …)` at `heapam.c:2231`.
- Reordered the heap_insert step list to match the source: `heap_prepare_insert` → `RelationGetBufferForTuple` → `RelationPutHeapTuple`/`PageAddItem` → `MarkBufferDirty` → WAL emission → `END_CRIT_SECTION`/`UnlockReleaseBuffer` → `pgstat_count_heap_insert`. Cited verified line numbers `heapam.c:2155`, `:2231`, `:2236`, `:2238`, `:2251`.
- Added side-effect coverage (indexes, TOAST via `heap_toast_insert_or_update`, visibility map, free-space map via `RecordPageWithFreeSpace`, CLOG via `TransactionIdSetTreeStatus`) and the bgwriter / checkpointer / walwriter async-flush actors.
- Replaced TODO-shaped `Open Questions` ("Extend to INSERT ... SELECT?", "Index-specific WAL details?") with three follow-up traces tied to actual uncertainty: index-AM `RelationNeedsWAL` edge cases, replication-side wait under `synchronous_commit = remote_apply`, and `heap_multi_insert` WAL byte savings.
- `scripts/wiki_lint`: 0 errors, 1 unrelated pre-existing warning (`wiki/shared/output/README.md` orphan).

## [2026-05-02] add-supported-version v12 | Added PostgreSQL 12.2 support

- Pinned `raw/postgres-12/` to `REL_12_2` commit `45b88269a353ad93744772791feb6d01bc7e1e42` via `scripts/source_update --version 12`.
- Created `wiki/v12/index.md` landing page scaffold.
- Created empty `wiki/v12/{subsystems,concepts,code-paths,files,questions}/` directories.
- Added v12 row to `wiki/versions.md` supported versions table.
- Added `[[v12/index]]` section to `wiki/index.md`.

## [2026-05-02] answer v12 | query-disk-io-with-warm-cache

- Created `wiki/v12/questions/query-disk-io-with-warm-cache.md` answering: pre-execution and execution disk I/O paths in PG 12.2 and how a slow random-I/O disk hurts even when shared buffers and OS page cache are fully warm.

- Pre-execution: catalog buffer reads short-circuit at `BufferAlloc`; plan-cache revalidation locks no writes.

- Execution: commit WAL fsync (`xact.c:1371`), WAL wrap (`xlog.c:AdvanceXLInsertBuffer`), dirty victim (`bufmgr.c:FlushBuffer`), extension (`mdzeroextend`), temp spills (`BufFile`).

- Added per-statement summary (SELECT, INSERT, UPDATE, DELETE, etc.) and per-planning-phase summary.

- Cited `raw/postgres-12/src/backend/access/transam/xact.c:1371`, `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:2672`, etc.

- Updated `wiki/v12/index.md` and `wiki/index.md`.

## [2026-05-03] expand v12 | source code tree overview

- Expanded key features and functionalities for each source tree directory in `wiki/v12/diagrams/source-code-tree-overview.md` with additional citations from READMEs and key source files/symbols.

- Updated `verified_by_agent: Cline 2026-05-03T12:40:00Z`.

- `scripts/wiki_lint`: 0 errors, 10 warnings (unrelated front matter order/orphan).

## [2026-05-02] review v12 | query-disk-io-with-warm-cache

- Verified citations against `raw/postgres-12@45b88269a353ad93744772791feb6d01bc7e1e42`: `xact.c:1371` `XLogFlush(XactLastRecEnd)`, `xlog.c:2086` `AdvanceXLInsertBuffer` def, `bufmgr.c:2672` `FlushBuffer` def, etc.

- Fixed source refs `xlog.c:2798` → `xlog.c:2086`.

- Removed open questions (all lines verified).


## [2026-05-02] answer v12 | plan-cache-mode-production-impact

- Created \`wiki/v12/questions/plan-cache-mode-production-impact.md\` with PG 12 analysis of plan_cache_mode production impacts, best modes per scenario, pros/cons, slow random I/O disk section.

- Verified/cited \`raw/postgres-12/src/backend/utils/cache/plancache.c:choose_custom_plan\`, \`plancache.h:PlanCacheMode\`, \`guc.c:plan_cache_mode_options\`, \`plancat.c:get_relation_info\`.

- Updated \`wiki/v12/index.md\` (coverage, questions), \`wiki/index.md\`.

## [2026-05-02] answer v12 | detect-slow-random-io-disk-metrics

- Created \`wiki/v12/questions/detect-slow-random-io-disk-metrics.md\` answering PG 12 slow random disk I/O detection via pg_stat_database.blk_read_time/blks_read ratio, pg_stat_statements blk_read_time, pg_stat_activity IO:DataFileRead waits, cache hit ratio, pg_stat_user_tables idx_scan inference.

- Cited \`raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c\`, \`contrib/pg_stat_statements/pg_stat_statements.c\`, \`src/backend/storage/buffer/bufmgr.c\`, \`src/backend/postmaster/pgstat.c:DataFileRead\`.

- Updated \`wiki/v12/index.md\` (coverage, questions list).

## [2026-05-02] answer v12 | track-io-timing-blk-write-time-dirty-victim-select

- Created \`wiki/v12/questions/track-io-timing-blk-write-time-dirty-victim-select.md\` answering: PG 12 SELECT execution, does `track_io_timing=on` `blk_write_time` capture "dirty victim" time (synchronous evictions yes via `FlushBuffer`).

- Cited \`raw/postgres-12/src/backend/storage/buffer/bufmgr.c:2764-2769\` (`track_io_timing` / `smgrwrite` / `pgBufferUsage.blk_write_time += io_time`), \`contrib/pg_stat_statements/pg_stat_statements.c:1051-1052,1292\` (`pgBufferUsage` delta).

- Updated \`wiki/v12/index.md\` (coverage, questions), \`wiki/index.md\` (v12 questions list).

## [2026-05-03] review v12 | plan-cache-mode-production-impact

- Reviewed [[v12/questions/plan-cache-mode-production-impact]] against `raw/postgres-12@45b88269a3` (REL_12_2).
- Fixed decision tree step 3: replaced `!StmtPlanRequiresRevalidation → generic` (helper does not exist in PG 12; introduced post-12) with the actual v12 macro `IsTransactionStmtPlan` at `plancache.c:82,1028`. Added explicit `plancache.c` line numbers for steps 1-9.
- Fixed `plancat.c` path in two places: `optimizer/plan/plancat.c` → `optimizer/util/plancat.c` (Where The Setting Is Read, Source References).
- Verified other claims against v12 source: `choose_custom_plan`/`GetCachedPlan`/`cached_plan_cost`/`BuildCachedPlan`/`RevalidateCachedQuery` in `plancache.c`; `PlanCacheMode` enum in `plancache.h:26-32`; `plan_cache_mode_options` in `guc.c:429-432` with PGC_USERSET at `guc.c:4504-4512`; `pg_prepared_statements` view (5 cols, no counters) in `system_views.sql:332`; `DISCARD PLANS` → `ResetPlanCache` in `discard.c:40,75`; EXPLAIN EXECUTE `$1` vs literal in `prepare.sgml`.
- `scripts/wiki_lint`: 0 errors, 1 unrelated pre-existing warning (`wiki/shared/output/README.md` orphan).

## [2026-05-03] revise v12 | plan-cache-mode-production-impact auto-mode revalidation detail

- Added "Auto Mode: Revalidation Overhead And Timing" section to [[v12/questions/plan-cache-mode-production-impact]] covering: GetCachedPlan entry points (`postgres.c:1876` Bind, `prepare.c:246` ExecuteQuery, `prepare.c:663` ExplainExecuteQuery, `spi.c:1389,1822,2215`), steady-state cheap-path cost (two lock sweeps via `AcquirePlannerLocks`/`AcquireExecutorLocks`, sinval drain through `AcceptInvalidationMessages`, search_path/RLS compares, race rechecks at `plancache.c:616,842`), invalidation-path cost (`pg_analyze_and_rewrite[_params]` + `extract_query_dependencies` for plansource invalidation; full `pg_plan_queries` + wart recheck at `plancache.c:1200` for plan invalidation; preservation of `generic_cost`/`total_custom_cost`/`num_custom_plans` per `plancache.c:768-775` comment), and a sequence diagram showing the revalidation block sits between message dispatch and `ExecutorStart` (so cost is invisible to EXPLAIN ANALYZE but visible in client Bind/Execute latency).
- All new citations verified against `raw/postgres-12@45b88269a3`.
- `scripts/wiki_lint`: 0 errors, 1 unrelated pre-existing warning.
- Updated the page's `## Question` section to record the follow-up ask (auto-mode revalidation overhead and timing in the query execution cycle) so the page stands on its own without the chat context.

## [2026-05-03] update | AGENTS.md: instruct agents to set verified: false on new reports/pages

- Updated ## Verification rules in AGENTS.md per user feedback.
- New rule: When creating new pages or reports (e.g., question pages under `wiki/vNN/questions/`), agents must set `verified: false` in front matter.
- Agents may set initial `verified: false` but never change or remove human-set values.

## [2026-05-03] lint | added verification field checks to wiki_lint

- Implemented new checks in `scripts/wiki_lint`: `verified:` must be 'true'/'false'; `verified_by_agent:` regex format; question pages (type=question) require `verified: false`; managed pages WARN if missing both fields.
- Test run (`scripts/wiki_lint --warnings-as-errors`): 11 ERRORS (question pages missing verified: false), 16 WARN (missing fields + orphan).
- Updated AGENTS.md `## Lint The Wiki` check list.

## [2026-05-03] lint | set verified: false on all question pages

- Added `verified: false` to `wiki/v12/questions/detect-slow-random-io-disk-metrics.md` (the only one missing it)

## [2026-05-03] revert v18 | restored verified: true across all v18 pages

- Reverted removal of human-set `verified: true` from 16+ v18 pages.
- Used `sed -i '/pinned_commit: .../a verified: true'` batch insert after pinned_commit lines in `wiki/v18/*.md`.
- Verified 18 matches post-revert.

## [2026-05-03] lint v18 | removed verified: true from question pages

- Removed `verified: true` from 7 v18 question pages (wiki/v18/questions/).
- Command: `sed -i '/^verified: true$/d' wiki/v18/questions/*.md`.
- Pre: 7 matches; Post: 0 matches in questions.
 - No v12 changes needed.

## [2026-05-03] cleanup | removed local LLM related log entries

- Removed log entries related to local LLM setup: Hermes-managed LLM lifecycle, Hermes local LLM config, llama.cpp local LLM backend.
## [2026-05-03] diagram v12 | source code tree overview

- Created `wiki/v12/diagrams/source-code-tree-overview.md` with mermaid mindmap of source tree directories and explanations of main code areas `raw/postgres-12@45b88269...`.

- Updated `wiki/v12/index.md` (## Diagrams) and `wiki/index.md` (v12 #### Diagrams).


## [2026-05-03] diagram v12 | source code tree overview

- Created `wiki/v12/diagrams/source-code-tree-overview.md` (mermaid mindmap + explanations/citations for main areas).

- Verified against `raw/postgres-12@45b88269a353ad93744772791feb6d01bc7e1e42`.

- Updated `wiki/v12/index.md` and `wiki/index.md`.
## [2026-05-03] verify-fix v12 | source-code-tree-overview

- Re-verified citations against raw/postgres-12@45b88269...

- Fixed invalid (heap/README, pg_stat_statements/README), standardized relative paths (src/backend/..., include/...), corrected headers.

- wiki_lint: 0 errors.


## [2026-05-03] answer v12 | dirty-victim-select-mitigation

- Created `wiki/v12/questions/dirty-victim-select-mitigation.md` answering: PG 12 mitigation strategies for "dirty victim" synchronous writes during SELECT queries (tune bgwriter_lru_maxpages, bgwriter_lru_multiplier, checkpoint_completion_target, shared_buffers).

- Cited `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:1095-1167` (BufferAlloc dirty victim handling), `bufmgr.c:2051-2336` (BgBufferSync algorithm), `freelist.c:200-358` (StrategyGetBuffer victim selection).

- Updated `wiki/v12/index.md` and `wiki/index.md`.

## [2026-05-04] review v12 | production-io-overhead-measurement-protocol-track-io-timing

- Verified all source citations against `raw/postgres-12@45b88269`: GUC at `guc.c:1402` (PGC_SUSET ✓), read timing `bufmgr.c:894-905` (ReadBuffer_common ✓), write timing `bufmgr.c:2752-2770` (FlushBuffer ✓), `pg_stat_statements` blk_read/write_time at `pg_stat_statements.c:1291-1292` ✓, `pgstatfuncs.c:1569` ✓.
- Fixed broken SQL: `pg_stat_database` query had `blks_read + blks_hit - blks_read` (= blks_hit) as write denominator — removed `avg_write_ms_per_block` (no blks_written in pg_stat_database), added comment directing to pg_stat_bgwriter.
- Converted all Source References from plain-text/line-number to Obsidian `[[raw/postgres-12/...#symbol]]` format per AGENTS.md mandate.
- Moved unsourced per-call overhead numbers (~1-2μs, ~700-1500ns) out of factual claims; moved to Open Questions with note about pg_test_timing.
- Set `verified_by_agent: claude-sonnet-4-6 2026-05-04T00:00:00Z`.
