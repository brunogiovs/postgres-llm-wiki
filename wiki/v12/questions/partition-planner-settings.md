---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

## Question

In PostgreSQL 12, what settings or configs are used by query planner for partition tables, summarized by inheritance and declarative partitioning?

## Answer

PostgreSQL 12 supports two partitioning methods: inheritance-based partitioning (traditional) and declarative partitioning (introduced in PostgreSQL 10). The query planner uses different settings for each method to optimize partition-related operations.

### Inheritance Partitioning (Traditional)

Inheritance partitioning relies on table inheritance with CHECK constraints. The primary planner setting is `constraint_exclusion`.

- **`constraint_exclusion`** (enum, default: `partition`):
  - Controls the planner's use of CHECK constraints to optimize queries on inheritance hierarchies.
  - Values: `on` (examine all tables), `off` (never examine), `partition` (examine only inheritance children and UNION ALL subqueries).
  - Default `partition` enables constraint exclusion for inheritance-based partitioning.
  - Context: `PGC_USERSET` - can be changed per-session without restart.
  - Usage: Allows planner to skip scanning child tables where CHECK constraints contradict query conditions.
  - Citation: [[raw/postgres-12/src/backend/utils/misc/guc.c#constraint_exclusion]]

### Declarative Partitioning

Declarative partitioning uses `PARTITION BY` syntax and has dedicated partition pruning and optimization features.

- **`enable_partition_pruning`** (boolean, default: `on`):
  - Enables plan-time and run-time partition pruning for declarative partitioned tables.
  - Allows planner to eliminate partitions from query plans based on partition bounds and query conditions.
  - Context: `PGC_USERSET` - can be changed per-session without restart.
  - Usage: Compares partition bounds to query conditions to determine which partitions must be scanned.
  - Citation: [[raw/postgres-12/src/backend/utils/misc/guc.c#enable_partition_pruning]]

- **`enable_partitionwise_join`** (boolean, default: `off`):
  - Enables partitionwise join optimization for declarative partitioned tables.
  - Allows joins between partitioned tables to be performed by joining matching partitions.
  - Requirements: Join conditions must include all partition keys with matching data types and partition sets.
  - Context: `PGC_USERSET` - can be changed per-session without restart.
  - Usage: Can significantly increase planning CPU/memory usage; disabled by default due to performance cost.
  - Citation: [[raw/postgres-12/src/backend/utils/misc/guc.c#enable_partitionwise_join]]

- **`enable_partitionwise_aggregate`** (boolean, default: `off`):
  - Enables partitionwise aggregation and grouping for declarative partitioned tables.
  - Allows aggregation/grouping to be performed separately for each partition.
  - Supports full partitionwise aggregation when GROUP BY includes all partition keys, or partial otherwise.
  - Context: `PGC_USERSET` - can be changed per-session without restart.
  - Usage: Can significantly increase planning CPU/memory usage; disabled by default due to performance cost.
  - Citation: [[raw/postgres-12/src/backend/utils/misc/guc.c#enable_partitionwise_aggregate]]

### Summary by Partitioning Type

| Setting | Inheritance | Declarative | Default | Context |
|---------|-------------|-------------|---------|---------|
| `constraint_exclusion` | Primary pruning mechanism | Not applicable | `partition` | Session |
| `enable_partition_pruning` | Not applicable | Primary pruning mechanism | `on` | Session |
| `enable_partitionwise_join` | Not applicable | Join optimization | `off` | Session |
| `enable_partitionwise_aggregate` | Not applicable | Aggregation optimization | `off` | Session |

### Additional Notes

- Inheritance partitioning predates declarative partitioning and uses constraint exclusion for optimization.
- Declarative partitioning introduced dedicated pruning and partitionwise operations with specific GUCs.
- Partitionwise operations are disabled by default due to planning overhead.
- All settings are session-scoped and do not require restart to change.
- For production use, consider `statement_timeout` and `lock_timeout` when testing partition-related queries.

## Open Questions

- Are there any interactions between `constraint_exclusion` and declarative partitioning settings?
- How do partitionwise operations interact with parallel query execution?