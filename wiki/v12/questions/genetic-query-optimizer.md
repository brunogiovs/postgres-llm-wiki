---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

## Question

In PostgreSQL 12, how does the genetic query optimizer work? What are its pros and cons, and how can I tell if it is causing overhead in query execution? Please include examples of SQL queries that would trigger GEQO.

## Answer

The Genetic Query Optimizer (GEQO) in PostgreSQL 12 is an alternative to the standard dynamic programming-based join order search algorithm. It uses genetic algorithms to explore the join order search space more efficiently for complex queries with many tables.

### How GEQO Works

GEQO models the query optimization problem as a Traveling Salesman Problem (TSP), where:
- Each relation to be joined represents a "city"
- The join order represents the "tour" through these cities
- The cost of executing the join order represents the "distance" to minimize

The algorithm maintains a "population" of candidate join orders (chromosomes) and evolves them through generations using genetic operators:

1. **Initialization**: Randomly generates an initial population of join orders
2. **Evaluation**: Each join order is evaluated by actually planning the query and measuring its execution cost
3. **Selection**: Fitter individuals (lower cost) are selected with higher probability for reproduction
4. **Crossover**: Selected individuals exchange genetic material to create offspring
5. **Mutation**: Random changes are applied to maintain diversity
6. **Replacement**: Less fit individuals are replaced by new offspring

The process repeats for a fixed number of generations or until convergence.

### Key Parameters

GEQO behavior is controlled by several GUC parameters:

- `geqo_threshold` (default: 12): Minimum number of FROM items before GEQO is used
- `geqo_effort` (default: 5): Controls population size and generations (1-10 scale)
- `geqo_pool_size`: Number of individuals in population (default: 10 * geqo_effort)
- `geqo_generations`: Number of generations (default: same as pool_size)
- `geqo_selection_bias` (default: 2.0): Selection pressure (1.5-2.0)
- `geqo_seed`: Random seed for reproducible results

### When GEQO Is Used

GEQO is enabled by default (`geqo = on`) and activates when:
```sql
enable_geqo = true AND number_of_relations >= geqo_threshold
```

For queries with fewer than `geqo_threshold` relations (default 12), PostgreSQL uses the standard dynamic programming algorithm.

### SQL Examples That Trigger GEQO

Queries with 12 or more tables in the FROM clause will trigger GEQO by default. Here are examples:

**Simple 12-table join (triggers GEQO):**
```sql
SELECT /* wiki_geqo_12_table_example */ *
FROM t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12
WHERE t1.id = t2.id AND t2.id = t3.id AND t3.id = t4.id
  AND t4.id = t5.id AND t5.id = t6.id AND t6.id = t7.id
  AND t7.id = t8.id AND t8.id = t9.id AND t9.id = t10.id
  AND t10.id = t11.id AND t11.id = t12.id;
```

**Complex query with subqueries and CTEs (counted as separate relations):**
```sql
WITH cte1 AS (SELECT * FROM table1),
     cte2 AS (SELECT * FROM table2)
SELECT /* wiki_geqo_complex_cte_example */ *
FROM cte1 c1
JOIN cte2 c2 ON c1.id = c2.id
JOIN table3 t3 ON c2.id = t3.id
JOIN table4 t4 ON t3.id = t4.id
JOIN table5 t5 ON t4.id = t5.id
JOIN table6 t6 ON t5.id = t6.id
JOIN table7 t7 ON t6.id = t7.id
JOIN table8 t8 ON t7.id = t8.id
JOIN table9 t9 ON t8.id = t9.id
JOIN table10 t10 ON t9.id = t10.id
JOIN table11 t11 ON t10.id = t11.id
JOIN table12 t12 ON t11.id = t12.id;
```

**Inheritance partitioning with many child tables:**
```sql
SELECT /* wiki_geqo_inheritance_example */ *
FROM parent_table p
JOIN child1 c1 ON p.id = c1.id
JOIN child2 c2 ON p.id = c2.id
JOIN child3 c3 ON p.id = c3.id
JOIN child4 c4 ON p.id = c4.id
JOIN child5 c5 ON p.id = c5.id
JOIN child6 c6 ON p.id = c6.id
JOIN child7 c7 ON p.id = c7.id
JOIN child8 c8 ON p.id = c8.id
JOIN child9 c9 ON p.id = c9.id
JOIN child10 c10 ON p.id = c10.id
JOIN child11 c11 ON p.id = c11.id
JOIN child12 c12 ON p.id = c12.id;
```

**Query that stays below threshold (uses standard optimizer):**
```sql
SELECT /* wiki_standard_optimizer_example */ *
FROM t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11
WHERE t1.id = t2.id AND t2.id = t3.id AND t3.id = t4.id
  AND t4.id = t5.id AND t5.id = t6.id AND t6.id = t7.id
  AND t7.id = t8.id AND t8.id = t9.id AND t9.id = t10.id
  AND t10.id = t11.id;
```

### Pros

1. **Scalability**: Handles complex queries with many joins more efficiently than exhaustive search
2. **Approximation Quality**: Often finds good (though not always optimal) join orders
3. **Memory Efficiency**: Uses bounded memory regardless of query complexity
4. **Termination Guarantee**: Always completes within predictable time bounds

### Cons

1. **Suboptimal Plans**: May not find the truly optimal join order
2. **Planning Overhead**: Evaluates multiple candidate plans, increasing planning time
3. **Randomness**: Results can vary between executions (unless seeded)
4. **Parameter Tuning**: Performance depends on correct parameter settings
5. **Limited Scope**: Only optimizes join order, not other query transformations

### Detecting GEQO Overhead

To determine if GEQO is causing overhead:

1. **Check if GEQO is being used**:
   ```sql
   EXPLAIN (VERBOSE, COSTS) SELECT ...;
   ```
   Look for "GEQO" in the execution plan or check query planning time.

2. **Monitor planning time**:
   ```sql
   SET log_min_duration_statement = 0;
   -- Look for lines like: LOG:  GEQO with 15 generations, population size 100
   ```

3. **Compare with standard optimizer**:
   ```sql
   SET geqo = off;
   EXPLAIN ANALYZE SELECT ...;
   SET geqo = on;
   EXPLAIN ANALYZE SELECT ...;
   ```

4. **Check pg_stat_statements** for planning vs execution time ratios:
   ```sql
   SELECT query, total_plan_time, total_exec_time
   FROM pg_stat_statements
   WHERE total_plan_time > total_exec_time * 0.1; -- Planning > 10% of execution
   ```

### Mitigating GEQO Overhead

If GEQO is causing excessive planning overhead:

1. **Increase threshold**:
   ```sql
   SET geqo_threshold = 20; -- Only use GEQO for very complex queries
   ```

2. **Reduce effort** (trading planning time for potentially worse plans):
   ```sql
   SET geqo_effort = 3; -- Smaller population, fewer generations
   ```

3. **Disable GEQO entirely** for problematic queries:
   ```sql
   SET geqo = off;
   ```

4. **Use query-specific plans** with PREPARE:
   ```sql
   PREPARE complex_query AS SELECT ...;
   EXECUTE complex_query; -- Reuses cached plan
   ```

### Implementation Details

The GEQO implementation uses several recombination operators:
- **Edge Recombination Crossover (ERX)**: Default, preserves edges from parents
- **Partially Mapped Crossover (PMX)**
- **Cycle Crossover (CX)**
- **Position-based Crossover (PX)**
- **Order Crossover (OX1/OX2)**

Fitness evaluation involves constructing actual query plans and measuring their costs, making GEQO more expensive per evaluation than heuristic approaches but more thorough.

## Source References

- [[raw/postgres-12/src/backend/optimizer/geqo/geqo_main.c#geqo]] - GEQO main algorithm implementation
- [[raw/postgres-12/src/backend/optimizer/geqo/geqo_eval.c#geqo_eval]] - Fitness evaluation function
- [[raw/postgres-12/src/include/optimizer/geqo.h]] - GEQO header with parameter definitions
- [[raw/postgres-12/src/backend/optimizer/path/allpaths.c#make_rel_from_joinlist]] - GEQO activation logic
- [[raw/postgres-12/src/backend/utils/misc/guc.c]] - GUC parameter definitions for geqo_threshold, enable_geqo

## Open Questions

- How does GEQO performance compare with modern PostgreSQL versions?
- Are there specific query patterns where GEQO consistently underperforms?
- What are the trade-offs of different recombination operators?