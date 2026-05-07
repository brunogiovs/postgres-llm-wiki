---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Bgwriter tuning recommendations (unverified)

## Question

In PostgreSQL 12, list the recommended bgwriter settings for the main PostgreSQL bgwriter tuning scenarios. Show each tuning knob's default, range, and reload semantics; for each scenario, give the documented direction of change for each knob and ground the direction claim in the pinned source. Include the diagnostic counters from `pg_stat_bgwriter` that should drive numeric tuning, verify their wiring against the source, and explain how to interpret `buffers_backend / (buffers_clean + buffers_backend + buffers_checkpoint)` with practical threshold percentages and actions for each range.

## Answer

Assumption: "PostgreSQL 12" means the local checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`. The PG 12 source defines four bgwriter GUCs and exposes diagnostic counters through `pg_stat_bgwriter`. The pinned source documents direction-of-effect per knob but does not encode specific per-scenario numeric "recommendations"; the scenario table states the documented direction of change for each knob, and the backend-write-share bands below are operational heuristics for deciding how strongly to move in that direction. Specific percentage thresholds are not PostgreSQL-defined constants.

### The bgwriter loop in PG 12

Each round, the bgwriter sleeps `bgwriter_delay` ms ([[raw/postgres-12/src/backend/postmaster/bgwriter.c#BackgroundWriterMain|bgwriter.c#L337-L339]]), then `BgBufferSync` estimates the next round's allocation pressure as `upcoming_alloc_est = smoothed_alloc * bgwriter_lru_multiplier` ([[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BgBufferSync|bufmgr.c#L2226]]) and writes dirty reusable buffers from the LRU clock-sweep position until it laps the strategy scan, hits `bgwriter_lru_maxpages` (which increments `m_maxwritten_clean` and breaks the loop), or has enough clean reusable buffers to satisfy the estimate ([[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BgBufferSync|bufmgr.c#L2275-L2300]]). On Linux it then asks the kernel to start writeback of the freshly written pages every `bgwriter_flush_after` blocks ([[raw/postgres-12/src/backend/postmaster/bgwriter.c#BackgroundWriterMain|bgwriter.c#L157]] wires `bgwriter_flush_after` into `WritebackContextInit`). When `BgBufferSync` reports nothing happened for two consecutive cycles, the bgwriter hibernates by sleeping `bgwriter_delay * 50` ms (`HIBERNATE_FACTOR`) until a backend wakes it via the latch ([[raw/postgres-12/src/backend/postmaster/bgwriter.c#BackgroundWriterMain|bgwriter.c#L73, L359-L370]]).

### The four bgwriter GUCs (PG 12)

All four are `PGC_SIGHUP`. To apply changes use `ALTER SYSTEM SET ...; SELECT pg_reload_conf();` (or send `SIGHUP` to the postmaster); no restart needed, no per-session scope.

| GUC | Default | Range | Unit | GUC context | Source |
|---|---|---|---|---|---|
| `bgwriter_delay` | `200ms` | `10`–`10000` | ms | `PGC_SIGHUP` | [[raw/postgres-12/src/backend/utils/misc/guc.c#L2728-L2736|guc.c#L2728]] |
| `bgwriter_lru_maxpages` | `100` | `0`–`INT_MAX/2` | buffers/round | `PGC_SIGHUP` | [[raw/postgres-12/src/backend/utils/misc/guc.c#L2738-L2746|guc.c#L2738]] |
| `bgwriter_lru_multiplier` | `2.0` | `0.0`–`10.0` | multiplier | `PGC_SIGHUP` | [[raw/postgres-12/src/backend/utils/misc/guc.c#L3351-L3359|guc.c#L3351]] |
| `bgwriter_flush_after` | `512kB` on Linux (`64` blocks); `0` elsewhere | `0`–`2MB` (`WRITEBACK_MAX_PENDING_FLUSHES = 256`) | blocks | `PGC_SIGHUP` | [[raw/postgres-12/src/backend/utils/misc/guc.c#L2748-L2757|guc.c#L2748]], default macros in [[raw/postgres-12/src/include/pg_config_manual.h#L153-L163|pg_config_manual.h#L153]] |

The shipped sample defaults match: [[raw/postgres-12/src/backend/utils/misc/postgresql.conf.sample#L168|postgresql.conf.sample#L168]]. Setting `bgwriter_lru_maxpages = 0` disables background writing entirely; checkpoints are unaffected ([[raw/postgres-12/doc/src/sgml/config.sgml#L2080-L2088|config.sgml#L2080]]).

`PGC_SIGHUP` reload semantics per AGENTS.md: change via `postgresql.conf` + `SIGHUP` (or `pg_reload_conf()` / `ALTER SYSTEM`); no restart, no session-scope `SET` because none of these GUCs are user-settable.

### Tuning scenarios (source-documented direction of change)

| Scenario | `bgwriter_delay` | `bgwriter_lru_maxpages` | `bgwriter_lru_multiplier` | `bgwriter_flush_after` | Counter to watch |
|---|---|---|---|---|---|
| **Default / unknown workload** | `200ms` | `100` | `2.0` | `512kB` (Linux) / `0` (other) | `buffers_backend`, `maxwritten_clean` |
| **Write-heavy / high buffer-allocation rate** — backends are forced to write their own buffers because the bgwriter cannot keep up | shorter (more frequent rounds) | larger (allow more writes per round) | larger (more cushion vs. demand spikes) | keep default on Linux | drive `buffers_backend` down; watch `maxwritten_clean` |
| **Read-mostly or low-churn workload** — minimize the extra I/O of the bgwriter rewriting repeatedly-dirtied pages | keep or lengthen | smaller | smaller | keep default | accept higher `buffers_backend` for fewer total writes |
| **Avoid checkpoint fsync stalls / smooth kernel writeback (Linux)** | — | — | — | non-zero (default `512kB` already enables this) | watch `checkpoint_sync_time` |
| **Workload bigger than `shared_buffers` but smaller than the OS page cache, where `bgwriter_flush_after` regresses latency** | — | — | — | `0` | latency improvement, not a bgwriter counter |
| **Non-Linux platforms (no `sync_file_range`)** | — | — | — | `0` (default; setting may have no effect) | n/a |
| **Disable bgwriter entirely** | n/a | `0` | n/a | n/a | n/a — backends do all writes |

Source backing for each direction:

- "Larger values provide some cushion against spikes in demand, while smaller values intentionally leave writes to be done by server processes" — about `bgwriter_lru_multiplier`, [[raw/postgres-12/doc/src/sgml/config.sgml#L2108-L2113|config.sgml#L2108]].
- "Smaller values of `bgwriter_lru_maxpages` and `bgwriter_lru_multiplier` reduce the extra I/O load caused by the background writer, but make it more likely that server processes will have to issue writes for themselves, delaying interactive queries" — [[raw/postgres-12/doc/src/sgml/config.sgml#L2153-L2158|config.sgml#L2153]].
- "While a repeatedly-dirtied page might otherwise be written only once per checkpoint interval, the background writer might write it several times as it is dirtied in the same interval" (the cost of being more aggressive) — [[raw/postgres-12/doc/src/sgml/config.sgml#L2030-L2042|config.sgml#L2030]].
- `bgwriter_flush_after` "will limit the amount of dirty data in the kernel's page cache, reducing the likelihood of stalls when an `fsync` is issued at the end of a checkpoint … there also are some cases, especially with workloads that are bigger than `shared_buffers`, but smaller than the OS's page cache, where performance might degrade. This setting may have no effect on some platforms." — [[raw/postgres-12/doc/src/sgml/config.sgml#L2127-L2148|config.sgml#L2127]].
- `sync_file_range`-gated default for `bgwriter_flush_after` — [[raw/postgres-12/src/include/pg_config_manual.h#L147-L161|pg_config_manual.h#L147]].
- "Setting [`bgwriter_lru_maxpages`] to zero disables background writing" — [[raw/postgres-12/doc/src/sgml/config.sgml#L2080-L2088|config.sgml#L2080]].
- `bgwriter_delay` "delay between activity rounds" with default 200 ms and 10 ms resolution caveat — [[raw/postgres-12/doc/src/sgml/config.sgml#L2052-L2068|config.sgml#L2052]].

### Counters to drive numeric tuning

The `pg_stat_bgwriter` view exposes the counters that turn the directional matrix above into concrete adjustments. View definition: [[raw/postgres-12/src/backend/catalog/system_views.sql#L935-L947|system_views.sql#L935]]; column descriptions: [[raw/postgres-12/doc/src/sgml/monitoring.sgml#L2400-L2477|monitoring.sgml#L2400]].

Each counter's wiring against PG 12 source:

| Column | Meaning | C accumulator | Increment site |
|---|---|---|---|
| `buffers_checkpoint` | Buffers written during checkpoints | `BgWriterStats.m_buf_written_checkpoints` -> `globalStats.buf_written_checkpoints` -> `pg_stat_get_bgwriter_buf_written_checkpoints()` | checkpoint write increment at [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BufferSync|bufmgr.c#L1991-L1994]]; SQL function at [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#L1612-L1616|pgstatfuncs.c#L1612]] |
| `buffers_clean` | Buffers written by the bgwriter | `BgWriterStats.m_buf_written_clean` → `globalStats.buf_written_clean` → `pg_stat_get_bgwriter_buf_written_clean()` | accumulator at [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BgBufferSync|bufmgr.c#L2300]]; SQL function at [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#L1618-L1622|pgstatfuncs.c#L1618]] |
| `maxwritten_clean` | Rounds where the bgwriter stopped because it hit `bgwriter_lru_maxpages` | `BgWriterStats.m_maxwritten_clean` → `globalStats.maxwritten_clean` → `pg_stat_get_bgwriter_maxwritten_clean()` | increment at [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BgBufferSync|bufmgr.c#L2290-L2293]]; SQL function at [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#L1624-L1628|pgstatfuncs.c#L1624]] |
| `buffers_backend` | Buffers written directly by a backend instead of by the bgwriter | `CheckpointerShmem->num_backend_writes` → `BgWriterStats.m_buf_written_backend` → `globalStats.buf_written_backend` → `pg_stat_get_buf_written_backend()` | increment at [[raw/postgres-12/src/backend/postmaster/checkpointer.c#ForwardSyncRequest|checkpointer.c#L1120-L1122]]; rollup into BgWriterStats at [[raw/postgres-12/src/backend/postmaster/checkpointer.c#L1297-L1300|checkpointer.c#L1297]]; SQL function at [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#L1650-L1654|pgstatfuncs.c#L1650]] |
| `buffers_backend_fsync` | Backend had to perform its own fsync because the checkpointer's request queue was full | `CheckpointerShmem->num_backend_fsync` → `globalStats.buf_fsync_backend` | increment at [[raw/postgres-12/src/backend/postmaster/checkpointer.c#ForwardSyncRequest|checkpointer.c#L1137-L1138]] |
| `buffers_alloc` | Buffer allocations (new buffer demand) | `globalStats.buf_alloc` | exposed at [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#L1662-L1667|pgstatfuncs.c#L1662]] |
| `checkpoint_write_time`, `checkpoint_sync_time` | Total time spent writing / fsyncing during checkpoints, in ms | `globalStats.checkpoint_write_time`, `checkpoint_sync_time` | exposed at [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c#L1630-L1642|pgstatfuncs.c#L1630]] |

### Backend-write-share threshold bands

Use the ratio on **deltas over a representative interval**, not on lifetime counters since `stats_reset`:

```text
backend_write_pct =
  100 * delta(buffers_backend)
      / NULLIF(delta(buffers_clean) + delta(buffers_backend) + delta(buffers_checkpoint), 0)
```

The denominator is total shared-buffer writes visible in `pg_stat_bgwriter`: checkpoint writes, bgwriter writes, and backend writes. The numerator is the share that reached the backend write path instead of being absorbed by bgwriter/checkpointer background activity. PostgreSQL documents the bgwriter's purpose as writing dirty buffers so query-serving processes "seldom or never need to wait for a write", while also warning that smaller `bgwriter_lru_maxpages` and `bgwriter_lru_multiplier` make it more likely that server processes must issue writes themselves and delay interactive queries ([[raw/postgres-12/doc/src/sgml/config.sgml#L2030-L2041|config.sgml#L2030]], [[raw/postgres-12/doc/src/sgml/config.sgml#L2153-L2158|config.sgml#L2153]]). In this wiki's operational shorthand, **"high" starts around a sustained 10% backend-write share**, and **20%+ is severe enough to tune actively unless the interval is known to be an unusual burst**.

| Backend-write share | Interpretation | Proposed action |
|---|---|---|
| `0%`-`2%` | Excellent. Almost all dirty-buffer writes are happening through checkpoint or bgwriter paths, so backends are rarely forced onto the write path. | Leave bgwriter settings alone. If `buffers_clean` is also much larger than `buffers_backend` and write I/O looks excessive, consider the read-mostly direction: slightly lower `bgwriter_lru_multiplier` or `bgwriter_lru_maxpages`, then re-measure total writes and latency. |
| `>2%`-`5%` | Healthy for many mixed workloads. Some foreground writes occur, but they are not a dominant part of buffer writing. | Usually no change. Watch `maxwritten_clean`; if it rises repeatedly, the per-round cap is being reached, so raise `bgwriter_lru_maxpages` first. |
| `>5%`-`10%` | Caution band. The bgwriter may be a little behind during allocation bursts, especially if latency-sensitive sessions line up with these writes. | Re-check on multiple intervals. If sustained, raise `bgwriter_lru_multiplier` modestly, for example by `+0.5` to `+1.0` from the current value, to add cushion against spikes. If `maxwritten_clean` increases in the same intervals, raise `bgwriter_lru_maxpages` by roughly `50%`-`100%` instead or first. |
| `>10%`-`20%` | High. Foreground writes are a material share of dirty-buffer write work, matching the "bgwriter is not keeping up" diagnostic. | Move toward the write-heavy column: raise `bgwriter_lru_maxpages` first when `maxwritten_clean` is non-zero; otherwise raise `bgwriter_lru_multiplier` toward a more aggressive cushion, for example from the default `2.0` toward `3.0`-`4.0` as a measured experiment. If the ratio remains high and storage has write headroom, shorten `bgwriter_delay`, for example from `200ms` to `100ms`, so rounds run more often. |
| `>20%`-`40%` | Very high. Backends are doing enough writes that query latency can be directly affected, and either the bgwriter cap, its demand estimate, or the storage/checkpoint environment is not absorbing the workload. | Raise `bgwriter_lru_maxpages` aggressively, often `2x` or more from the current setting while staying inside the GUC range. Raise `bgwriter_lru_multiplier` in the same tuning window only if `maxwritten_clean` is not the obvious limiter. Consider shortening `bgwriter_delay` after increasing capacity per round. Also inspect `buffers_backend_fsync`, `checkpoint_write_time`, `checkpoint_sync_time`, and device saturation, because a saturated checkpointer or storage layer will not be fixed by making the bgwriter issue more writes. |
| `>40%` | Critical for bgwriter smoothing. A large fraction of visible buffer writes are happening in foreground paths, or the measurement window is dominated by an unusual burst. | Treat as an incident or controlled tuning exercise. Combine a larger `bgwriter_lru_maxpages`, a higher `bgwriter_lru_multiplier`, and possibly a shorter `bgwriter_delay`, then measure latency and total write volume. If the percentage does not fall, stop escalating bgwriter alone and investigate checkpoint cadence, dirtying rate, `shared_buffers` fit, write bandwidth, and storage latency; otherwise the bgwriter may simply be moving the same bottleneck earlier. |

Choose the first knob from the shape of the supporting counters:

- High backend-write share plus rising `maxwritten_clean` means `bgwriter_lru_maxpages` is the first suspect, because `BgBufferSync` increments `m_maxwritten_clean` exactly when the scan stops after reaching that cap ([[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BgBufferSync|bufmgr.c#L2287-L2293]]).
- High backend-write share with little or no `maxwritten_clean` points more toward the demand estimate or cadence: `bgwriter_lru_multiplier` scales the predicted next-round allocation need, and `bgwriter_delay` controls how often `BgBufferSync` runs ([[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BgBufferSync|bufmgr.c#L2215-L2227]], [[raw/postgres-12/src/backend/postmaster/bgwriter.c#BackgroundWriterMain|bgwriter.c#L337-L339]]).
- Any increase in `buffers_backend_fsync` is a stronger warning than `buffers_backend` alone, because it means the backend could not hand the fsync request to the checkpointer queue and had to do its own fsync path ([[raw/postgres-12/src/backend/postmaster/checkpointer.c#ForwardSyncRequest|checkpointer.c#L1124-L1138]]).
- A low backend-write share with high `buffers_checkpoint` means checkpoint writes dominate the denominator; tune checkpoint/WAL behavior separately instead of making the bgwriter more aggressive.

Iterative bgwriter tuning loop, grounded in those counters:

1. Take a delta of `pg_stat_bgwriter` over a representative interval (use `pg_stat_reset_shared('bgwriter')` to baseline if needed).
2. Compute `backend_write_pct` from the delta counters above. If it is sustained above `10%`, push toward the "write-heavy" column; if it is above `20%`, tune actively and check for storage/checkpoint pressure at the same time.
3. If `maxwritten_clean` is consistently non-zero, the per-round write cap is biting → raise `bgwriter_lru_maxpages` first; the bgwriter writes more per round but rounds remain `bgwriter_delay` apart.
4. If `buffers_clean` is high but `buffers_backend` is near zero, the bgwriter may be doing more work than necessary → push toward the "read-mostly" column (smaller `bgwriter_lru_maxpages` / `bgwriter_lru_multiplier`).
5. If `checkpoint_sync_time` spikes during checkpoints on Linux, leave `bgwriter_flush_after` non-zero (default `512kB`) and verify on representative storage; if the workload matches the documented regression case (bigger than `shared_buffers`, smaller than OS page cache), set `bgwriter_flush_after = 0`.

Sample diagnostic snippet (read-only, follows AGENTS.md SQL discipline — inline tag, session-scoped timeouts):

```sql
SET /* wiki_bgwriter_statement_timeout */ statement_timeout = '30s';
SET /* wiki_bgwriter_lock_timeout */ lock_timeout = '5s';
SELECT /* wiki_bgwriter_counters */
       buffers_checkpoint,
       buffers_clean,
       maxwritten_clean,
       buffers_backend,
       buffers_backend_fsync,
       buffers_alloc,
       checkpoint_write_time,
       checkpoint_sync_time,
       stats_reset
  FROM pg_stat_bgwriter;
```

Current-counter backend-write-share snapshot (use monitoring-system deltas for final decisions):

```sql
SET /* wiki_bgwriter_ratio_statement_timeout */ statement_timeout = '30s';
SET /* wiki_bgwriter_ratio_lock_timeout */ lock_timeout = '5s';
SELECT /* wiki_bgwriter_backend_write_share */
       buffers_checkpoint,
       buffers_clean,
       buffers_backend,
       buffers_checkpoint + buffers_clean + buffers_backend AS total_buffer_writes,
       CASE
         WHEN buffers_checkpoint + buffers_clean + buffers_backend > 0
         THEN round(
                (buffers_backend::numeric * 100)
                / (buffers_checkpoint + buffers_clean + buffers_backend),
                2
              )
       END AS backend_write_pct,
       maxwritten_clean,
       buffers_backend_fsync,
       stats_reset
  FROM pg_stat_bgwriter;
```

Apply a tuning change with `pg_reload_conf()`:

```sql
SET /* wiki_bgwriter_alter_statement_timeout */ statement_timeout = '30s';
SET /* wiki_bgwriter_alter_lock_timeout */ lock_timeout = '5s';
ALTER /* wiki_set_bgwriter_lru_maxpages */ SYSTEM SET bgwriter_lru_maxpages = 100;
SELECT /* wiki_reload_conf */ pg_reload_conf();
```

`statement_timeout` / `lock_timeout` are session-scoped (`SET`); pick values appropriate for the operation (these defaults suit the diagnostic snippet only — `ALTER SYSTEM` itself is fast, but the tag/timeout discipline applies to the whole session).

## Context Reviewed

- Navigation and bookkeeping: `wiki/versions.md`, `wiki/index.md`, the last 20 entries from `scripts/recent_log --limit 20`, and `wiki/v12/index.md`.
- Context pack: `.wiki-runtime/context/postgres-12/manifest.md` (regenerated 2026-05-06T20:25:04Z, pinned commit `45b88269...`); `tree-L4.txt`, `compile_commands.json`, `include-deps.txt`, and the focused `BackgroundWriterMain` / `ExecutorRun` callgraphs.
- Source search envelope: `scripts/source_lookup --version 12 --symbol bgwriter_delay --regex`, `scripts/source_lookup --version 12 --symbol bgwriter_lru_multiplier --regex`, `scripts/source_lookup --version 12 --symbol DEFAULT_BGWRITER_FLUSH_AFTER --regex`, `scripts/source_lookup --version 12 --symbol pg_stat_get_bgwriter --regex`, `scripts/source_lookup --version 12 --symbol maxwritten_clean --regex`, `scripts/source_lookup --version 12 --symbol m_buf_written_backend --regex`, `scripts/source_lookup --version 12 --symbol num_backend_writes --regex`, `scripts/source_lookup --version 12 --symbol buf_written_checkpoints`, `scripts/source_lookup --version 12 --symbol 'BufferSync('`, and targeted `--path ... --start ... --limit ...` slices into `src/backend/utils/misc/guc.c`, `src/backend/utils/misc/postgresql.conf.sample`, `src/include/pg_config_manual.h`, `src/backend/postmaster/bgwriter.c`, `src/backend/storage/buffer/bufmgr.c`, `src/backend/postmaster/checkpointer.c`, `src/backend/postmaster/pgstat.c`, `src/backend/utils/adt/pgstatfuncs.c`, `src/backend/catalog/system_views.sql`, `doc/src/sgml/config.sgml`, and `doc/src/sgml/monitoring.sgml`.
- Context dependency checks: `scripts/source_deps --version 12 --compile-unit src/backend/storage/buffer/bufmgr.c --full-command`, `scripts/source_deps --version 12 --includes src/backend/storage/buffer/bufmgr.c --limit 80`, and `scripts/source_deps --version 12 --compile-unit src/backend/postmaster/checkpointer.c --full-command`.
- Tests inspected: regression view-definition coverage in [[raw/postgres-12/src/test/regress/expected/rules.out|rules.out#L1795-L1805]], which confirms the `pg_stat_bgwriter` view shape against a `pg_dump --schema-only` style normalization. No bgwriter-tuning behavior test exists in the v12 tree.
- GUC-context discipline: the four bgwriter GUCs and `effective_io_concurrency` / `backend_flush_after` neighbors all carry `PGC_SIGHUP` or `PGC_USERSET` per [[raw/postgres-12/src/backend/utils/misc/guc.c#L2728-L2786|guc.c#L2728]] and [[raw/postgres-12/src/backend/utils/misc/guc.c#L3351-L3359|guc.c#L3351]]; reload semantics map to AGENTS.md "GUC Configuration Changes" section.

## Evidence Map

- Defaults and ranges of the four bgwriter GUCs map to `ConfigureNamesInt` / `ConfigureNamesReal` entries in [[raw/postgres-12/src/backend/utils/misc/guc.c|guc.c]] and to `DEFAULT_BGWRITER_FLUSH_AFTER` / `WRITEBACK_MAX_PENDING_FLUSHES` in [[raw/postgres-12/src/include/pg_config_manual.h|pg_config_manual.h]].
- Loop structure (delay → BgBufferSync → pgstat_send_bgwriter → WaitLatch → optional hibernation) maps to [[raw/postgres-12/src/backend/postmaster/bgwriter.c#BackgroundWriterMain|bgwriter.c#L240-L373]].
- Round-by-round write decision (alloc smoothing, multiplier, maxpages cap, writeback context) maps to [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#BgBufferSync|bufmgr.c#L2200-L2300]].
- Direction-of-change guidance maps to [[raw/postgres-12/doc/src/sgml/config.sgml|config.sgml#L2030-L2158]] (the bgwriter GUC subsection).
- `pg_stat_bgwriter` counters map to: view definition in [[raw/postgres-12/src/backend/catalog/system_views.sql|system_views.sql#L935-L947]]; column docs in [[raw/postgres-12/doc/src/sgml/monitoring.sgml|monitoring.sgml#L2400-L2477]]; SQL functions in [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c|pgstatfuncs.c#L1600-L1670]]; checkpoint-write accumulator in [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c|bufmgr.c#L1991-L1994]]; bgwriter-side accumulators in [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c|bufmgr.c#L2290-L2300]]; backend-write counter in [[raw/postgres-12/src/backend/postmaster/checkpointer.c|checkpointer.c#L1120-L1138, L1297-L1300]]; aggregator in [[raw/postgres-12/src/backend/postmaster/pgstat.c|pgstat.c#L6316-L6321]].
- Reload semantics (`PGC_SIGHUP`, no restart, no per-session scope) map to the GUC entries above and AGENTS.md "GUC Configuration Changes".

## Open Questions

- The pinned PG 12 source and its docs do not specify numeric per-scenario "recommendations" for any of the four bgwriter GUCs beyond the documented defaults and ranges. The backend-write-share percentages in this page are practical wiki heuristics derived from the source-defined counter meanings and bgwriter control loop; they are not source-defined PostgreSQL thresholds. Values commonly cited in external tuning literature are intentionally not treated as source facts here. To turn the directional matrix into numbers, drive `pg_stat_bgwriter` deltas as described and adjust until `buffers_backend` is small relative to total writes and `maxwritten_clean` is near zero for the workload.
- The hibernation factor (`HIBERNATE_FACTOR = 50`) is a compile-time constant ([[raw/postgres-12/src/backend/postmaster/bgwriter.c#L73|bgwriter.c#L73]]) with a code comment that asks "Perhaps this needs to be configurable?". It is not exposed as a GUC in PG 12; tuning the *idle* cadence is therefore not user-controllable beyond `bgwriter_delay` itself.
- `bgwriter_flush_after` is documented to "have no effect on some platforms" ([[raw/postgres-12/doc/src/sgml/config.sgml#L2137-L2138|config.sgml#L2137]]). The exact set of platforms where the writeback hint is effective is not enumerated in the v12 tree beyond the `HAVE_SYNC_FILE_RANGE` gate of the default value; behavior on non-Linux Unix variants where `sync_file_range` exists but the hint may be a no-op is not characterized further by the pinned source.

## Source References

- Source pin and context pack: [[raw/postgres-12/]], `.wiki-runtime/context/postgres-12/manifest.md`
- GUC definitions: [[raw/postgres-12/src/backend/utils/misc/guc.c|guc.c]], [[raw/postgres-12/src/include/pg_config_manual.h|pg_config_manual.h]], [[raw/postgres-12/src/backend/utils/misc/postgresql.conf.sample|postgresql.conf.sample]]
- Bgwriter loop: [[raw/postgres-12/src/backend/postmaster/bgwriter.c|bgwriter.c]]
- BgBufferSync logic and counter accumulation: [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c|bufmgr.c]]
- Backend-write counter wiring: [[raw/postgres-12/src/backend/postmaster/checkpointer.c|checkpointer.c]]
- `pg_stat_bgwriter` view and SQL functions: [[raw/postgres-12/src/backend/catalog/system_views.sql|system_views.sql]], [[raw/postgres-12/src/backend/utils/adt/pgstatfuncs.c|pgstatfuncs.c]], [[raw/postgres-12/src/backend/postmaster/pgstat.c|pgstat.c]]
- Documentation: [[raw/postgres-12/doc/src/sgml/config.sgml|config.sgml]] (bgwriter GUC subsection), [[raw/postgres-12/doc/src/sgml/monitoring.sgml|monitoring.sgml]] (`pg_stat_bgwriter` column descriptions)
- Source searches used: `scripts/source_lookup --version 12 --symbol ... --regex`, targeted `scripts/source_lookup --version 12 --path ...`, and context-pack manifest review
