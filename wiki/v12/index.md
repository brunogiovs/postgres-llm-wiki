# PostgreSQL 12.2

## Source Pin

- Branch: `REL_12_STABLE`
- Commit: `45b88269a353ad93744772791feb6d01bc7e1e42`
- Status: `legacy`
- Source path: `raw/postgres-12/`
- Added: 2026-05-02

## Coverage

Questions filed:

- [[v12/questions/bgwriter-tuning-recommendations|Bgwriter tuning recommendations (unverified)]] (four bgwriter GUCs with defaults/ranges/reload semantics, source-grounded direction-of-change matrix per scenario, and verified `pg_stat_bgwriter` counter wiring for iterative tuning)
- [[v12/questions/checkpoint-monitoring-optimization-scenarios|Checkpoint monitoring and optimization scenarios (unverified)]] (PG 12 checkpoint monitoring and tuning workflow using `pg_stat_bgwriter`, `log_checkpoints`, a `pg_settings` checkpoint-configuration inventory query, checkpoint/WAL GUC reload semantics, and deployment scenarios for fast local disks and cloud block storage)
- [[v12/questions/disk-io-before-after-query-plan-execution|Disk I/O before/after query planning and execution]] (agent-reviewed query-lifecycle I/O map covering catalog and relcache access, planner relation-size probes, shared-buffer hits versus storage reads, DML writes, hint bits, temp spills, WAL flushes, bgwriter/checkpointer writes, DDL/maintenance file operations, and the exact `track_io_timing` boundary around `smgrread` / `smgrwrite`)
- [[v12/questions/enable-io-timing-measurements-production|Enable I/O timing measurements on production]] (agent-reviewed procedure for enabling `track_io_timing` on production, with host timing preflight, reload/session semantics, tagged SQL sampling, `pg_stat_database`, optional `pg_stat_statements`, and plan-level drill-down)
- [[v12/questions/inheritance-partition-no-pruning-overhead|Inheritance partition query overhead when no pruning is possible]] (agent-reviewed matrix of PG 12 tunables that reduce or add overhead when a traditional-inheritance query must visit roughly 300 child tables because constraint exclusion cannot prune them)

A generated project-context pack exists under `.wiki-runtime/context/postgres-12/`; its compiler database now includes the normal build plus an appended contrib build capture.

## Project Context

- Manifest: `.wiki-runtime/context/postgres-12/manifest.md`
- Generated artifacts: `.wiki-runtime/context/postgres-12/tree-L4.txt`, `.wiki-runtime/context/postgres-12/build-config/`, `.wiki-runtime/context/postgres-12/external-deps.txt`, `.wiki-runtime/context/postgres-12/compile_commands.json` (normal build plus appended contrib capture), `.wiki-runtime/context/postgres-12/include-deps.txt`, and `.wiki-runtime/context/postgres-12/callgraphs/`
- Deferred artifacts: none
