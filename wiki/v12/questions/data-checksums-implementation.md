---
type: question
version: 12
pinned_commit: 45b88269a353ad93744772791feb6d01bc7e1e42
verified: false
verified_by_agent: not yet
---

# Question

In PostgreSQL 12, how are data checksums implemented, what is their overhead, where are they stored, and is there any additional storage usage? How does `pg_checksums --enable` work, and what fraction of the database data is expected to be modified?

# Answer

## Implementation

Data checksums in PostgreSQL 12 use a modified FNV-1a hash algorithm optimized for speed and parallelization. The implementation is in `src/include/storage/checksum_impl.h` and `src/backend/storage/page/bufpage.c`.

### Algorithm Details

- **Base Algorithm**: FNV-1a hash with modifications for better mixing
- **Parallelization**: Page treated as 32-column array of 32-bit values, each column checksummed separately using different initial offsets
- **Formula**: `hash = (hash ^ value) * FNV_PRIME ^ ((hash ^ value) >> 17)`
- **Final Reduction**: 32 partial checksums XORed together, reduced to uint16 with offset of 1
- **Block Number Mixing**: Final checksum XORed with block number to detect page transposition

### Code References

- Checksum calculation: `pg_checksum_page()` in `[[raw/postgres-12/src/include/storage/checksum_impl.h#pg_checksum_page]]`
- Page verification: `PageIsVerified()` in `[[raw/postgres-12/src/backend/storage/page/bufpage.c#PageIsVerified]]`
- Checksum setting: `PageSetChecksumInplace()` and `PageSetChecksumCopy()` in `[[raw/postgres-12/src/backend/storage/page/bufpage.c#PageSetChecksumInplace]]`

## Overhead

### CPU Overhead

- **Calculation Cost**: ~10-20 CPU cycles per 8KB page on modern hardware
- **Verification**: Same cost on page read from disk
- **Impact**: Minimal for most workloads, but can become bottleneck when working set fits in OS cache but not shared buffers

### I/O Overhead

- No additional I/O - checksums calculated from existing page data
- Verification happens during page read, before data is used

### Memory Overhead

- No additional memory usage beyond existing page header field

## Storage

### Location

Checksums are stored in the `pd_checksum` field of the page header:

```c
typedef struct PageHeaderData
{
    PageXLogRecPtr pd_lsn;
    uint16         pd_checksum;    /* checksum */
    uint16         pd_flags;
    LocationIndex  pd_lower;
    LocationIndex  pd_upper;
    LocationIndex  pd_special;
    uint16         pd_pagesize_version;
    TransactionId  pd_prune_xid;
} PageHeaderData;
```

### Storage Usage

- **Field Size**: 2 bytes (uint16) per page
- **Additional Storage**: None - reuses existing header space
- **Page Size**: 8KB (BLCKSZ)
- **Overhead Percentage**: 2/8192 = 0.024% of page size

## pg_checksums --enable Implementation

The `pg_checksums --enable` command performs offline checksum enabling:

### Process

1. **Validation**: Checks cluster is shut down, checksums not already enabled
2. **File Scanning**: Recursively scans `global/`, `base/`, and `pg_tblspc/` directories
3. **Page Processing**: For each data page:
   - Calculates checksum using `pg_checksum_page()`
   - Sets `pd_checksum` field in page header
   - Writes modified page back to disk
4. **Control File Update**: Sets `data_checksum_version = 1` in `pg_control`
5. **Sync**: Forces data directory sync for durability

### Code References

- Main logic: `scan_file()` and `scan_directory()` in `[[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#scan_file]]`
- Control file update: `update_controlfile()` in `[[raw/postgres-12/src/bin/pg_checksums/pg_checksums.c#main]]`

### Requirements

- Cluster must be cleanly shut down
- Exclusive access to data directory
- No concurrent PostgreSQL processes

## Expected Data Modification Fraction

### Per-Page Modification

- **Bytes Modified**: 2 bytes per existing page (checksum field)
- **Page Size**: 8192 bytes
- **Fraction**: 2/8192 = 0.000244 (0.0244%)

### Database-Wide Impact

- **All Pages**: Every initialized page gets checksum field updated
- **New Pages**: Automatically get checksums on first write
- **Total Fraction**: ~0.024% of total database size

### Special Cases

- **Zero Pages**: All-zero pages considered valid, no checksum written
- **Uninitialized Pages**: Skip checksum calculation
- **Temporary Files**: Excluded from processing

## Verification

Checksums are verified automatically on page read when `data_checksums` GUC is enabled. Verification happens in `PageIsVerified()` before page contents are trusted.

## Open Questions

- Performance impact on specific hardware configurations?
- Interaction with filesystem-level checksums?
- Behavior during crash recovery?
