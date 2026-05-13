# Wiki Log

Append one entry after every scaffold change, version lifecycle event, ingest, trace, lint pass, or filed answer.

## [2026-05-10] scaffold | removed all operations

- Deleted `wiki/operations/` directory and its contents.
- Removed references to the operations page from `wiki/index.md`.

## [2026-05-13] fix v12 | avg_leaf_density_minimal_io_query — source verification and corrections

- Rewrote Approach C: replaced non-existent pageinspect functions (`getpage`, `btmetalevel`, `btpageitem`, `pagegetfree_space`) with real `bt_page_stats()` from the pageinspect contrib extension, which returns `free_size` and `max_avail` fields matching the pgstatindex formulas.
- Added `## Context Reviewed` and `## Evidence Map` sections required by AGENTS.md filing rules.
- Fixed typo: `minib_leaf_density` → `mini_leaf_density` in Open Questions.
- Clarified Approach B limitations: expanded error sources (stale reltuples, deep-tree overestimation, tuple size variance) and raised expected error from 10-20% to 15-30%.
- Fixed stale pageinspect reference in "How to Find Leaf Pages Without Scanning" section.

## [2026-05-13] cleanup | removed source-tool path references

- Removed wiki references to source-tool script paths from the global index, overview, version manifest, and version landing pages.
- Kept the source-navigation guidance focused on pinned raw checkouts and Graphify runtime artifacts.

## [2026-05-13] scaffold v12 | avg_leaf_density_minimal_io_query — sampling-based density estimation

- Created `wiki/v12/questions/avg_leaf_density_minimal_io_query.md` (unverified).
- Explained why pure SQL cannot compute leaf density (no page-level read functions in standard SQL).
- Provided ~80-line C extension using systematic sampling of leaf pages with BAS_BULKREAD strategy.
- Compared against pgstatindex full-scan approach from `contrib/pgstattuple/pgstatindex.c`.
- Added ASCII diagrams for 5 fragmentation scenarios (healthy, post-delete, localized fragmentation, post-VACUUM, custom fillfactor).
- Added 3 partial index scenarios explaining why partiality does not affect leaf page density.
- Cited source: pgstatindex.c, nbtree.h, bufpage.h, nbtpage.c.
- Updated `wiki/v12/index.md` with question reference.
