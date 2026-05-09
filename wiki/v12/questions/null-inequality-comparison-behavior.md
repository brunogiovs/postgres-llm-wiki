---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: claude-opus-4-7 2026-05-08T20:00:00Z
---

# NULL Inequality Comparison Behavior

The query `SELECT * FROM users WHERE status_id <> 1` will not return any rows where `status_id` is NULL.

In PostgreSQL, any comparison involving NULL yields NULL, not TRUE or FALSE. Since `NULL <> 1` evaluates to NULL, and the WHERE clause treats NULL as falsy (equivalent to FALSE), rows with `status_id = NULL` are excluded from the result set.

## Context Reviewed

- PostgreSQL version 12 source code, pinned to commit `45b88269a353ad93744772791feb6d01bc7e1e42`.
- Expression evaluation in the executor, specifically qualification handling in WHERE clauses.
- SQL standard behavior for NULL comparisons.

## Evidence Map

- WHERE clause qualification treats NULL results as FALSE, implemented in `EEOP_QUAL` opcode in the expression interpreter [[raw/postgres-12/src/backend/executor/execExprInterp.c#EEOP_QUAL]].
- Comparison operators like `<>` are evaluated as function calls, but the overall expression result is NULL if any operand is NULL, leading to exclusion in WHERE.

## Open Questions

None.