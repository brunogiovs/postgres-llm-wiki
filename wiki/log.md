# Wiki Log

Append one entry after every scaffold change, version lifecycle event, ingest, trace, lint pass, or filed answer.

## [2026-05-05] question v12 | track_io_timing production measurement procedure

- Filed [[v12/questions/measure-io-overhead-with-track-io-timing]] covering host clock-source qualification with `pg_test_timing`, cluster-wide enable via `ALTER SYSTEM` + `pg_reload_conf()`, delta sampling from `pg_stat_database` and `pg_stat_statements`, and per-plan drill-down via `EXPLAIN (ANALYZE, BUFFERS)`.
- GUC scope verified `PGC_SUSET` against `raw/postgres-12/src/backend/utils/misc/guc.c` and `src/include/utils/guc.h`; instrumentation sites verified in `src/backend/storage/buffer/bufmgr.c` and `src/backend/commands/explain.c`. Counter exposure verified in `src/backend/utils/adt/pgstatfuncs.c`, `src/backend/catalog/system_views.sql`, and `contrib/pg_stat_statements/pg_stat_statements.c`.
- Updated `wiki/index.md` and `wiki/v12/index.md` to link the new question.
- Removed stale `## Diagrams` / `#### Diagrams` sections from `wiki/v12/index.md` and `wiki/index.md`; the linked files were deleted in the prior diagram cleanup commit but the links were left behind.

## [2026-05-05] maintenance | removed all diagrams and cleaned up log.md

- Removed all diagram files and directories (`wiki/diagrams/`, `wiki/v12/diagrams/`)
- Cleaned up `wiki/log.md` by removing malformed entries and obsolete diagram-related log entries

Use this prefix shape:

```md
## [YYYY-MM-DD] <kind> v<NN> | <subject>
```
