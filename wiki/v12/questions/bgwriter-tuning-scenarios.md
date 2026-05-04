---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

## Question

In PostgreSQL 12, list the recommended bgwriter settings for the following PostgreSQL bgwriter tuning scenarios:

- High checkpoint I/O spikes / poor query latency during checkpoints
- Bgwriter hits maxwritten_clean / bgwriter_lru_maxpages limit too often
- Backends doing too much writing (buffers_backend high)
- Bursty or variable write workloads
- Too much constant background I/O on idle/low-load systems
- Low-power / laptop / battery environments (minimize disk activity)
- Kernel page cache pressure & fsync stalls (Linux)
- Very high-write OLTP with large shared_buffers

## Answer

### Background Writer Settings in PostgreSQL 12

The background writer in PostgreSQL 12 has four main tunable parameters:

- `bgwriter_delay`: Sleep time between rounds (default 200ms, range 10-10000ms) [[raw/postgres-12/src/backend/utils/misc/guc.c#2728-2735]]
- `bgwriter_lru_maxpages`: Maximum number of LRU pages to flush per round (default 100, range 0 to INT_MAX/2) [[raw/postgres-12/src/backend/utils/misc/guc.c#2739-2745]]
- `bgwriter_lru_multiplier`: Multiple of average buffer usage to free per round (default 2.0, range 0.0-10.0) [[raw/postgres-12/src/backend/utils/misc/guc.c#3352-3359]]
- `bgwriter_flush_after`: Number of pages after which writes are flushed to disk (default 0, range 0 to WRITEBACK_MAX_PENDING_FLUSHES) [[raw/postgres-12/src/backend/utils/misc/guc.c#2749-2756]]

The background writer algorithm estimates future buffer allocation needs based on recent allocation rates and scans ahead of the clock sweep to clean dirty buffers [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#2052-2336]].

### Recommended Settings by Scenario

#### High checkpoint I/O spikes / poor query latency during checkpoints

**Problem**: Checkpoints cause I/O spikes that interfere with query performance.

**Recommendations**:
- Increase `bgwriter_lru_maxpages` to 200-500 to clean more buffers per round, reducing checkpoint I/O spikes
- Increase `bgwriter_lru_multiplier` to 3.0-4.0 for more aggressive cleaning ahead of allocations
- Consider `bgwriter_flush_after = 32` (8KB) to enable writeback throttling
- Reduce `checkpoint_completion_target` to 0.5-0.7 to spread checkpoint I/O over a shorter time

#### Bgwriter hits maxwritten_clean / bgwriter_lru_maxpages limit too often

**Problem**: Background writer frequently hits the `bgwriter_lru_maxpages` limit, indicating it's not keeping up with dirty buffer generation.

**Recommendations**:
- Increase `bgwriter_lru_maxpages` to 200-1000 to allow more pages per round
- Increase `bgwriter_lru_multiplier` to 3.0-5.0 for more aggressive buffer cleaning
- Decrease `bgwriter_delay` to 100-150ms for more frequent cleaning rounds
- Consider increasing `shared_buffers` if memory allows

#### Backends doing too much writing (buffers_backend high)

**Problem**: Regular backends are writing too many buffers directly instead of the background writer handling them.

**Recommendations**:
- Increase `bgwriter_lru_multiplier` to 4.0-6.0 to make bgwriter more aggressive
- Increase `bgwriter_lru_maxpages` to 300-1000 to clean more per round
- Decrease `bgwriter_delay` to 50-100ms for more frequent operation
- Monitor `pg_stat_bgwriter.buffers_clean` vs `buffers_backend` ratios

#### Bursty or variable write workloads

**Problem**: Workloads with variable write patterns cause inconsistent I/O behavior.

**Recommendations**:
- Increase `bgwriter_lru_multiplier` to 3.0-4.0 to handle bursty allocation patterns
- Set `bgwriter_lru_maxpages` to 200-500 for moderate per-round cleaning
- Keep `bgwriter_delay` at default 200ms for responsiveness
- Consider `bgwriter_flush_after = 64` (16KB) for writeback control

#### Too much constant background I/O on idle/low-load systems

**Problem**: Background writer generates unnecessary I/O when system is mostly idle.

**Recommendations**:
- Decrease `bgwriter_lru_multiplier` to 1.0-1.5 to reduce cleaning aggressiveness
- Set `bgwriter_lru_maxpages` to 50-100 to limit per-round I/O
- Increase `bgwriter_delay` to 500-1000ms to reduce wake-up frequency
- The bgwriter will hibernate when no allocations occur [[raw/postgres-12/src/backend/postmaster/bgwriter.c#359-370]]

#### Low-power / laptop / battery environments (minimize disk activity)

**Problem**: Minimize disk I/O to preserve battery life and reduce noise/heat.

**Recommendations**:
- Set `bgwriter_lru_maxpages = 0` to disable LRU scanning entirely [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#2109-2113]]
- Increase `bgwriter_delay` to 2000-5000ms for minimal wake-ups
- Decrease `bgwriter_lru_multiplier` to 0.5-1.0 if LRU scanning enabled
- Rely on backends to handle their own dirty buffer writes

#### Kernel page cache pressure & fsync stalls (Linux)

**Problem**: Linux page cache pressure causes fsync stalls during checkpoints.

**Recommendations**:
- Increase `bgwriter_lru_maxpages` to 500-1000 for more aggressive cleaning
- Increase `bgwriter_lru_multiplier` to 4.0-6.0 to stay ahead of allocations
- Set `bgwriter_flush_after = 128` (32KB) to control writeback batching
- Decrease `bgwriter_delay` to 100ms for more frequent small writes
- Tune `vm.dirty_ratio` and `vm.dirty_background_ratio` in `/etc/sysctl.conf`

#### Very high-write OLTP with large shared_buffers

**Problem**: High-write OLTP workloads with large shared buffer caches need aggressive background cleaning.

**Recommendations**:
- Increase `bgwriter_lru_maxpages` to 500-2000 based on buffer cache size
- Increase `bgwriter_lru_multiplier` to 5.0-8.0 for very aggressive cleaning
- Decrease `bgwriter_delay` to 50-100ms for frequent operation
- Set `bgwriter_flush_after = 256` (64KB) for efficient writeback
- Monitor `pg_stat_bgwriter` for cleaning effectiveness

### Monitoring and Validation

Monitor these metrics to validate bgwriter tuning:

- `pg_stat_bgwriter.buffers_clean`: Buffers cleaned by bgwriter
- `pg_stat_bgwriter.buffers_backend`: Buffers cleaned by backends (should be low)
- `pg_stat_bgwriter.maxwritten_clean`: Times bgwriter hit `bgwriter_lru_maxpages` limit
- `pg_stat_bgwriter.buffers_alloc`: Total buffer allocations

The bgwriter should handle most buffer cleaning, with backends only cleaning buffers when absolutely necessary for new allocations.

## Source References

- [[raw/postgres-12/src/backend/utils/misc/guc.c]] — GUC definitions for `bgwriter_delay`, `bgwriter_lru_maxpages`, `bgwriter_lru_multiplier`, `bgwriter_flush_after`
- [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c]] — bgwriter LRU scan and buffer allocation logic
- [[raw/postgres-12/src/backend/postmaster/bgwriter.c]] — bgwriter main loop and hibernation