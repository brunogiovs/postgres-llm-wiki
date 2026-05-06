---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: gpt-5 2026-05-06T18:16:24Z
---

# Corruption log entries

## Question

In PostgreSQL 12, review the "Corruption log entries" catalog. Using the pinned PostgreSQL 12 source checkout, list backend, bundled-contrib, and core data-directory tool output messages that can indicate persistent database, index, WAL, relation-map, replication-state, or table-storage corruption. Include the relevant core data-directory tools reviewed here (`pg_checksums`, `pg_controldata`, `pg_ctl`, and `pg_resetwal`). For each message or tightly related message family, explain the condition and give a confidence number from 0 to 100% that persistent database contents are corrupted.

## Answer

Assumption: "PostgreSQL 12" means the local checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`. The confidence values below are triage estimates for persistent database corruption; PostgreSQL does not encode such percentages in the source.

Reviewed scope: source-visible messages in `raw/postgres-12/src/backend/`, `raw/postgres-12/contrib/`, and the core data-directory tools `pg_checksums`, `pg_controldata`, `pg_ctl`, and `pg_resetwal`, searched for `ERRCODE_DATA_CORRUPTED`, `ERRCODE_INDEX_CORRUPTED`, and corruption/checksum/invalid-page WAL strings. Localized `.po` files, frontend dump-archive corruption, network protocol/user-input decoding, and generic client-memory messages are excluded unless noted.

### Critical Page And Storage Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 100% | `page verification failed, calculated checksum %u but expected %u` | A data page read from disk did not match its page checksum when checksums were enabled; `PageIsVerified` reports the mismatch before deciding whether the page can be accepted. | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIsVerified]] |
| 95% | `invalid page in block %u of relation %s` | `ReadBuffer_common` or relation-storage copy read a relation block whose page failed `PageIsVerified`; all-zero pages are allowed by the verifier, so this points at non-zero invalid page contents or checksum failure. | [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common]], [[raw/postgres-12/src/backend/catalog/storage.c#RelationCopyStorage]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIsVerified]] |
| 100% | `invalid page in block %u of relation %s; zeroing out page` | The same invalid-page path is reached, but PostgreSQL zeros the damaged block because the read mode or `zero_damaged_pages` permits that. | [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common]] |
| 90% | `could not read block %u in file "%s": read only %d of %d bytes` | The storage manager got a short read for a relation block. Outside recovery or zero-damaged-page handling, `mdread` reports this as `ERRCODE_DATA_CORRUPTED`. | [[raw/postgres-12/src/backend/storage/smgr/md.c#mdread]] |
| 95% | `corrupted page pointers: lower = %u, upper = %u, special = %u` | Page header bounds fail consistency checks before page modification or compaction; these checks guard against spreading damage while moving tuple data. | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageAddItemExtended]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageRepairFragmentation]] |
| 95% | `corrupted line pointer: %u` | A line pointer offset falls outside the tuple storage area during page defragmentation. | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageRepairFragmentation]] |
| 95% | `corrupted line pointer: offset = %u, size = %u` | Index-page tuple deletion or replacement found a line pointer whose offset/size does not fit inside the page tuple area. | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIndexTupleDelete]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIndexTupleOverwrite]] |
| 95% | `corrupted item lengths: total %u, available space %u` | The total aligned item length on a page exceeds the available tuple space, which is a page-layout inconsistency. | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageRepairFragmentation]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIndexMultiDelete]] |
| 85% | `pg_largeobject entry for OID %u, page %d has invalid data field size %d` | Large-object storage found a `pg_largeobject.data` field outside the valid chunk-size range. | [[raw/postgres-12/src/backend/storage/large_object/inv_api.c#getdatafield]] |

### Heap And MVCC Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 85% | `found multixact %u from before relminmxid %u` | Tuple-freezing code found an XMAX multixact older than the relation's minimum multixact horizon. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]] |
| 80% | `multixact %u from before cutoff %u found to be still running` | A multixact old enough to be below the cutoff is still considered running, which violates the freezing assumptions. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]] |
| 85% | `found update xid %u from before relfrozenxid %u` | A tuple update XID is older than the relation's frozen XID boundary. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]] |
| 85% | `found xmin %u from before relfrozenxid %u` | A tuple xmin predates the relation's frozen XID boundary during freeze preparation. | [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 80% | `uncommitted xmin %u from before xid cutoff %u needs to be frozen` | A tuple xmin that should be safely freezable is not known committed. | [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 80% | `found xmax %u from before relfrozenxid %u` | A tuple xmax predates the relation's frozen XID boundary. | [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 80% | `cannot freeze committed update xid %u` / `cannot freeze committed xmax %u` | Freeze code found a committed update/delete XID where removing it would be unsafe. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]], [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 75% | `found update xid %u from before xid cutoff %u` | A retained update XID is older than the cutoff, contradicting the tuple-freezing path's expectations. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]] |
| 75% | `found xmax %u (infomask 0x%04x) not frozen, not multi, not normal` | Tuple xmax bits do not describe a normal, multi, invalid, or frozen state. | [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 85% | `failed to find parent tuple for heap-only tuple at (%u,%u) in table "%s"` | HOT-chain processing could not find the root tuple for a heap-only tuple while building or validating index entries. | [[raw/postgres-12/src/backend/access/heap/heapam_handler.c#heapam_index_build_range_scan]], [[raw/postgres-12/src/backend/access/heap/heapam_handler.c#heapam_index_validate_scan]] |

### Index Access Method Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 95% | `index "%s" is not a btree` | The B-tree metapage does not have B-tree flags or magic. | [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_getmeta]] |
| 90% | `version mismatch in index "%s": file version %d, current version %d, minimal supported version %d` | The B-tree metapage version is outside the supported range. | [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_getmeta]] |
| 95% | `index "%s" contains unexpected zero page at block %u` | A freshly read B-tree, hash, or GiST index page is all-zero where the access method expects a valid page. | [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_checkpage]], [[raw/postgres-12/src/backend/access/hash/hashutil.c#_hash_checkpage]], [[raw/postgres-12/src/backend/access/gist/gistutil.c#gistcheckpage]] |
| 95% | `index "%s" contains corrupted page at block %u` | B-tree, hash, GiST, or `pgstattuple` hash inspection found an index page with an invalid special area or page-type metadata. | [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_checkpage]], [[raw/postgres-12/src/backend/access/hash/hashutil.c#_hash_checkpage]], [[raw/postgres-12/src/backend/access/gist/gistutil.c#gistcheckpage]], [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstathashindex]] |
| 95% | `index "%s" is not a hash index` / `index "%s" has wrong hash version` | Hash-index metapage magic or version does not match the access method. | [[raw/postgres-12/src/backend/access/hash/hashutil.c#_hash_checkpage]] |
| 90% | `unexpected page type 0x%04X in HASH index "%s" block %u` | `pgstattuple` hash-index inspection saw a hash page type outside the valid hash page classes. | [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstathashindex]] |
| 90% | `index table contains corrupted page` / `invalid magic number for metadata` / `invalid version for metadata` | `pageinspect` hash-page inspection found invalid hash page layout, metapage magic, or metapage version in a raw page value. | [[raw/postgres-12/contrib/pageinspect/hashfuncs.c#verify_hash_page]] |
| 85% | `corrupted BRIN index: inconsistent range map` | BRIN reverse-map navigation found a repeated or out-of-range tuple pointer. | [[raw/postgres-12/src/backend/access/brin/brin_revmap.c#brinGetTupleForHeapBlock]] |
| 90% | `unexpected page type 0x%04X in BRIN index "%s" block %u` | BRIN reverse-map extension found a non-regular/non-empty page where it expected a regular page. | [[raw/postgres-12/src/backend/access/brin/brin_revmap.c#revmap_physical_extend]] |

### Pageinspect Heap Raw-Page Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 70% | `number of attributes in tuple header is greater than number of attributes in tuple descriptor` | `pageinspect` tuple-data splitting found a heap tuple header that names more attributes than the relation descriptor. With `tuple_data_split()` fed from `heap_page_items(get_raw_page(...))`, that can indicate heap tuple or catalog/descriptor inconsistency; with hand-written arguments it can also be caller misuse. | [[raw/postgres-12/contrib/pageinspect/heapfuncs.c#tuple_data_split_internal]] |
| 75% | `first byte of varlena attribute is incorrect for attribute %d` / `unexpected end of tuple data` / `end of tuple reached without looking at all its data` | `pageinspect` could not walk raw tuple data according to the relation's attribute layout: a varlena header was invalid, an attribute overran the tuple data, or bytes remained after all attributes were decoded. | [[raw/postgres-12/contrib/pageinspect/heapfuncs.c#tuple_data_split_internal]] |
| 35% | `illegal character '%c' in t_bits string` / `argument of t_bits is null...` / `unexpected length of t_bits %u, expected %d` / `t_bits string is expected to be NULL...` | These are `pageinspect` tuple-split input-consistency failures around the null bitmap. They can accompany a corrupt tuple inspection workflow, but by themselves are often inconsistent function arguments rather than persistent storage corruption. | [[raw/postgres-12/contrib/pageinspect/heapfuncs.c#text_to_bits]], [[raw/postgres-12/contrib/pageinspect/heapfuncs.c#tuple_data_split]] |

### Amcheck B-Tree Verification Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 90% | `index "%s" lacks a main relation fork` | `amcheck` opened the index relation but the main fork file was absent. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_index_check_internal]] |
| 95% | `index "%s" has no valid pages on level below %u or first level` | `amcheck` could not find a valid page on the next expected B-tree level. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_check_every_level]] |
| 95% | `downlink or sibling link points to deleted block in index "%s"` | A readonly parent/sibling traversal reached a page already marked deleted. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_check_level_from_leftmost]] |
| 95% | `block %u fell off the end of index "%s"` | Traversal encountered an ignorable page that is also marked rightmost. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_check_level_from_leftmost]] |
| 95% | `block %u is not leftmost in index "%s"` / `block %u is not true root in index "%s"` | The page reached from the expected leftmost/root path lacks the required leftmost/root flag. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_check_level_from_leftmost]] |
| 95% | `left link/right link pair in index "%s" not in agreement` | Adjacent B-tree page sibling links disagree in readonly verification. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_check_level_from_leftmost]] |
| 95% | `leftmost down link for level points to block in index "%s" whose level is not one level down` | A downlink points to a child page at the wrong B-tree level. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_check_level_from_leftmost]] |
| 95% | `circular link chain found in block %u of index "%s"` | B-tree sibling traversal detected a loop. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_check_level_from_leftmost]] |
| 90% | `wrong number of high key index tuple attributes in index "%s"` / `wrong number of index tuple attributes in index "%s"` | `amcheck` found tuple attribute counts inconsistent with B-tree tuple rules. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_target_page_check]] |
| 90% | `index tuple size does not equal lp_len in index "%s"` | A B-tree tuple's internal size disagrees with its line-pointer length; the source hint says this could be a torn page problem. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_target_page_check]] |
| 90% | `could not find tuple using search from root page in index "%s"` | A leaf tuple cannot be found by descending from the root during readonly root-descent verification. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_target_page_check]] |
| 90% | `index row size %zu exceeds maximum for index "%s"` | A B-tree index tuple exceeds the size limit for that page/version. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_target_page_check]] |
| 95% | `high key invariant violated for index "%s"` | A tuple violates the page high-key bound. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_target_page_check]] |
| 95% | `item order invariant violated for index "%s"` | Items on a B-tree page are not in strict logical order. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_target_page_check]] |
| 95% | `cross page item order invariant violated for index "%s"` | The last item on a page is not ordered before the first available item on the right sibling. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_target_page_check]] |
| 95% | `downlink to deleted page found in index "%s"` / `down-link lower bound invariant violated for index "%s"` | Parent-to-child B-tree checks found a deleted child or a child tuple below the parent's lower bound. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_downlink_check]] |
| 90% | `leaf index block lacks downlink in index "%s"` / `internal index block lacks downlink in index "%s"` | Readonly heapallindexed verification found a page whose parent downlink is missing after accounting for interrupted split/deletion cases. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_downlink_missing_check]] |
| 95% | `heap tuple (%u,%u) from table "%s" lacks matching index tuple within index "%s"` | Heapallindexed verification found a heap tuple that should have a matching B-tree index tuple but does not. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_tuple_present_callback]] |
| 90% | `external varlena datum in tuple that references heap row (%u,%u) in index "%s"` | A B-tree index tuple contains an external varlena datum, which should not appear in an index tuple ready for insertion. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#bt_normalize_tuple]] |
| 95% | `invalid meta page found at block %u in index "%s"` / `index "%s" meta page is corrupt` | A B-tree metapage appears at the wrong block, or block 0 lacks valid B-tree metapage flags/magic. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#palloc_btree_page]] |
| 90% | `version mismatch in index "%s": file version %d, current version %d, minimum supported version %d` | `amcheck` found a B-tree metapage version outside the supported range. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#palloc_btree_page]] |
| 95% | `invalid leaf page level %u for block %u in index "%s"` / `invalid internal page level 0 for block %u in index "%s"` | B-tree page type and level metadata are inconsistent. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#palloc_btree_page]] |
| 95% | `Number of items on block %u of index "%s" exceeds MaxIndexTuplesPerPage (%u)` | A B-tree page reports more line pointers than the maximum possible. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#palloc_btree_page]] |
| 95% | `internal block %u in index "%s" lacks high key and/or at least one downlink` / `non-rightmost leaf block %u in index "%s" lacks high key item` | Required B-tree structural items are missing. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#palloc_btree_page]] |
| 90% | `internal page block %u in index "%s" is half-dead` / `internal page block %u in index "%s" has garbage items` | B-tree internal page flags are in states that PostgreSQL 12 treats as corruption. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#palloc_btree_page]] |
| 95% | `line pointer points past end of tuple space in index "%s"` / `invalid line pointer storage in index "%s"` | B-tree page line-pointer validation found out-of-bounds or invalid storage metadata. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#PageGetItemIdCareful]] |
| 90% | `block %u or its right sibling block or child block in index "%s" contains non-pivot tuple that lacks a heap TID` | A non-pivot B-tree tuple lacks the heap TID that should identify the heap row. | [[raw/postgres-12/contrib/amcheck/verify_nbtree.c#BTreeTupleGetHeapTIDCareful]] |

### WAL, Control File, And Recovery Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 95% | `incorrect checksum in control file` | `ReadControlFile` recalculated the `pg_control` CRC and it did not match the stored CRC. | [[raw/postgres-12/src/backend/access/transam/xlog.c#ReadControlFile]] |
| 90% | `could not read file "global/pg_control": read %d of %zu` | The server read a short `pg_control` file and reports `ERRCODE_DATA_CORRUPTED`. | [[raw/postgres-12/src/backend/access/transam/xlog.c#ReadControlFile]] |
| 85% | `invalid record length at %X/%X: wanted %u, got %u` | WAL record-header validation found a record length inconsistent with the expected amount of WAL data. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#ValidXLogRecordHeader]] |
| 90% | `record with incorrect prev-link %X/%X at %X/%X` | WAL record-header validation found a previous-record link that does not match the reader's expected LSN chain. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#ValidXLogRecordHeader]] |
| 95% | `incorrect resource manager data checksum in record at %X/%X` | WAL record CRC validation failed. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#ValidXLogRecord]] |
| 85% | `invalid magic number %04X in log segment %s, offset %u` | A WAL page header has the wrong magic number for PostgreSQL 12 WAL. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#XLogReaderValidatePageHeader]] |
| 85% | `record with invalid length at %X/%X` | WAL record decoding found a record body whose length fields are internally inconsistent. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#DecodeXLogRecord]] |
| 85% | `could not read from log segment %s, offset %u: read %d of %zu` | WAL reading got a short read from a segment while replay or WAL sender expected a complete WAL page/range. This can be WAL truncation, missing bytes, or a concurrently removed/recycled segment; the source marks the replay-reader path as `ERRCODE_DATA_CORRUPTED`. | [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogPageRead]], [[raw/postgres-12/src/backend/replication/walsender.c#XLogRead]] |
| 75% | `invalid record offset at %X/%X` / `contrecord is requested by %X/%X` / `there is no contrecord flag at %X/%X` / `invalid contrecord length %u at %X/%X` / `record length %u at %X/%X too long` | WAL record assembly found impossible record or continuation boundaries. This is strong evidence for malformed WAL at that LSN, though recovery can also encounter expected invalid records at the end of available WAL. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#XLogReadRecord]] |
| 80% | `invalid resource manager ID %u at %X/%X` / `invalid block_id %u at %X/%X` / backup-image header invariant messages / `invalid compressed image at %X/%X, block %d` | WAL record decoding found an impossible resource-manager ID, block-reference header, backup image shape, or compressed full-page image. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#ValidXLogRecordHeader]], [[raw/postgres-12/src/backend/access/transam/xlogreader.c#DecodeXLogRecord]], [[raw/postgres-12/src/backend/access/transam/xlogreader.c#RestoreBlockImage]] |
| 70% | `invalid info bits %04X in log segment %s, offset %u` / `unexpected pageaddr %X/%X in log segment %s, offset %u` / `out-of-sequence timeline ID %u (after %u) in log segment %s, offset %u` / `WAL file is from different database system...` | WAL page-header validation found metadata inconsistent with the requested WAL stream. These can indicate WAL-file corruption, but the "different database system" variants can also mean the wrong WAL file or incompatible archive was supplied. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#XLogReaderValidatePageHeader]] |
| 85% | `invalid length of primary checkpoint record` / `invalid length of checkpoint record` | Startup checkpoint record parsing found a checkpoint record with the wrong total length. | [[raw/postgres-12/src/backend/access/transam/xlog.c#ReadCheckpointRecord]] |
| 95% | `page %u of relation %s is uninitialized` / `page %u of relation %s does not exist` followed by `WAL contains references to invalid pages` | Recovery tracked WAL references to invalid pages; unresolved entries are logged and then trigger PANIC. | [[raw/postgres-12/src/backend/access/transam/xlogutils.c#report_invalid_page]], [[raw/postgres-12/src/backend/access/transam/xlogutils.c#XLogCheckInvalidPages]] |
| 50% | `database system was interrupted while in recovery at %s` with hint `This probably means that some data is corrupted...` | Startup noticed a previous interruption during recovery. The hint warns of possible corruption, but the state itself is not a direct page or checksum failure. | [[raw/postgres-12/src/backend/access/transam/xlog.c#StartupXLOG]] |
| 45% | `database system was interrupted while in recovery at log time %s` with hint `some data might be corrupted...` | Similar to the previous entry, but the source text itself says "might"; treat as possible rather than proven corruption. | [[raw/postgres-12/src/backend/access/transam/xlog.c#StartupXLOG]] |
| 35% | `backup_label contains data inconsistent with control file` with hint `the backup is corrupted...` | This is strong evidence that the backup being restored is inconsistent, but it does not prove the original source cluster is corrupt. | [[raw/postgres-12/src/backend/access/transam/xlog.c#StartupXLOG]] |
| 30% | `the standby was promoted during online backup` with hint `the backup being taken is corrupt and should not be used` | The online backup artifact is unsafe because promotion happened during the backup; it is not evidence that the live database contents were already corrupt. | [[raw/postgres-12/src/backend/replication/basebackup.c#sendDir]], [[raw/postgres-12/src/backend/access/transam/xlog.c#do_pg_stop_backup]] |

### Backup, Checksums, And Data-Directory Tool Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 100% | `checksum verification failed in file "%s", block %d: calculated %X but expected %X` | Base backup checksum validation reread a failed block once and then counted the mismatch as a real checksum failure. | [[raw/postgres-12/src/backend/replication/basebackup.c#sendFile]] |
| 100% | `further checksum verification failures in file "%s" will not be reported` | Base backup hit the per-file reporting cap after real checksum failures were counted. | [[raw/postgres-12/src/backend/replication/basebackup.c#sendFile]] |
| 100% | `file "%s" has a total of %d checksum verification failure` / `file "%s" has a total of %d checksum verification failures` | Base backup completed a file with one or more checksum failures. | [[raw/postgres-12/src/backend/replication/basebackup.c#sendFile]] |
| 100% | `%s total checksum verification failures` / `checksum verification failure during base backup` | The base backup operation accumulated checksum failures and ends with `ERRCODE_DATA_CORRUPTED`. | [[raw/postgres-12/src/backend/replication/basebackup.c#perform_base_backup]] |
| 55% | `could not verify checksum in file "%s", block %d: read buffer size %d and page size %d differ` | Base backup cannot perform block-level checksum validation when the read size is not a multiple of `BLCKSZ`; this is suspicious for relation files, but the message itself is "could not verify", not "failed". | [[raw/postgres-12/src/backend/replication/basebackup.c#sendFile]] |
| 100% | `checksum verification failed in file "%s", block %u: calculated checksum %X but block contains %X` | Offline `pg_checksums --check` found a page checksum mismatch in a data-directory file. | [[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#scan_file]] |
| 90% | `could not read block %u in file "%s": read %d of %d` from `pg_checksums` | Offline checksum verification read a partial page from a data-directory file. | [[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#scan_file]] |
| 95% | `WARNING: Calculated CRC checksum does not match value stored in file...` from `pg_controldata` | `pg_controldata` detected a `pg_control` CRC mismatch and warns that the file may be corrupt or incompatible with the tool's expected layout. | [[raw/postgres-12/src/bin/pg_controldata/pg_controldata.c#main]] |
| 90% | `WARNING: invalid WAL segment size... The file is corrupt...` from `pg_controldata` | `pg_controldata` found a WAL segment size in `pg_control` outside the valid power-of-two range. | [[raw/postgres-12/src/bin/pg_controldata/pg_controldata.c#main]] |
| 95% | `%s: control file appears to be corrupt` from `pg_ctl` | `pg_ctl` could not validate the control-file CRC while reading the cluster state. | [[raw/postgres-12/src/bin/pg_ctl/pg_ctl.c#get_control_dbstate]] |
| 95% | `pg_control exists but has invalid CRC; proceed with caution` from `pg_resetwal` | `pg_resetwal` could read a same-version `pg_control`, but its CRC did not validate; the tool keeps the values while treating them as guessed. | [[raw/postgres-12/src/bin/pg_resetwal/pg_resetwal.c#ReadControlFile]] |
| 90% | `pg_control exists but is broken or wrong version; ignoring it` from `pg_resetwal` | `pg_resetwal` could open `pg_control`, but the file was too malformed or wrong-version for the normal read path, so it falls back to guessed control values. | [[raw/postgres-12/src/bin/pg_resetwal/pg_resetwal.c#ReadControlFile]] |
| 90% | `pg_control specifies invalid WAL segment size (%d byte[s]); proceed with caution` from `pg_resetwal` | `pg_resetwal` read `pg_control` but found an invalid WAL segment size, which is a control-file consistency failure. | [[raw/postgres-12/src/bin/pg_resetwal/pg_resetwal.c#ReadControlFile]] |

### Two-Phase, Replication, And Logical Decoding State

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 85% | `incorrect size of file "%s": %zu byte(s)` | Two-phase state file length is outside the valid bounds. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 85% | `incorrect alignment of CRC offset for file "%s"` | Two-phase state file length puts the stored CRC at an invalid alignment. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 90% | `invalid magic number stored in file "%s"` | Two-phase state file has the wrong magic number. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 85% | `invalid size stored in file "%s"` | Two-phase state file header length disagrees with the actual file size. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 95% | `calculated CRC checksum does not match value stored in file "%s"` | Two-phase state file CRC validation failed. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 90% | `corrupted two-phase state file for transaction %u` | Recovered two-phase file header transaction ID does not match the expected transaction. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ProcessTwoPhaseBuffer]] |
| 60% | `corrupted two-phase state in memory for transaction %u` | The same transaction-ID mismatch was found in memory rather than in a file; it is serious, but not direct evidence of persistent storage damage. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ProcessTwoPhaseBuffer]] |
| 80% | `could not read file "%s": read %d of %zu` from logical replication origin, replication slot, or snapbuild state restore | A persistent logical-replication state file was shorter than the fixed-size header or expected payload being restored. The same generic text appears in several restore paths, so the file path and surrounding context identify whether it is origin, slot, or snapbuild state. | [[raw/postgres-12/src/backend/replication/logical/origin.c#StartupReplicationOrigin]], [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]], [[raw/postgres-12/src/backend/replication/logical/snapbuild.c#SnapBuildRestore]] |
| 75% | `replication checkpoint has wrong magic %u instead of %u` | Logical replication origin checkpoint file magic is wrong. | [[raw/postgres-12/src/backend/replication/logical/origin.c#StartupReplicationOrigin]] |
| 80% | `replication slot checkpoint has wrong checksum %u, expected %u` | Logical replication origin checkpoint CRC is wrong. | [[raw/postgres-12/src/backend/replication/logical/origin.c#StartupReplicationOrigin]] |
| 75% | `replication slot file "%s" has wrong magic number: %u instead of %u` | Replication slot state file magic is wrong. | [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]] |
| 70% | `replication slot file "%s" has unsupported version %u` | Replication slot state file version is unsupported for this build. | [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]] |
| 80% | `replication slot file "%s" has corrupted length %u` | Replication slot state file length field is not the expected on-disk size. | [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]] |
| 85% | `checksum mismatch for replication slot file "%s": is %u, should be %u` | Replication slot state file checksum failed. | [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]] |
| 75% | `snapbuild state file "%s" has wrong magic number: %u instead of %u` | Logical decoding snapshot-builder state file magic is wrong. | [[raw/postgres-12/src/backend/replication/logical/snapbuild.c#SnapBuildRestore]] |
| 70% | `snapbuild state file "%s" has unsupported version: %u instead of %u` | Snapshot-builder state file version is unsupported for this build. | [[raw/postgres-12/src/backend/replication/logical/snapbuild.c#SnapBuildRestore]] |
| 85% | `checksum mismatch for snapbuild state file "%s": is %u, should be %u` | Snapshot-builder state file checksum failed. | [[raw/postgres-12/src/backend/replication/logical/snapbuild.c#SnapBuildRestore]] |

### Relation Map And Auxiliary State

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 90% | `could not read file "%s": read %d of %zu` from relation mapping load | Relation mapping file had a short read while loading shared or per-database relation mappings. | [[raw/postgres-12/src/backend/utils/cache/relmapper.c#load_relmap_file]] |
| 95% | `relation mapping file "%s" contains invalid data` | Relation mapping file magic or mapping count is invalid. | [[raw/postgres-12/src/backend/utils/cache/relmapper.c#load_relmap_file]] |
| 95% | `relation mapping file "%s" contains incorrect checksum` | Relation mapping file CRC validation failed. | [[raw/postgres-12/src/backend/utils/cache/relmapper.c#load_relmap_file]] |
| 35% | `corrupted statistics file "%s"` | The stats collector detected a malformed statistics file; PostgreSQL can discard/rebuild stats, so this is not strong evidence of table/index corruption. | [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_read_statsfiles]] |
| 30% | `autoprewarm block dump file is corrupted at line %d` | `pg_prewarm`'s autoprewarm dump file is malformed; it affects prewarm state, not table contents. | [[raw/postgres-12/contrib/pg_prewarm/autoprewarm.c#apw_load_buffers]] |
| 20% | `fixing corrupt FSM block %u, relation %u/%u/%u` | Free-space-map page contents were inconsistent and PostgreSQL is repairing the FSM page; FSM corruption can hurt space reuse but is not heap tuple corruption by itself. | [[raw/postgres-12/src/backend/storage/freespace/fsmpage.c#fsm_search_avail]] |

### Internal State Messages With Low Database-Corruption Confidence

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 35% | `SMgrRelation hashtable corrupted` | Storage-manager in-memory hashtable state is inconsistent; serious backend state corruption, but not direct evidence of persistent relation-file corruption. | [[raw/postgres-12/src/backend/storage/smgr/smgr.c#smgrclose]] |
| 30% | `local buffer hash table corrupted` | Local buffer hash state is inconsistent. Temporary/local buffer state may be damaged, but persistent database contents are not proven corrupt. | [[raw/postgres-12/src/backend/storage/buffer/localbuf.c#LocalBufferAlloc]] |
| 35% | `shared buffer hash table corrupted` | Shared buffer lookup state is inconsistent. It is severe shared-memory corruption, but not itself a page checksum or on-disk layout failure. | [[raw/postgres-12/src/backend/storage/buffer/buf_table.c#BufTableDelete]] |
| 25% | `lock table corrupted` / `proclock table corrupted` / `locallock table corrupted` | Lock-manager tables are inconsistent; this can force backend or cluster failure, but does not directly say that stored data files are corrupt. | [[raw/postgres-12/src/backend/storage/lmgr/lock.c#LockAcquireExtended]], [[raw/postgres-12/src/backend/storage/lmgr/lock.c#CleanUpLock]], [[raw/postgres-12/src/backend/storage/lmgr/lock.c#RemoveLocalLock]] |
| 25% | `hash table "%s" corrupted` | Generic dynamic hash table corruption; persistent data corruption depends on which in-memory hash table was affected. | [[raw/postgres-12/src/backend/utils/hash/dynahash.c#hash_corrupted]] |
| 20% | `doubly linked list is corrupted` | Generic in-memory list invariant failure, not direct on-disk evidence. | [[raw/postgres-12/src/backend/lib/ilist.c#dlist_check]] |
| 20% | `free page manager btree is corrupt` | Dynamic shared memory allocator metadata is corrupt; it is allocator state, not a PostgreSQL relation index. | [[raw/postgres-12/src/backend/utils/mmgr/freepage.c#FreePageManagerGetInternal]] |
| 25% | `dynamic shared memory control segment is corrupt` / `invalid magic number in dynamic shared memory segment` | DSM control/segment metadata is invalid. This points to shared-memory state, not table/index files. | [[raw/postgres-12/src/backend/storage/ipc/dsm.c#dsm_postmaster_startup]], [[raw/postgres-12/src/backend/access/transam/parallel.c#ParallelWorkerMain]] |

## Context Reviewed

- Navigation and bookkeeping: `wiki/versions.md`, `wiki/index.md`, the last 20 `wiki/log.md` entries through `scripts/recent_log --limit 20`, and `wiki/v12/index.md`.
- Context pack: `.wiki-runtime/context/postgres-12/manifest.md`, `include-deps.txt`, `compile_commands.json`, and targeted `scripts/source_deps --version 12` checks for storage, WAL reader, logical replication origin, pageinspect, `pg_checksums`, and `pg_resetwal` files.
- Source search envelope: `scripts/source_lookup --version 12 --symbol ERRCODE_DATA_CORRUPTED --limit 200`, `scripts/source_lookup --version 12 --symbol ERRCODE_INDEX_CORRUPTED --limit 200`, and `rg` over `raw/postgres-12/src/backend`, `raw/postgres-12/contrib`, `raw/postgres-12/src/common`, `raw/postgres-12/src/bin/pg_checksums`, `raw/postgres-12/src/bin/pg_controldata`, `raw/postgres-12/src/bin/pg_ctl`, and `raw/postgres-12/src/bin/pg_resetwal`.
- Tests checked: checksum-corruption coverage in [[raw/postgres-12/src/bin/pg_checksums/t/002_actions.pl]], control-file warnings in [[raw/postgres-12/src/bin/pg_controldata/t/001_pg_controldata.pl]], `pg_resetwal` corrupt-control handling in [[raw/postgres-12/src/bin/pg_resetwal/t/002_corrupted.pl]], backend basebackup checksum reporting through the `pg_basebackup` TAP test in [[raw/postgres-12/src/bin/pg_basebackup/t/010_pg_basebackup.pl]], amcheck regression coverage in [[raw/postgres-12/contrib/amcheck/expected/check_btree.out]], pageinspect normal-path coverage in [[raw/postgres-12/contrib/pageinspect/expected/page.out]], and invalid-page recovery coverage in [[raw/postgres-12/src/test/recovery/t/015_promotion_pages.pl]].

## Evidence Map

- Page and storage messages map to page verification, buffer reads, storage-manager reads, relation-storage copy, large-object chunks, and FSM repair in `bufpage.c`, `bufmgr.c`, `md.c`, `storage.c`, `inv_api.c`, and `fsmpage.c`.
- Heap and MVCC messages map to tuple freezing and HOT-chain index-build/validation paths in `heapam.c` and `heapam_handler.c`.
- Index messages map to B-tree, hash, GiST, BRIN, amcheck, pgstattuple, and pageinspect source paths under `src/backend/access/` and `contrib/`.
- WAL, control-file, and recovery messages map to WAL record/page validation, checkpoint/control-file loading, invalid-page tracking, and backup interruption checks in `xlogreader.c`, `xlog.c`, and `xlogutils.c`.
- Tool-output messages map to the checked core data-directory tools: `pg_checksums`, `pg_controldata`, `pg_ctl`, and `pg_resetwal`.
- Replication-state messages map to two-phase state, logical replication origin state, replication slot state, and logical decoding snapbuild state restore paths.
- Low-confidence internal-state messages map to shared/local buffer, smgr, lock-manager, dynahash, ilist, freepage, DSM, and parallel-worker invariant checks; they are included because the source text says "corrupt/corrupted", but the explanations keep them separate from direct persistent relation-file evidence.

## Open Questions

No unresolved source-evidence gaps were found for the catalog entries above. The confidence percentages remain reviewer triage judgments, not PostgreSQL source-defined probabilities.

## Source References

- Source pin and context pack: [[raw/postgres-12/]], `.wiki-runtime/context/postgres-12/manifest.md`
- Context checks used for this review: `.wiki-runtime/context/postgres-12/include-deps.txt` through `scripts/source_deps --version 12 --includes ...`
- Source searches used for this review: `scripts/source_lookup --version 12 --symbol ...`, `rg` over `raw/postgres-12/src/backend`, `raw/postgres-12/contrib`, `raw/postgres-12/src/bin/pg_checksums`, `raw/postgres-12/src/bin/pg_controldata`, `raw/postgres-12/src/bin/pg_ctl`, and `raw/postgres-12/src/bin/pg_resetwal`
