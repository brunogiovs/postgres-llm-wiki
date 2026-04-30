---
type: concept
scope: shared
verified_against:
  18: 6cb307251c5c6261286c1566496920976640108e
primary_example_version: 18
---

# TupleTableSlot

## Definition

A `TupleTableSlot` is the executor's container for a tuple-like row as it moves through plan nodes.

## Why It Exists

Executor nodes need a common way to return rows without forcing every node to expose the same physical tuple representation. A slot carries a tuple descriptor, values, null flags, tuple identity fields, memory context, and slot-operation callbacks. Different slot implementations can materialize, copy, deform, or clear tuple contents as needed.

## Where It Appears

- [[v18/subsystems/executor]] names `TupleTableSlot` as the row container returned by executor node calls.
- [[v18/code-paths/simple-select-query]] returns slots from scan nodes through `ExecProcNode`.
- [[v18/code-paths/insert-path]], [[v18/code-paths/update-path]], and [[v18/code-paths/delete-path]] use slots for source rows, old rows, new rows, and optional `RETURNING` rows.

## Related Structures and Functions

- `TupleTableSlot` in `src/include/executor/tuptable.h`
- `TupleTableSlotOps`
- `ExecProcNode`
- `SeqNext`
- `ExecStoreBufferHeapTuple`
- `table_scan_getnextslot`

## Interactions With Other Concepts

- [[shared/concepts/plan-and-planstate|PlanState]] has result slots and expression contexts that refer to slots.
- [[shared/concepts/executor-state|EState]] tracks executor slots in `es_tupleTable`.
- [[shared/concepts/modifytable|ModifyTable]] uses slots heavily when building or applying DML tuples.
- [[shared/concepts/querydesc|QueryDesc]] receives tuple descriptors after executor startup.

## Version Notes

Verified against PostgreSQL 18 at commit `6cb307251c5c6261286c1566496920976640108e`.

## Source References

- `raw/postgres-18/src/include/executor/tuptable.h:TupleTableSlot`
- `raw/postgres-18/src/include/executor/tuptable.h:TupleTableSlotOps`
- `raw/postgres-18/src/include/executor/executor.h:ExecProcNode`
- `raw/postgres-18/src/backend/executor/execTuples.c`
- `raw/postgres-18/src/backend/executor/nodeSeqscan.c:SeqNext`

## Open Questions

- Which slot implementations should be explained first: virtual, heap, minimal, or buffer heap slots?
- Where should tuple deformation and materialization be traced in detail?
