# Phase 2 Done: Bootstrap Supported Versions

## Status

Done on 2026-04-30.

## Goal

Add one or more PostgreSQL major versions to the wiki, each with a pinned source checkout, generated source-context pack, and version-local landing page.

## Recommended MVP

Start with one primary version only.

```text
primary: latest chosen PostgreSQL stable branch
active: none until the first source-backed pages are useful
legacy: none
```

Add active or legacy versions later when there is a real need to compare behavior across versions.

## Inputs

For each version:

- PostgreSQL major version number, such as `17`
- Branch name, such as `REL_17_STABLE`
- Exact pinned commit hash
- Status: `primary`, `active`, or `legacy`

## Create Files and Directories

For version `NN`:

```text
raw/
  postgres-NN/

wiki/
  vNN/
    index.md
    questions/              # created only when filed answers need it

.wiki-runtime/
  context/
    postgres-NN/
      manifest.md
```

## Tasks

1. Add the PostgreSQL source checkout under `raw/postgres-NN/` inside this project directory.
2. Pin it to the chosen commit.
3. Update `wiki/versions.md` with the version row.
4. Create `wiki/vNN/index.md`.
5. Generate `.wiki-runtime/context/postgres-NN/` with `scripts/source_context`.
6. Create `wiki/vNN/questions/` only when a filed answer needs it.
7. If this is the primary version, ensure no other version is marked `primary`.
8. If adding an active version after pages already exist, perform an active-version verification pass.
9. Update `wiki/index.md`.
10. Append an `add-version` or `context` entry to `wiki/log.md`.

## Project-Local Dependency Rules

- Do not point the wiki at a PostgreSQL checkout outside this project.
- Do not rely on a global source index for the checkout.
- Store any generated indexes for this version under `.wiki-runtime/indexes/`.
- Store temporary clone/download files under `.wiki-runtime/tmp/`.
- Store logs from checkout or indexing operations under `.wiki-runtime/logs/`.
- If the source checkout is too large to track in git, keep it untracked, but keep it physically inside `raw/postgres-NN/`.

## Required `wiki/vNN/index.md` Shape

```md
# PostgreSQL NN

## Source Pin

- Branch: `REL_NN_STABLE`
- Commit: `COMMIT_HASH`
- Status: `primary`

## Coverage

Generated source-context pack: `.wiki-runtime/context/postgres-NN/manifest.md`

## Project Context

- Manifest: `.wiki-runtime/context/postgres-NN/manifest.md`
- Generated artifacts:
- Deferred artifacts:

## Questions

## Open Questions
```

## Active-Version Verification Rules

When adding an active version after source-backed pages already exist:

- Do not mark a page verified just because one cited file is unchanged.
- Check relevant symbols, headers, callees, macros, and nearby control flow.
- Create a `wiki/vNN/...` page only after checking that version's source.
- If the check is too expensive for the local model, record it as an Open Question on `wiki/vNN/index.md`.

## Definition Of Done

- `raw/postgres-NN/` exists and is pinned.
- `.wiki-runtime/context/postgres-NN/manifest.md` exists or a deferral is recorded.
- `wiki/versions.md` links to `[[vNN/index]]`.
- `wiki/vNN/index.md` exists and records the source pin.
- Version-local question directory exists only when durable filed answers need it.
- `wiki/log.md` records the version addition.
