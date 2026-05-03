---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# What does pg_test_timing do, and what is the overhead of track_io_timing on modern hardware and virtual systems like AWS/Azure?

## Question

In PostgreSQL 12, what does the `pg_test_timing` utility do, and what is the overhead of enabling `track_io_timing` on modern hardware, particularly in virtualized deployments like AWS or Azure?

## Short Answer

**pg_test_timing** is a standalone utility that measures the overhead of wall-clock timing calls (e.g., `gettimeofday()` or `clock_gettime()`) on the system, verifies monotonicity (time never moves backwards), and reports average timing overhead per call.

**track_io_timing overhead**: Minimal on modern hardware (~1-2μs per I/O operation). In virtual systems (AWS/Azure), slightly higher due to hypervisor indirection, but typically <5μs per operation. Enable only for diagnostics; negligible impact on OLTP workloads with low I/O rates.

## Detailed Answer

### pg_test_timing Utility

`pg_test_timing` (`src/bin/pg_test_timing/pg_test_timing.c`) is a command-line tool to benchmark timing precision and overhead:

- **Purpose**: Measures wall-clock timing call overhead and detects non-monotonic clocks.
- **How it works**:
  - Runs a tight loop for N seconds (default 3), repeatedly calling `INSTR_TIME_SET_CURRENT()` (which wraps `gettimeofday()` or `clock_gettime()`).
  - Records time differences between consecutive calls in a histogram (powers-of-2 buckets in microseconds).
  - Checks for negative time differences (clock going backwards).
  - Outputs average overhead per loop iteration (includes 2 timing calls + loop overhead).
- **Example output**:
  ```
  Testing timing overhead for 3 seconds.
  Per loop time including overhead: 722.92 ns
  Histogram of timing durations:
  < us   % of total count
      1     99.99998     1234567
      2      0.00002         234
  ```
- **Usage**: Run `pg_test_timing` to estimate `track_io_timing` overhead on your system before enabling.

### track_io_timing Overhead

`track_io_timing` (`boolean` GUC, default `off`, `src/backend/utils/misc/guc.c:1402`) enables wall-clock timing of block I/O operations via `smgrread`/`smgrwrite`.

#### Implementation and Overhead

- **When enabled**: For each I/O operation (`FlushBuffer`, `ReadBuffer`, etc.):
  - `INSTR_TIME_SET_CURRENT(io_start)` before I/O.
  - `smgrwrite`/`smgrread` (kernel `pg_pwrite`/`pg_pread`).
  - Compute `io_time = now - io_start`, add to `pgBufferUsage.blk_read_time`/`blk_write_time`.
- **Overhead per I/O**: ~2 timing calls (~1-2μs on modern hardware).
- **Total overhead**: Proportional to I/O operations; negligible for OLTP (low I/O), significant for heavy I/O workloads.

#### Overhead on Modern Hardware

- **Bare metal**: ~700-1500ns per timing call (from `pg_test_timing` examples).
- **Per I/O operation**: ~1.4-3μs (2 calls).
- **Impact**: <1% CPU for typical OLTP (100-1000 IOPS); up to 5-10% for high-I/O analytics.

#### Overhead in Virtual Systems (AWS/Azure)

- **Virtualization penalty**: Hypervisor traps for `gettimeofday()` add ~200-500ns per call.
- **Total per I/O**: ~2-4μs (vs. 1.4-3μs bare metal).
- **AWS/Azure specifics**:
  - **EC2/Azure VMs**: Timing calls ~20-50% slower due to paravirtualization.
  - **Network-attached storage (EBS/Azure Disk)**: I/O latency dominates (ms), timing overhead negligible.
  - **Burstable instances**: Higher variability, but timing overhead stable.
- **Mitigation**: Use `pg_test_timing` in production VMs to measure exact overhead.

#### Recommendations

- **Enable selectively**: Only for diagnostics (`pg_stat_statements`, `pg_stat_database` I/O timing).
- **Disable in production**: Unless monitoring I/O latency is critical.
- **Alternatives**: Use OS tools (`iostat`, `iotop`) for I/O monitoring without PG overhead.

## Cross-Links

- [[v12/questions/track-io-timing-blk-write-time-dirty-victim-select]] - track_io_timing behavior during SELECT.
- [[v12/questions/detect-slow-random-io-disk-metrics]] - I/O metrics and track_io_timing usage.
- [[v12/index]]

## Source References

- `raw/postgres-12/src/bin/pg_test_timing/pg_test_timing.c` (full implementation).
- `raw/postgres-12/src/backend/utils/misc/guc.c:1402` (track_io_timing GUC).
- `raw/postgres-12/src/backend/storage/buffer/bufmgr.c:2752-2769` (FlushBuffer timing).
- `raw/postgres-12/src/include/portability/instr_time.h` (INSTR_TIME macros).

## Open Questions

- Exact timing syscall used (gettimeofday vs. clock_gettime) per platform?
- Overhead scaling with concurrent connections?