# Phase 6 Done: Maintenance Tooling

## Status

Done on 2026-04-30.

## Goal

Add small local tools that help the LLM and human maintainer keep the wiki healthy as it grows.

## Tooling Scope

Start with simple scripts. They should make wiki problems visible, not replace the LLM maintainer.

All tooling must run from the project root and store generated state inside this project directory. Durable helper scripts live in `scripts/`.

## Proposed Scripts

```text
scripts/
  wiki_lint
  source_lookup
  version_diff
  recent_log
```

## `scripts/wiki_lint`

Checks:

- Broken Obsidian links.
- Orphan pages.
- Pages without source references.
- Pages under `wiki/vNN/` without matching `version:` and `pinned_commit:`.
- Stale `pinned_commit:` values relative to `wiki/versions.md`.
- Question pages citing source from the wrong version checkout.
- Version landing pages missing links to existing version-local pages.
- `wiki/versions.md` coverage notes that disagree with actual pages.

## `scripts/source_lookup`

Purpose:

- Wrap `rg`, `git grep`, and `git log` for the selected PostgreSQL version.
- Default to the primary version from `wiki/versions.md`.
- Make source lookup easy for the agent.
- Use only source checkouts under `raw/postgres-NN/`.
- Use project-local indexes when available.

Example shape:

```bash
scripts/source_lookup --version 17 --symbol ExecutorRun
scripts/source_lookup --version 17 --path src/backend/executor/execMain.c
scripts/source_lookup --version 17 --log src/backend/executor/execMain.c
```

## `scripts/version_diff`

Purpose:

- Compare cited files or symbols across two PostgreSQL checkouts.
- Support active-version verification.
- Read only from `raw/postgres-NN/` checkouts inside this project.

Example shape:

```bash
scripts/version_diff --from 17 --to 16 --path src/backend/executor/execMain.c
```

## `scripts/recent_log`

Purpose:

- Show recent wiki activity.
- Help the agent quickly understand what changed recently.

Example shape:

```bash
scripts/recent_log --limit 20
```

## Implementation Order

1. Implement `recent_log` first because it is simple and useful.
2. Implement minimal `wiki_lint` for broken links and missing front matter.
3. Add source-reference checks to `wiki_lint`.
4. Implement `source_lookup`.
5. Implement `version_diff`.
6. Expand `wiki_lint` to check version pins and landing-page coverage.

## Runtime Storage Rules

- `scripts/wiki_lint` should write cache files, if any, under `.wiki-runtime/cache/wiki_lint/`.
- `scripts/source_lookup` should read indexes from `.wiki-runtime/indexes/` and write temporary output under `.wiki-runtime/tmp/`.
- `scripts/version_diff` should write temporary diffs under `.wiki-runtime/tmp/` if it needs files.
- ctags output should go under `.wiki-runtime/indexes/ctags/`.
- Search indexes should go under `.wiki-runtime/indexes/search/`.
- Tool logs should go under `.wiki-runtime/logs/`.
- Do not write generated state to home-directory caches or global tool directories.

## Local Model Guidance

These tools are especially important for the 16GB local model setup. They reduce context load by letting the agent ask narrow questions:

- "Find this symbol."
- "Show recent log entries."
- "Check whether this page has broken links."
- "Diff this cited file across two versions."

## Definition Of Done

- `scripts/recent_log` can show recent activity from `wiki/log.md`.
- `scripts/wiki_lint` catches at least broken links, missing front matter, and missing source references.
- `scripts/source_lookup` can search the primary PostgreSQL checkout.
- `scripts/version_diff` can compare one path across two checkouts.
- Generated indexes, caches, temporary files, and logs are written under `.wiki-runtime/`.
- The lint workflow in `AGENTS.md` references the scripts.
