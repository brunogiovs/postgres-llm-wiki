---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Corruption log entries (unverified)

## Question

In PostgreSQL 12, create a list of all possible log entries that could be related to database corruption, explain each error and give a confidence number from 0 to 100% that the database is corrupted.

## Answer

This page catalogs PostgreSQL 12 log messages that indicate potential database corruption. Each entry includes the log message, explanation, and a confidence score (0-100%) representing how likely the database is corrupted when this message appears. Scores are based on the error's context, severity, and whether it definitively proves corruption versus other possible causes.

### Page Header and Structure Corruption

1. **"corrupted page pointers: lower = %u, upper = %u, special = %u"**
   - **Explanation**: Page header contains invalid offset values for the start of tuple data (lower), end of tuple data (upper), or special space. This indicates physical corruption of the page structure.
   - **Confidence**: 95% - Page headers are fundamental and corruption here almost always indicates disk/storage corruption.
   - **Source**: [[raw/postgres-12/src/backend/storage/page/bufpage.c]]

2. **"corrupted line pointer: offset = %u, size = %u"**
   - **Explanation**: A line pointer in the page header references invalid tuple data offsets or sizes, indicating corruption in the page's tuple directory.
   - **Confidence**: 90% - Line pointers are critical for data access and corruption suggests physical damage.
   - **Source**: [[raw/postgres-12/src/backend/storage/page/bufpage.c]]

3. **"corrupted item lengths: total %u, available space %u"**
   - **Explanation**: The total length of tuples on the page doesn't match the available space calculation, indicating data corruption.
   - **Confidence**: 85% - Space calculations are fundamental and mismatches strongly suggest corruption.
   - **Source**: [[raw/postgres-12/src/backend/storage/page/bufpage.c]]

4. **"invalid page in block %u of relation %s"**
   - **Explanation**: A database page contains invalid data that cannot be interpreted as a valid PostgreSQL page.
   - **Confidence**: 95% - Invalid page content is a clear sign of corruption.
   - **Source**: [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c]]

5. **"invalid page in block %u of relation %s; zeroing out page"**
   - **Explanation**: Same as above, but the system is attempting recovery by zeroing the corrupted page.
   - **Confidence**: 100% - The system has detected definitive corruption and is taking emergency action.
   - **Source**: [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c]]

### Checksum Failures

6. **"page verification failed, calculated checksum %u but expected %u"**
   - **Explanation**: Data page checksum doesn't match the expected value, indicating the page data has been corrupted since it was written.
   - **Confidence**: 100% - Checksum failures definitively prove data corruption has occurred.
   - **Source**: [[raw/postgres-12/src/backend/storage/page/bufpage.c]]

7. **"checksum verification failure during base backup"**
   - **Explanation**: During pg_basebackup, a page checksum failed verification, indicating corruption in the source database.
   - **Confidence**: 100% - Checksum verification during backup confirms corruption exists.
   - **Source**: [[raw/postgres-12/src/backend/replication/basebackup.c]]

8. **"file \"%s\" has a total of %d checksum verification failure"**
   - **Explanation**: Multiple checksum failures detected in a single file during backup or verification.
   - **Confidence**: 100% - Multiple checksum failures confirm widespread corruption.
   - **Source**: [[raw/postgres-12/src/backend/replication/basebackup.c]]

### Index Corruption

9. **"index \"%s\" contains corrupted page at block %u"**
   - **Explanation**: An index page contains invalid data structure or content.
   - **Confidence**: 90% - Index corruption affects data access but may not indicate heap corruption.
   - **Source**: [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c]]

10. **"invalid meta page found at block %u in index \"%s\""**
    - **Explanation**: The index metapage (block 0) contains invalid metadata.
    - **Confidence**: 95% - Metapage corruption severely impacts index functionality.
    - **Source**: [[raw/postgres-12/contrib/amcheck/verify_nbtree.c]]

11. **"version mismatch in index \"%s\": file version %d, expected %d"**
    - **Explanation**: Index file version doesn't match expected PostgreSQL version.
    - **Confidence**: 80% - Could be corruption or incompatible index, but corruption is likely.
    - **Source**: [[raw/postgres-12/contrib/amcheck/verify_nbtree.c]]

12. **"index \"%s\" lacks a main relation fork"**
    - **Explanation**: Index is missing its main data fork file.
    - **Confidence**: 70% - Could be administrative error, but suggests corruption.
    - **Source**: [[raw/postgres-12/contrib/amcheck/verify_nbtree.c]]

13. **"circular link chain found in block %u of index \"%s\""**
    - **Explanation**: Index pages form a circular reference chain, indicating structural corruption.
    - **Confidence**: 95% - Circular references are definitive corruption.
    - **Source**: [[raw/postgres-12/contrib/amcheck/verify_nbtree.c]]

14. **"high key invariant violated for index \"%s\""**
    - **Explanation**: Index high keys don't follow expected ordering rules.
    - **Confidence**: 90% - Invariant violations indicate corruption.
    - **Source**: [[raw/postgres-12/contrib/amcheck/verify_nbtree.c]]

15. **"item order invariant violated for index \"%s\""**
    - **Explanation**: Index tuples are not in correct sorted order.
    - **Confidence**: 95% - Ordering violations are clear corruption signs.
    - **Source**: [[raw/postgres-12/contrib/amcheck/verify_nbtree.c]]

### WAL and Transaction State Corruption

16. **"corrupted two-phase state file for transaction %u"**
    - **Explanation**: Two-phase commit state file contains invalid data.
    - **Confidence**: 85% - Affects transaction durability but may be recoverable.
    - **Source**: [[raw/postgres-12/src/backend/access/transam/twophase.c]]

17. **"invalid magic number stored in file \"%s\""**
    - **Explanation**: File header magic number is incorrect, indicating corruption.
    - **Confidence**: 90% - Magic number corruption suggests file damage.
    - **Source**: [[raw/postgres-12/src/backend/access/transam/twophase.c]]

18. **"calculated CRC checksum does not match value stored in file \"%s\""**
    - **Explanation**: File CRC checksum doesn't match stored value.
    - **Confidence**: 95% - CRC mismatch confirms file corruption.
    - **Source**: [[raw/postgres-12/src/backend/access/transam/twophase.c]]

### Replication and Logical Decoding Corruption

19. **"replication slot file \"%s\" has corrupted length %u"**
    - **Explanation**: Replication slot file has invalid length field.
    - **Confidence**: 80% - Affects replication but may not indicate data corruption.
    - **Source**: [[raw/postgres-12/src/backend/replication/slot.c]]

20. **"replication slot file \"%s\" has wrong magic number: %u instead of %u"**
    - **Explanation**: Replication slot file has incorrect magic number.
    - **Confidence**: 75% - File format corruption affecting replication.
    - **Source**: [[raw/postgres-12/src/backend/replication/slot.c]]

21. **"snapbuild state file \"%s\" has wrong magic number: %u instead of %u"**
    - **Explanation**: Logical replication snapshot build state file has invalid magic number.
    - **Confidence**: 70% - Affects logical replication state, corruption likely.
    - **Source**: [[raw/postgres-12/src/backend/replication/logical/snapbuild.c]]

22. **"checksum mismatch for snapbuild state file \"%s\": is %u, should be %u"**
    - **Explanation**: Logical replication state file checksum is invalid.
    - **Confidence**: 85% - Checksum failure indicates corruption.
    - **Source**: [[raw/postgres-12/src/backend/replication/logical/snapbuild.c]]

### Storage and File System Corruption

23. **"could not read block %u in file \"%s\": read only %d of %d bytes"**
    - **Explanation**: Failed to read expected number of bytes from a database file.
    - **Confidence**: 90% - I/O errors or file truncation indicate corruption.
    - **Source**: [[raw/postgres-12/src/backend/storage/smgr/md.c]]

24. **"SMgrRelation hashtable corrupted"**
    - **Explanation**: Internal storage manager relation hash table is corrupted.
    - **Confidence**: 60% - Memory or internal state corruption, may not affect persistent data.
    - **Source**: [[raw/postgres-12/src/backend/storage/smgr/smgr.c]]

### Heap and Table Corruption

25. **"found multixact %u from before relminmxid %u"**
    - **Explanation**: Multi-transaction ID is older than relation's minimum, indicating corruption.
    - **Confidence**: 85% - MultiXact state corruption affecting visibility.
    - **Source**: [[raw/postgres-12/src/backend/access/heap/heapam.c]]

26. **"found update xid %u from before relfrozenxid %u"**
    - **Explanation**: Transaction ID in tuple is older than relation freeze point.
    - **Confidence**: 80% - Indicates potential MVCC or freeze corruption.
    - **Source**: [[raw/postgres-12/src/backend/access/heap/heapam.c]]

27. **"pg_largeobject entry for OID %u, page %d has invalid data field size %d"**
    - **Explanation**: Large object page has invalid data size.
    - **Confidence**: 75% - Affects large objects but may not indicate widespread corruption.
    - **Source**: [[raw/postgres-12/src/backend/storage/large_object/inv_api.c]]

### Memory and Internal State Corruption

28. **"local buffer hash table corrupted"**
    - **Explanation**: Local buffer management hash table is corrupted.
    - **Confidence**: 50% - Internal memory corruption, may not affect persistent data.
    - **Source**: [[raw/postgres-12/src/backend/storage/buffer/localbuf.c]]

29. **"shared buffer hash table corrupted"**
    - **Explanation**: Shared buffer management hash table is corrupted.
    - **Confidence**: 60% - Internal memory corruption affecting buffer management.
    - **Source**: [[raw/postgres-12/src/backend/storage/buffer/buf_table.c]]

30. **"lock table corrupted"**
    - **Explanation**: Lock management table is corrupted.
    - **Confidence**: 40% - Internal state corruption, may be transient.
    - **Source**: [[raw/postgres-12/src/backend/storage/lmgr/lock.c]]

31. **"proclock table corrupted"**
    - **Explanation**: Process lock table is corrupted.
    - **Confidence**: 45% - Internal concurrency control corruption.
    - **Source**: [[raw/postgres-12/src/backend/storage/lmgr/lock.c]]

### BRIN Index Corruption

32. **"corrupted BRIN index: inconsistent range map"**
    - **Explanation**: BRIN index range map contains inconsistent data.
    - **Confidence**: 85% - BRIN structure corruption affecting index validity.
    - **Source**: [[raw/postgres-12/src/backend/access/brin/brin_revmap.c]]

33. **"unexpected page type 0x%04X in BRIN index \"%s\" block %u"**
    - **Explanation**: BRIN index page has unexpected type.
    - **Confidence**: 90% - Invalid page types indicate corruption.
    - **Source**: [[raw/postgres-12/src/backend/access/brin/brin_revmap.c]]

### Hash Index Corruption

34. **"index \"%s\" contains corrupted page at block %u"**
    - **Explanation**: Hash index page contains invalid data.
    - **Confidence**: 90% - Hash index structural corruption.
    - **Source**: [[raw/postgres-12/src/backend/access/hash/hashutil.c]]

35. **"unexpected page type 0x%04X in HASH index \"%s\" block %u"**
    - **Explanation**: Hash index page has unexpected type.
    - **Confidence**: 90% - Invalid page types indicate corruption.
    - **Source**: [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c]]

### GIN Index Corruption

36. **"index \"%s\" contains unexpected zero page at block %u"**
    - **Explanation**: GIN index contains an unexpected empty page.
    - **Confidence**: 80% - May indicate corruption or incomplete operation.
    - **Source**: [[raw/postgres-12/src/backend/access/gist/gistutil.c]]

37. **"index \"%s\" contains corrupted page at block %u"**
    - **Explanation**: GIN index page contains invalid data.
    - **Confidence**: 90% - GIN index corruption.
    - **Source**: [[raw/postgres-12/src/backend/access/gist/gistutil.c]]

### GiST Index Corruption

38. **"index \"%s\" contains unexpected zero page at block %u"**
    - **Explanation**: GiST index contains an unexpected empty page.
    - **Confidence**: 80% - May indicate corruption or incomplete operation.
    - **Source**: [[raw/postgres-12/src/backend/access/gist/gistutil.c]]

39. **"index \"%s\" contains corrupted page at block %u"**
    - **Explanation**: GiST index page contains invalid data.
    - **Confidence**: 90% - GiST index corruption.
    - **Source**: [[raw/postgres-12/src/backend/access/gist/gistutil.c]]

## Source References

All corruption log messages and explanations are sourced from the PostgreSQL 12 source code checkout pinned to commit `45b88269a353ad93744772791feb6d01bc7e1e42`. The following files were analyzed for error messages:

- [[raw/postgres-12/src/backend/storage/page/bufpage.c]] - Page header and checksum validation
- [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c]] - Buffer management and page validation
- [[raw/postgres-12/src/backend/replication/basebackup.c]] - Base backup checksum verification
- [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c]] - B-tree index corruption detection
- [[raw/postgres-12/contrib/amcheck/verify_nbtree.c]] - Index verification and corruption checking
- [[raw/postgres-12/src/backend/access/transam/twophase.c]] - Two-phase commit state validation
- [[raw/postgres-12/src/backend/replication/slot.c]] - Replication slot file validation
- [[raw/postgres-12/src/backend/replication/logical/snapbuild.c]] - Logical replication state validation
- [[raw/postgres-12/src/backend/storage/smgr/md.c]] - Storage manager file I/O
- [[raw/postgres-12/src/backend/storage/smgr/smgr.c]] - Storage manager internal state
- [[raw/postgres-12/src/backend/access/heap/heapam.c]] - Heap tuple and visibility validation
- [[raw/postgres-12/src/backend/storage/large_object/inv_api.c]] - Large object validation
- [[raw/postgres-12/src/backend/storage/buffer/localbuf.c]] - Local buffer management
- [[raw/postgres-12/src/backend/storage/buffer/buf_table.c]] - Shared buffer hash table
- [[raw/postgres-12/src/backend/storage/lmgr/lock.c]] - Lock management tables
- [[raw/postgres-12/src/backend/access/brin/brin_revmap.c]] - BRIN index validation
- [[raw/postgres-12/src/backend/access/hash/hashutil.c]] - Hash index validation
- [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c]] - Index statistics and validation
- [[raw/postgres-12/src/backend/access/gist/gistutil.c]] - GIN/GiST index validation

## Notes

- Confidence scores are estimates based on the error's context and typical causes
- Some messages may appear due to transient conditions rather than persistent corruption
- Checksum failures (100% confidence) are the most definitive indicators of corruption
- Index corruption messages generally indicate index-specific issues rather than heap corruption
- Memory/internal state corruption messages have lower confidence as they may be transient
- Always verify corruption claims against the pinned source commit for the specific version
