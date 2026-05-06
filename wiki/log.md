# Wiki Log

Append one entry after every scaffold change, version lifecycle event, ingest, trace, lint pass, or filed answer.

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
