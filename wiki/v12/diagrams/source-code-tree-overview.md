---
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified_by_agent: Cline 2026-05-03T12:40:00Z
---

# PostgreSQL 12 Source Code Tree Overview

This page provides a visual diagram and explanations of the main code areas in the PostgreSQL 12 source tree (`raw/postgres-12@45b88269a353ad93744772791feb6d01bc7e1e42`). The diagram helps humans navigate the directory structure, highlighting key subsystems.

## Diagram

```mermaid
mindmap
  root((PG 12))
    config((Build config))
    contrib((Extensions))
    doc((Documentation))
    src((Source))
      backend((Core server))
        access((Access methods))
        bootstrap((Bootstrap / initdb))
        catalog((System catalogs))
        commands((SQL commands DDL/DML))
        executor((Query executor))
        foreign((Foreign data))
        lib((Utility libraries))
        main((main.c))
        nodes((Plan nodes))
        optimizer((Planner/optimizer))
        parser((SQL parser))
        partitioning((Partitioning))
        postmaster((Postmaster & processes))
        regex((Regex))
        replication((Replication))
        rewrite((Rule rewriting))
        storage((Storage: buffer, WAL, lmgr))
        statistics((Statistics))
        tcop((TCOP postgres.c))
        tsearch((Full text))
        utils((Utils, hash, arrays))
      bin((Client binaries: psql, pg_dump))
      common((Common code))
      fe_utils((Frontend utils))
      include((Headers))
      interfaces((libpq, ecpg))
      pl((PL/pgSQL, plperl))
      port((Portability))
      test((Tests))
```

## Main Code Areas

### src/backend/ - Core Server Logic

- **access/**: Table and index access methods (heap, btree, gin, gist, hash, brin, spgist). `[[raw/postgres-12/src/backend/access/heap/README|heap/README]]`, `[[raw/postgres-12/src/backend/access/nbtree/README|nbtree/README]]`, `[[raw/postgres-12/src/backend/access/gin/README|gin/README]]`, `[[raw/postgres-12/src/backend/access/heap/README.HOT|heap/README.HOT]]`.
- **bootstrap/**: Cluster initialization (initdb backend). `[[raw/postgres-12/src/backend/bootstrap/bootstrap.c|bootstrap.c]]`.
- Key: boot_parse, boot_yyparse for initial catalogs.
- **catalog/**: System catalogs (pg_class, pg_attribute, etc.). `[[raw/postgres-12/src/backend/catalog/heap.c|heap.c]]`, `[[raw/postgres-12/src/backend/catalog/pg_class.h|pg_class.h]]`, `[[raw/postgres-12/src/backend/catalog/indexing.c|indexing.c]]`.
- **commands/**: SQL command processing (DDL/DML: CREATE TABLE, ANALYZE, VACUUM). `[[raw/postgres-12/src/backend/commands/tablecmds.c|tablecmds.c]]`, `[[raw/postgres-12/src/backend/commands/analyze.c|analyze.c]]`, `[[raw/postgres-12/src/backend/commands/vacuum.c|vacuum.c]]`.
- **executor/**: Query execution engine. `[[raw/postgres-12/src/backend/executor/execMain.c|execMain.c:ExecutorRun]]`, `[[raw/postgres-12/src/backend/executor/README|executor/README]]`, `[[raw/postgres-12/src/backend/executor/nodeSeqscan.c|nodeSeqscan.c]]`.
- **nodes/**: Node types for parse trees, plans, PlanState. `[[raw/postgres-12/src/backend/nodes/README|nodes/README]]`, `[[raw/postgres-12/src/backend/nodes/parsenodes.h|parsenodes.h]]`, `[[raw/postgres-12/src/backend/nodes/plannodes.h|plannodes.h]]`.
- **optimizer/**: Query planning/optimizer. `[[raw/postgres-12/src/backend/optimizer/README|optimizer/README]]`, `[[raw/postgres-12/src/backend/optimizer/plan/planner.c|planner.c]]`, `[[raw/postgres-12/src/backend/optimizer/path/allpaths.c|allpaths.c]]`.
- **parser/**: SQL parsing (gram.y bison). `[[raw/postgres-12/src/backend/parser/README|parser/README]]`, `[[raw/postgres-12/src/backend/parser/gram.y|gram.y]]`, `[[raw/postgres-12/src/backend/parser/scan.l|scan.l]]`.
- **postmaster/**: Postmaster & backend processes (autovacuum, bgwriter, etc.). `[[raw/postgres-12/src/backend/postmaster/postmaster.c|postmaster.c]]`, `[[raw/postgres-12/src/backend/postmaster/autovacuum.c|autovacuum.c]]`.
- **storage/**: Storage manager (buffers, WAL, lock manager, SMGR). `[[raw/postgres-12/src/backend/storage/buffer/README|buffer/README]]`, `[[raw/postgres-12/src/backend/storage/buffer/bufmgr.c|bufmgr.c]]`, `[[raw/postgres-12/src/backend/storage/wal/xlog.c|xlog.c]]`, `[[raw/postgres-12/src/backend/storage/lmgr/README|lmgr/README]]`.
- **tcop/**: TCOP (postgres.c query dispatcher). `[[raw/postgres-12/src/backend/tcop/postgres.c|postgres.c:exec_simple_query]]`, `[[raw/postgres-12/src/backend/tcop/dest.c|dest.c]]`.
- **utils/**: Utilities, data types, hash tables, arrays. `[[raw/postgres-12/src/backend/utils/adt/|adt/]]`, `[[raw/postgres-12/src/backend/utils/hash/|hash/]]`, `[[raw/postgres-12/src/backend/utils/resowner/README|resowner/README]]`.

### Other Areas

- **config/**: Autoconf build configuration.
- **contrib/**: Contributed extensions (pg_stat_statements, pgcrypto). `[[raw/postgres-12/contrib/README|contrib/README]]`, `[[raw/postgres-12/contrib/pg_stat_statements/README|pg_stat_statements/README]]`.
- **doc/**: Documentation sources.

- **src/bin/**: Client tools (psql, pg_dump, pg_restore). `[[raw/postgres-12/src/bin/psql/psql.c|psql.c]]`, `[[raw/postgres-12/src/bin/pg_dump/|pg_dump/]]`.
- **src/common/**: Shared code (base64, username, etc.). `[[raw/postgres-12/src/common/|common/]]`.
- **src/pl/**: Procedural languages (plpgsql, plperl, plpython). `[[raw/postgres-12/src/pl/plpgsql/src/pl_exec.c|pl_exec.c]]`, `[[raw/postgres-12/src/pl/plperl/README|plperl/README]]`.
- **src/interfaces/**: Client libraries (libpq, ecpg). `[[raw/postgres-12/src/interfaces/libpq/README|libpq/README]]`, `[[raw/postgres-12/src/interfaces/ecpg/README.dynSQL|ecpg/README.dynSQL]]`.
- **src/port/**: Platform portability. `[[raw/postgres-12/src/port/README|port/README]]`.
- **src/test/**: Regression/isolation tests. `[[raw/postgres-12/src/test/regress/README|regress/README]]`, `[[raw/postgres-12/src/test/isolation/README|isolation/README]]`.

## Verification

Structure confirmed via directory listings of `raw/postgres-12/` at pinned commit `45b88269a353ad93744772791feb6d01bc7e1e42`. Citations point to representative files/symbols.
