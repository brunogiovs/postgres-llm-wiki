---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: gpt-5 2026-05-06T18:36:31Z
---

# Corruption log entries with data checksums disabled

## Question

In PostgreSQL 12, for a cluster whose data checksums are disabled, list source-visible backend, bundled-contrib, and core data-directory tool output messages that can indicate persistent database, index, WAL, relation-map, replication-state, table-storage, or auxiliary on-disk state corruption. Explain each message or tightly related message family and give a confidence number from 0 to 100% that persistent database contents are corrupted.

## Answer

Assumption: "PostgreSQL 12" means the local checkout pinned to `45b88269a353ad93744772791feb6d01bc7e1e42`. The confidence values are triage estimates for persistent database corruption; PostgreSQL does not define these percentages in source.

Checksum-disabled scope: `data_checksums` is an internal preset GUC populated from `DataChecksumsEnabled()`, and `DataChecksumsEnabled()` returns true only when `ControlFile->data_checksum_version > 0` [[raw/postgres-12/src/backend/utils/misc/guc.c#ConfigureNamesBool]], [[raw/postgres-12/src/backend/access/transam/xlog.c#DataChecksumsEnabled]]. With checksums disabled, `PageIsVerified()` still validates basic page-header shape and accepts all-zero pages, but it does not compute or report a data-page checksum mismatch [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIsVerified]]. Likewise, base backup checksum verification is only enabled when `DataChecksumsEnabled()` is true, and `pg_checksums --check` exits with `data checksums are not enabled in cluster` when the control file has checksum version 0 [[raw/postgres-12/src/backend/replication/basebackup.c#sendFile]], [[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#main]].

Reviewed scope: source-visible messages in `raw/postgres-12/src/backend/`, `raw/postgres-12/contrib/`, `raw/postgres-12/src/common/controldata_utils.c`, and the core data-directory tools `pg_checksums`, `pg_controldata`, `pg_ctl`, and `pg_resetwal`. Localized `.po` files, client protocol/user-input decoding, pg_dump/archive messages, extension-specific user-data formats such as pgcrypto encrypted payloads, and messages that merely say a generic file operation failed are excluded unless the source marks the condition as corruption or a persistent-state invariant failure.

### Critical Page, Relation, And TOAST Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 95% | `invalid page in block %u of relation %s` | A relation block read from storage failed `PageIsVerified()` even without data checksums; in this scope the likely detector is an impossible page-header layout rather than checksum mismatch. | [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common]], [[raw/postgres-12/src/backend/catalog/storage.c#RelationCopyStorage]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIsVerified]] |
| 100% | `invalid page in block %u of relation %s; zeroing out page` | The same invalid-page path was reached, but PostgreSQL zeroed the damaged page because the read mode or damage-handling path allowed zeroing. | [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common]] |
| 90% | `could not read block %u in file "%s": read only %d of %d bytes` | The storage manager got a partial relation block at EOF where callers expected a full block; outside recovery or zero-damaged-page handling it reports `ERRCODE_DATA_CORRUPTED`. | [[raw/postgres-12/src/backend/storage/smgr/md.c#mdread]] |
| 45% | `unexpected data beyond EOF in block %u of relation %s` | Relation extension found a valid non-zero buffer where the code expected a zero-filled beyond-EOF page; the source hint names buggy kernels as a known cause, so this is related but not direct database-file corruption proof. | [[raw/postgres-12/src/backend/storage/buffer/bufmgr.c#ReadBuffer_common]] |
| 95% | `corrupted page pointers: lower = %u, upper = %u, special = %u` | Page header bounds fail consistency checks before page modification or compaction, which prevents following impossible tuple-space pointers. | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageAddItemExtended]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageRepairFragmentation]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIndexTupleDelete]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIndexMultiDelete]] |
| 95% | `corrupted line pointer: %u` / `corrupted line pointer: offset = %u, size = %u` | A line pointer is outside the valid tuple area or has impossible offset/size while a page is being repaired, compacted, or edited. | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageRepairFragmentation]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIndexTupleDelete]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIndexTupleOverwrite]] |
| 95% | `corrupted item lengths: total %u, available space %u` | The sum of aligned items on a page exceeds the available tuple space. | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageRepairFragmentation]], [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIndexMultiDelete]] |
| 90% | `found toasted toast chunk for toast value %u in %s` | TOAST fetch found a toast chunk that is itself stored as an extended/toasted datum, which the source says should never happen. | [[raw/postgres-12/src/backend/access/heap/tuptoaster.c#toast_fetch_datum]], [[raw/postgres-12/src/backend/access/heap/tuptoaster.c#toast_fetch_datum_slice]] |
| 90% | `unexpected chunk number %d...` / `unexpected chunk size %d...` / `missing chunk number %d for toast value %u in %s` | TOAST chunk order, count, or chunk length disagrees with the varlena toast pointer and expected chunking layout. | [[raw/postgres-12/src/backend/access/heap/tuptoaster.c#toast_fetch_datum]], [[raw/postgres-12/src/backend/access/heap/tuptoaster.c#toast_fetch_datum_slice]] |
| 85% | `compressed data is corrupted` | TOAST decompression failed while detoasting a compressed varlena datum. | [[raw/postgres-12/src/backend/access/heap/tuptoaster.c#toast_decompress_datum]], [[raw/postgres-12/src/backend/access/heap/tuptoaster.c#toast_decompress_datum_slice]] |
| 85% | `pg_largeobject entry for OID %u, page %d has invalid data field size %d` | Large-object storage found a `pg_largeobject.data` field outside the valid chunk-size range. | [[raw/postgres-12/src/backend/storage/large_object/inv_api.c#getdatafield]] |

### Heap, MVCC, And Visibility Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 85% | `found multixact %u from before relminmxid %u` | Tuple-freezing code found an XMAX multixact older than the relation's minimum multixact horizon. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]] |
| 80% | `multixact %u from before cutoff %u found to be still running` | A multixact old enough to be below the freeze cutoff is still considered running. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]] |
| 85% | `found update xid %u from before relfrozenxid %u` / `found xmin %u from before relfrozenxid %u` | Tuple transaction IDs predate the relation's frozen-XID boundary. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]], [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 80% | `uncommitted xmin %u from before xid cutoff %u needs to be frozen` | A tuple xmin that should be safely freezable is not known committed. | [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 80% | `found xmax %u from before relfrozenxid %u` | A tuple xmax predates the relation's frozen-XID boundary. | [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 80% | `cannot freeze committed update xid %u` / `cannot freeze committed xmax %u` | Freeze code found a committed update/delete XID where removing it would be unsafe. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]], [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 75% | `found update xid %u from before xid cutoff %u` | A retained update XID is older than the cutoff, contradicting the tuple-freezing path's expectations. | [[raw/postgres-12/src/backend/access/heap/heapam.c#FreezeMultiXactId]] |
| 75% | `found xmax %u (infomask 0x%04x) not frozen, not multi, not normal` | Tuple xmax bits do not describe a normal, multi, invalid, or frozen state. | [[raw/postgres-12/src/backend/access/heap/heapam.c#heap_prepare_freeze_tuple]] |
| 85% | `failed to find parent tuple for heap-only tuple at (%u,%u) in table "%s"` | HOT-chain processing could not find the root tuple for a heap-only tuple while building or validating index entries. | [[raw/postgres-12/src/backend/access/heap/heapam_handler.c#heapam_index_build_range_scan]], [[raw/postgres-12/src/backend/access/heap/heapam_handler.c#heapam_index_validate_scan]] |

### Index Access Method Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 95% | `index "%s" is not a btree` | The B-tree metapage does not have B-tree flags or magic. | [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_getmeta]], [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_getroot]] |
| 90% | `version mismatch in index "%s": file version %d, current version %d, minimal supported version %d` | The B-tree metapage version is outside the supported range. | [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_getmeta]], [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_getroot]] |
| 95% | `index "%s" contains unexpected zero page at block %u` | A freshly read B-tree or hash index page is all-zero where the access method expects a valid page. | [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_checkpage]], [[raw/postgres-12/src/backend/access/hash/hashutil.c#_hash_checkpage]] |
| 95% | `index "%s" contains corrupted page at block %u` | B-tree, hash, GiST, or `pgstattuple` hash inspection found invalid page special area or page-type metadata. | [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_checkpage]], [[raw/postgres-12/src/backend/access/hash/hashutil.c#_hash_checkpage]], [[raw/postgres-12/src/backend/access/gist/gistutil.c#gistcheckpage]], [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstathashindex]] |
| 85% | `index "%s" contains a half-dead internal page` | B-tree page deletion found a half-dead internal page left in the tree; the source logs `ERRCODE_INDEX_CORRUPTED` and hints to reindex. | [[raw/postgres-12/src/backend/access/nbtree/nbtpage.c#_bt_pagedel]] |
| 95% | `index "%s" is not a hash index` / `index "%s" has wrong hash version` | Hash-index metapage magic or version does not match the access method. | [[raw/postgres-12/src/backend/access/hash/hashutil.c#_hash_checkpage]] |
| 90% | `unexpected page type 0x%04X in HASH index "%s" block %u` | `pgstattuple` hash-index inspection saw a hash page type outside the valid hash page classes. | [[raw/postgres-12/contrib/pgstattuple/pgstatindex.c#pgstathashindex]] |
| 90% | `index table contains corrupted page` / `invalid magic number for metadata` / `invalid version for metadata` | `pageinspect` hash-page inspection found invalid hash page layout, metapage magic, or metapage version in a raw page value. | [[raw/postgres-12/contrib/pageinspect/hashfuncs.c#verify_hash_page]] |
| 85% | `corrupted BRIN index: inconsistent range map` | BRIN reverse-map navigation found a repeated or out-of-range tuple pointer. | [[raw/postgres-12/src/backend/access/brin/brin_revmap.c#brinGetTupleForHeapBlock]] |
| 90% | `unexpected page type 0x%04X in BRIN index "%s" block %u` | BRIN reverse-map extension found a non-regular/non-empty page where it expected a regular page. | [[raw/postgres-12/src/backend/access/brin/brin_revmap.c#revmap_physical_extend]] |
| 20% | `cannot reindex invalid index "%s.%s" concurrently, skipping` | `REINDEX ... CONCURRENTLY` skips an already-invalid toast index and uses `ERRCODE_INDEX_CORRUPTED`, but an invalid index can be a normal leftover from an interrupted concurrent index operation rather than storage corruption. | [[raw/postgres-12/src/backend/commands/indexcmds.c#ReindexRelationConcurrently]] |

### Pageinspect Heap Raw-Page Signals

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 70% | `number of attributes in tuple header is greater than number of attributes in tuple descriptor` | `pageinspect` tuple-data splitting found a heap tuple header that names more attributes than the relation descriptor; with `tuple_data_split()` fed from `heap_page_items(get_raw_page(...))`, this can indicate heap tuple or descriptor inconsistency. | [[raw/postgres-12/contrib/pageinspect/heapfuncs.c#tuple_data_split_internal]] |
| 75% | `first byte of varlena attribute is incorrect for attribute %d` / `unexpected end of tuple data` / `end of tuple reached without looking at all its data` | `pageinspect` could not walk raw tuple bytes according to the relation's attribute layout. | [[raw/postgres-12/contrib/pageinspect/heapfuncs.c#tuple_data_split_internal]] |
| 35% | `illegal character '%c' in t_bits string` / `argument of t_bits is null...` / `unexpected length of t_bits %u, expected %d` / `t_bits string is expected to be NULL...` | These are `pageinspect` tuple-split input-consistency failures around the null bitmap; they can accompany raw corrupt tuple inspection, but by themselves can be caller misuse. | [[raw/postgres-12/contrib/pageinspect/heapfuncs.c#text_to_bits]], [[raw/postgres-12/contrib/pageinspect/heapfuncs.c#tuple_data_split]] |

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
| 95% | `incorrect checksum in control file` | Server startup/control-file loading recalculated the `pg_control` CRC and it did not match the stored CRC. | [[raw/postgres-12/src/backend/access/transam/xlog.c#ReadControlFile]] |
| 90% | `could not read file "global/pg_control": read %d of %zu` | The server read a short `pg_control` file and reports `ERRCODE_DATA_CORRUPTED`. | [[raw/postgres-12/src/backend/access/transam/xlog.c#ReadControlFile]] |
| 85% | `invalid record length at %X/%X: wanted %u, got %u` | WAL record-header validation found a record length inconsistent with the expected amount of WAL data. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#ValidXLogRecordHeader]] |
| 90% | `record with incorrect prev-link %X/%X at %X/%X` | WAL record-header validation found a previous-record link that does not match the reader's expected LSN chain. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#ValidXLogRecordHeader]] |
| 95% | `incorrect resource manager data checksum in record at %X/%X` | WAL record CRC validation failed; this WAL checksum is independent of disabled data-page checksums. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#ValidXLogRecord]] |
| 85% | `invalid magic number %04X in log segment %s, offset %u` | A WAL page header has the wrong magic number for PostgreSQL 12 WAL. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#XLogReaderValidatePageHeader]] |
| 85% | `record with invalid length at %X/%X` | WAL record decoding found a record body whose length fields are internally inconsistent. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#DecodeXLogRecord]] |
| 85% | `could not read from log segment %s, offset %u: read %d of %zu` | WAL reading got a short read from a segment while replay or WAL sender expected a complete page/range. | [[raw/postgres-12/src/backend/access/transam/xlog.c#XLogPageRead]], [[raw/postgres-12/src/backend/replication/walsender.c#XLogRead]] |
| 75% | `invalid record offset at %X/%X` / `contrecord is requested by %X/%X` / `there is no contrecord flag at %X/%X` / `invalid contrecord length %u at %X/%X` / `record length %u at %X/%X too long` | WAL record assembly found impossible record or continuation boundaries; these are strong evidence for malformed WAL at that LSN, though expected end-of-WAL can also surface invalid-record text. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#XLogReadRecord]] |
| 80% | `invalid resource manager ID %u at %X/%X` / `invalid block_id %u at %X/%X` / backup-image header invariant messages / `invalid compressed image at %X/%X, block %d` | WAL record decoding found an impossible resource-manager ID, block-reference header, backup image shape, or compressed full-page image. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#ValidXLogRecordHeader]], [[raw/postgres-12/src/backend/access/transam/xlogreader.c#DecodeXLogRecord]], [[raw/postgres-12/src/backend/access/transam/xlogreader.c#RestoreBlockImage]] |
| 70% | `invalid info bits %04X in log segment %s, offset %u` / `unexpected pageaddr %X/%X in log segment %s, offset %u` / `out-of-sequence timeline ID %u...` / `WAL file is from different database system...` | WAL page-header validation found metadata inconsistent with the requested WAL stream; this may be WAL-file corruption or the wrong WAL source/archive. | [[raw/postgres-12/src/backend/access/transam/xlogreader.c#XLogReaderValidatePageHeader]] |
| 85% | `invalid length of primary checkpoint record` / `invalid length of checkpoint record` | Startup checkpoint record parsing found a checkpoint record with the wrong total length. | [[raw/postgres-12/src/backend/access/transam/xlog.c#ReadCheckpointRecord]] |
| 95% | `page %u of relation %s is uninitialized` / `page %u of relation %s does not exist` followed by `WAL contains references to invalid pages` | Recovery tracked WAL references to invalid relation pages; unresolved entries are logged and then trigger PANIC. | [[raw/postgres-12/src/backend/access/transam/xlogutils.c#report_invalid_page]], [[raw/postgres-12/src/backend/access/transam/xlogutils.c#XLogCheckInvalidPages]] |
| 50% | `database system was interrupted while in recovery at %s` with hint `This probably means that some data is corrupted...` | Startup noticed a previous interruption during recovery; the hint warns of possible corruption, but the state is not a direct page or WAL validation failure. | [[raw/postgres-12/src/backend/access/transam/xlog.c#StartupXLOG]] |
| 45% | `database system was interrupted while in recovery at log time %s` with hint `some data might be corrupted...` | Similar to the previous entry, and the source wording is explicitly probabilistic. | [[raw/postgres-12/src/backend/access/transam/xlog.c#StartupXLOG]] |
| 35% | `backup_label contains data inconsistent with control file` with hint `the backup is corrupted...` | Strong evidence that the restore backup is inconsistent, but not proof that the original source cluster's live data files were corrupt. | [[raw/postgres-12/src/backend/access/transam/xlog.c#StartupXLOG]] |
| 30% | `the standby was promoted during online backup` with hint `the backup being taken is corrupt and should not be used` | The online backup artifact is unsafe because promotion happened during the backup; it is not evidence that the live database contents were already corrupt. | [[raw/postgres-12/src/backend/replication/basebackup.c#sendDir]], [[raw/postgres-12/src/backend/access/transam/xlog.c#do_pg_stop_backup]] |

### Data-Directory Tool Signals In Checksum-Disabled Clusters

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 95% | `pg_control CRC value is incorrect` from `pg_checksums` | `pg_checksums` reads the control file before checking the mode and exits if its CRC is bad; this applies even when data checksums are disabled. | [[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#main]], [[raw/postgres-12/src/common/controldata_utils.c#get_controlfile]] |
| 90% | `could not read file "%s": read %d of %zu` for `global/pg_control` from control-data utilities | A frontend or backend control-file reader got a short `pg_control` file. | [[raw/postgres-12/src/common/controldata_utils.c#get_controlfile]] |
| 90% | `could not read block %u in file "%s": read %d of %d` from `pg_checksums --enable` | With checksums disabled, `pg_checksums --check` refuses to run, but `pg_checksums --enable` scans relation files and reports partial blocks before writing checksums. | [[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#scan_file]], [[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#main]] |
| 95% | `WARNING: Calculated CRC checksum does not match value stored in file...` from `pg_controldata` | `pg_controldata` detected a `pg_control` CRC mismatch and warns that the file may be corrupt or incompatible with the expected layout. | [[raw/postgres-12/src/bin/pg_controldata/pg_controldata.c#main]] |
| 90% | `WARNING: invalid WAL segment size... The file is corrupt...` from `pg_controldata` | `pg_controldata` found a WAL segment size in `pg_control` outside the valid power-of-two range. | [[raw/postgres-12/src/bin/pg_controldata/pg_controldata.c#main]] |
| 95% | `%s: control file appears to be corrupt` from `pg_ctl` | `pg_ctl` could not validate the control-file CRC while reading cluster state. | [[raw/postgres-12/src/bin/pg_ctl/pg_ctl.c#get_control_dbstate]] |
| 95% | `pg_control exists but has invalid CRC; proceed with caution` from `pg_resetwal` | `pg_resetwal` could read a same-version `pg_control`, but its CRC did not validate; the tool keeps the values while treating them as guessed. | [[raw/postgres-12/src/bin/pg_resetwal/pg_resetwal.c#ReadControlFile]] |
| 90% | `pg_control exists but is broken or wrong version; ignoring it` from `pg_resetwal` | `pg_resetwal` could open `pg_control`, but the file was too malformed or wrong-version for the normal read path. | [[raw/postgres-12/src/bin/pg_resetwal/pg_resetwal.c#ReadControlFile]] |
| 90% | `pg_control specifies invalid WAL segment size (%d byte[s]); proceed with caution` from `pg_resetwal` | `pg_resetwal` read `pg_control` but found an invalid WAL segment size. | [[raw/postgres-12/src/bin/pg_resetwal/pg_resetwal.c#ReadControlFile]] |

### Two-Phase, Replication, And Logical Decoding State

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 85% | `incorrect size of file "%s": %zu byte(s)` | Two-phase state file length is outside the valid bounds. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 85% | `incorrect alignment of CRC offset for file "%s"` | Two-phase state file length puts the stored CRC at an invalid alignment. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 90% | `invalid magic number stored in file "%s"` | Two-phase state file has the wrong magic number. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 85% | `invalid size stored in file "%s"` | Two-phase state file header length disagrees with the actual file size. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 95% | `calculated CRC checksum does not match value stored in file "%s"` | Two-phase state file CRC validation failed; this is not a data-page checksum. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ReadTwoPhaseFile]] |
| 90% | `corrupted two-phase state file for transaction %u` | Recovered two-phase file header transaction ID does not match the expected transaction. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ProcessTwoPhaseBuffer]] |
| 60% | `corrupted two-phase state in memory for transaction %u` | The same transaction-ID mismatch was found in memory rather than in a file. | [[raw/postgres-12/src/backend/access/transam/twophase.c#ProcessTwoPhaseBuffer]] |
| 80% | `could not read file "%s": read %d of %zu` from logical replication origin, replication slot, or snapbuild state restore | A persistent logical-replication state file was shorter than the fixed-size header or expected payload. | [[raw/postgres-12/src/backend/replication/logical/origin.c#StartupReplicationOrigin]], [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]], [[raw/postgres-12/src/backend/replication/logical/snapbuild.c#SnapBuildRestore]] |
| 75% | `replication checkpoint has wrong magic %u instead of %u` | Logical replication origin checkpoint file magic is wrong. | [[raw/postgres-12/src/backend/replication/logical/origin.c#StartupReplicationOrigin]] |
| 80% | `replication slot checkpoint has wrong checksum %u, expected %u` | Logical replication origin checkpoint CRC is wrong; this is independent of data-page checksums. | [[raw/postgres-12/src/backend/replication/logical/origin.c#StartupReplicationOrigin]] |
| 75% | `replication slot file "%s" has wrong magic number: %u instead of %u` | Replication slot state file magic is wrong. | [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]] |
| 70% | `replication slot file "%s" has unsupported version %u` | Replication slot state file version is unsupported for this build. | [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]] |
| 80% | `replication slot file "%s" has corrupted length %u` | Replication slot state file length field is not the expected on-disk size. | [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]] |
| 85% | `checksum mismatch for replication slot file "%s": is %u, should be %u` | Replication slot state file checksum failed; this is not a data-page checksum. | [[raw/postgres-12/src/backend/replication/slot.c#RestoreSlotFromDisk]] |
| 75% | `snapbuild state file "%s" has wrong magic number: %u instead of %u` | Logical decoding snapshot-builder state file magic is wrong. | [[raw/postgres-12/src/backend/replication/logical/snapbuild.c#SnapBuildRestore]] |
| 70% | `snapbuild state file "%s" has unsupported version: %u instead of %u` | Snapshot-builder state file version is unsupported for this build. | [[raw/postgres-12/src/backend/replication/logical/snapbuild.c#SnapBuildRestore]] |
| 85% | `checksum mismatch for snapbuild state file "%s": is %u, should be %u` | Snapshot-builder state file checksum failed; this is not a data-page checksum. | [[raw/postgres-12/src/backend/replication/logical/snapbuild.c#SnapBuildRestore]] |

### Relation Map And Auxiliary State

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 90% | `could not read file "%s": read %d of %zu` from relation mapping load | Relation mapping file had a short read while loading shared or per-database relation mappings. | [[raw/postgres-12/src/backend/utils/cache/relmapper.c#load_relmap_file]] |
| 95% | `relation mapping file "%s" contains invalid data` | Relation mapping file magic or mapping count is invalid. | [[raw/postgres-12/src/backend/utils/cache/relmapper.c#load_relmap_file]] |
| 95% | `relation mapping file "%s" contains incorrect checksum` | Relation mapping file CRC validation failed; this is not a data-page checksum. | [[raw/postgres-12/src/backend/utils/cache/relmapper.c#load_relmap_file]] |
| 35% | `corrupted statistics file "%s"` | The stats collector detected a malformed statistics file; PostgreSQL can discard/rebuild stats, so this is not strong evidence of table/index corruption. | [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_read_statsfiles]] |
| 25% | `database hash table corrupted during cleanup --- abort` | The stats collector's in-memory database hash was inconsistent during cleanup; this is serious backend state corruption, not direct persistent relation-file evidence. | [[raw/postgres-12/src/backend/postmaster/pgstat.c#pgstat_recv_dropdb]] |
| 30% | `autoprewarm block dump file is corrupted at line %d` | `pg_prewarm`'s autoprewarm dump file is malformed; it affects prewarm state, not table contents. | [[raw/postgres-12/contrib/pg_prewarm/autoprewarm.c#apw_load_buffers]] |
| 20% | `fixing corrupt FSM block %u, relation %u/%u/%u` | Free-space-map page contents were inconsistent and PostgreSQL is repairing the FSM page; FSM corruption can hurt space reuse but is not heap tuple corruption by itself. | [[raw/postgres-12/src/backend/storage/freespace/fsmpage.c#fsm_search_avail]] |

### Internal State Messages With Low Database-Corruption Confidence

| Confidence | Log entry | Explanation | Source |
|---:|---|---|---|
| 35% | `SMgrRelation hashtable corrupted` | Storage-manager in-memory hashtable state is inconsistent; serious backend state corruption, but not direct evidence of persistent relation-file corruption. | [[raw/postgres-12/src/backend/storage/smgr/smgr.c#smgrclose]] |
| 30% | `local buffer hash table corrupted` | Local buffer hash state is inconsistent. Temporary/local buffer state may be damaged, but persistent database contents are not proven corrupt. | [[raw/postgres-12/src/backend/storage/buffer/localbuf.c#LocalBufferAlloc]], [[raw/postgres-12/src/backend/storage/buffer/localbuf.c#DropRelFileNodeLocalBuffers]] |
| 35% | `shared buffer hash table corrupted` | Shared buffer lookup state is inconsistent. It is severe shared-memory corruption, but not itself a page checksum or on-disk layout failure. | [[raw/postgres-12/src/backend/storage/buffer/buf_table.c#BufTableDelete]] |
| 25% | `lock table corrupted` / `proclock table corrupted` / `locallock table corrupted` | Lock-manager tables are inconsistent; this can force backend or cluster failure, but it does not directly say stored data files are corrupt. | [[raw/postgres-12/src/backend/storage/lmgr/lock.c#LockAcquireExtended]], [[raw/postgres-12/src/backend/storage/lmgr/lock.c#CleanUpLock]], [[raw/postgres-12/src/backend/storage/lmgr/lock.c#RemoveLocalLock]] |
| 25% | `hash table "%s" corrupted` / `hash table corrupted` / `corrupted hashtable` | Generic dynamic hash table corruption; persistent data corruption depends on which in-memory hash table was affected. | [[raw/postgres-12/src/backend/utils/hash/dynahash.c#hash_corrupted]], [[raw/postgres-12/src/backend/utils/cache/relfilenodemap.c#RelidByRelfilenode]] |
| 20% | `doubly linked list is corrupted` | Generic in-memory list invariant failure, not direct on-disk evidence. | [[raw/postgres-12/src/backend/lib/ilist.c#dlist_check]] |
| 20% | `pendingOps corrupted` | Checkpointer pending-sync in-memory hash cleanup failed; this is not direct evidence of table/index bytes being corrupt. | [[raw/postgres-12/src/backend/storage/sync/sync.c#ProcessSyncRequests]] |
| 20% | `free page manager btree is corrupt` | Dynamic shared memory allocator metadata is corrupt; it is allocator state, not a PostgreSQL relation index. | [[raw/postgres-12/src/backend/utils/mmgr/freepage.c#FreePageManagerGetInternal]] |
| 25% | `dynamic shared memory control segment is corrupt` / `invalid magic number in dynamic shared memory segment` | DSM control/segment metadata is invalid. This points to shared-memory state, not table/index files. | [[raw/postgres-12/src/backend/storage/ipc/dsm.c#dsm_postmaster_startup]], [[raw/postgres-12/src/backend/access/transam/parallel.c#ParallelWorkerMain]] |
| 10% | `terminating connection because of crash of another server process` with detail `possibly corrupted shared memory` | The postmaster tells other backends to exit after a peer process crash because shared memory may be unsafe; it does not identify persistent database corruption. | [[raw/postgres-12/src/backend/tcop/postgres.c#quickdie]] |

### Enabled-Checksum-Only Messages Excluded From The Main Catalog

These messages are corruption signals in a checksum-enabled cluster, but they are not expected for a cluster that still has data checksums disabled:

| Confidence in this scope | Log entry | Why excluded | Source |
|---:|---|---|---|
| 0% | `page verification failed, calculated checksum %u but expected %u` | `PageIsVerified()` only computes the page checksum and emits this warning when `DataChecksumsEnabled()` is true. | [[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIsVerified]] |
| 0% | `checksum verification failed in file "%s", block %d: calculated %X but expected %X` / `further checksum verification failures...` / `file "%s" has a total of %d checksum verification failure(s)` / `%s total checksum verification failures` / `checksum verification failure during base backup` | Base backup only verifies data-page checksums when the cluster has data checksums enabled. | [[raw/postgres-12/src/backend/replication/basebackup.c#sendFile]], [[raw/postgres-12/src/backend/replication/basebackup.c#perform_base_backup]] |
| 0% | `checksum verification failed in file "%s", block %u: calculated checksum %X but block contains %X` from `pg_checksums --check` | `pg_checksums --check` refuses to run when `ControlFile->data_checksum_version == 0`; it reports `data checksums are not enabled in cluster` instead. | [[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#main]], [[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#scan_file]] |

## Context Reviewed

- Navigation and bookkeeping: `wiki/versions.md`, `wiki/index.md`, the last 20 `wiki/log.md` entries through `scripts/recent_log --limit 20`, and `wiki/v12/index.md`.
- Context pack: `.wiki-runtime/context/postgres-12/manifest.md`; `tree-L4.txt`; `include-deps.txt`; `compile_commands.json`; focused `PostgresMain` and `ExecutorRun` callgraphs; and targeted `scripts/source_deps --version 12` checks for storage, WAL reader, basebackup, TOAST, `pg_checksums`, and amcheck include context.
- Source search envelope: `scripts/source_lookup --version 12 --symbol ERRCODE_DATA_CORRUPTED --limit 300`, `scripts/source_lookup --version 12 --symbol ERRCODE_INDEX_CORRUPTED --limit 300`, targeted `scripts/source_lookup --version 12 --path ...` slices, and `rg` searches over `raw/postgres-12/src/backend`, `raw/postgres-12/contrib`, `raw/postgres-12/src/common`, `raw/postgres-12/src/bin/pg_checksums`, `raw/postgres-12/src/bin/pg_controldata`, `raw/postgres-12/src/bin/pg_ctl`, and `raw/postgres-12/src/bin/pg_resetwal`.
- Tests checked: checksum-disabled/enabled control-file behavior and relation-file scan failures in [[raw/postgres-12/src/bin/pg_checksums/t/002_actions.pl]], control-file warnings in [[raw/postgres-12/src/bin/pg_controldata/t/001_pg_controldata.pl]], `pg_resetwal` corrupt-control handling in [[raw/postgres-12/src/bin/pg_resetwal/t/002_corrupted.pl]], checksum-enabled basebackup behavior used only for exclusion evidence in [[raw/postgres-12/src/bin/pg_basebackup/t/010_pg_basebackup.pl]], amcheck regression coverage in [[raw/postgres-12/contrib/amcheck/expected/check_btree.out]], pageinspect normal-path coverage in [[raw/postgres-12/contrib/pageinspect/expected/page.out]], and invalid-page recovery coverage in [[raw/postgres-12/src/test/recovery/t/015_promotion_pages.pl]].

## Evidence Map

- Checksum-disabled boundary maps to `DataChecksumsEnabled()`, the internal `data_checksums` GUC, `PageIsVerified()`, basebackup checksum gating, and `pg_checksums` mode checks.
- Page, relation, TOAST, and large-object messages map to page verification, buffer reads, storage-manager reads, relation-storage copy, page layout checks, TOAST chunk/decompression checks, and large-object chunk validation.
- Heap and MVCC messages map to tuple freezing and HOT-chain index-build/validation paths.
- Index messages map to B-tree, hash, GiST, BRIN, amcheck, pgstattuple, and pageinspect source paths.
- WAL, control-file, and recovery messages map to WAL record/page validation, checkpoint/control-file loading, invalid-page tracking, and backup interruption checks.
- Tool-output messages map to `pg_checksums`, `pg_controldata`, `pg_ctl`, `pg_resetwal`, and shared control-data utility code.
- Replication-state messages map to two-phase state, logical replication origin state, replication slot state, and logical decoding snapbuild state restore paths.
- Low-confidence internal-state messages map to shared/local buffer, smgr, lock-manager, dynahash, ilist, pending sync, freepage, DSM, and post-crash shared-memory warning paths.

## Open Questions

No unresolved source-evidence gaps were found for the catalog entries above. The confidence percentages remain reviewer triage judgments, not PostgreSQL source-defined probabilities.

## Source References

- Source pin and context pack: [[raw/postgres-12/]], `.wiki-runtime/context/postgres-12/manifest.md`
- Context checks used for this review: `.wiki-runtime/context/postgres-12/include-deps.txt`, `.wiki-runtime/context/postgres-12/compile_commands.json`, and `scripts/source_deps --version 12`
- Source searches used for this review: `scripts/source_lookup --version 12 --symbol ...`, targeted `scripts/source_lookup --version 12 --path ...`, and `rg` over the scoped v12 source directories
