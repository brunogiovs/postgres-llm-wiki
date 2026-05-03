# PostgreSQL Engine Wiki Agent Instructions

This repository is an LLM-maintained wiki for PostgreSQL engine internals. The agent writes and maintains the wiki; raw source material is treated as evidence.

## Read Before Writing

- Read `wiki/versions.md` first to identify supported PostgreSQL versions and the primary version.
- Read `wiki/index.md` before modifying or answering from the wiki.
- Read the last ~20 entries of `wiki/log.md` to understand recent activity.
- For version-specific work, read the relevant `wiki/vNN/index.md` before editing version-local pages.
- Search the PostgreSQL source tree before making any technical claim.

## Citation Discipline

- Cite source paths and symbols for every behavioral claim.
- Mandatory citation shape: `[[raw/postgres-NN/src/backend/executor/execMain.c#ExecutorRun]]` (replace NN with the page's version).
- For non-Markdown files you must include the full file extension (.c, .py, .java, etc.).
- Cite from the `raw/postgres-NN/` checkout matching the page's `version:`.
- Shared concept pages may cite version examples through `verified_against:`.
- Use the same citation format for all code references, function names, and symbols mentioned in the text.
- Code references may use aliases for compact display: `[[raw/postgres-NN/path/file.c#symbol|file.c#symbol]]`.
- If a claim is not backed by a source file, symbol, documentation page, commit, or saved design discussion, do not write it as fact.
- Put uncertainty under `## Open Questions` instead of guessing.

## Verification

Pages carry two distinct verification fields in front matter. They are not interchangeable.

- `verified:` — human-verified. Only a human reviewer may set, change, or remove this field. Agents must never write or modify it. Treat its presence and value as authoritative.
- `verified_by_agent:` — agent-verified. Agents may set or update this field after re-checking the page's claims against the pinned source. Format the value as `<agent-model> <ISO-8601-datetime-UTC>`, for example:

  ```yaml
  verified_by_agent: claude-opus-4-7 2026-05-03T14:30:00Z
  ```

  Use the exact model identifier the agent is running as, and a UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` form. Overwrite any prior `verified_by_agent:` value when re-verifying; do not accumulate history in front matter.

Rules for agents:

- Set `verified_by_agent:` only after a comprehensive review checking all claims and sources on the question, re-checking every behavioral claim on the page against the cited source paths in the matching `raw/postgres-NN/` checkout, and following all agent rules for the wiki.
- If verification fails for any claim, do not set `verified_by_agent:`. Either fix the claim, move it under `## Open Questions`, or leave the field absent.
- When creating new pages or reports (e.g., question pages under `wiki/vNN/questions/`), agents must set `verified: false` in front matter. Never change or remove a human-set `verified:`. Treat human-set values as authoritative.
- `verified:` and `verified_by_agent:` are independent. A page may have either, both, or neither.


- For question pages under `wiki/vNN/questions/`, front matter must use **exactly** this order:
  ```yaml
  type: question
  version: NN
  pinned_commit: abc123...
  verified: false
  verified_by_agent: model-name YYYY-MM-DDTHH:MM:SSZ
  ```
  Replace placeholders with actual values. Do not add extra fields like `filed`. Set `verified_by_agent` only after verifying claims.

## Version Awareness

- `wiki/versions.md` is the top-level version index and source pin manifest.
- Each supported version has a landing page at `wiki/vNN/index.md`.
- Default new ingests, traces, and answers to the primary version unless the user specifies another.
- If the user asks without naming a version, assume the primary version and state that assumption before answering.
- Never answer about one PostgreSQL version using citations from another version's checkout.
- Question pages are pinned to a single version. Filing the same question against another version creates a new question page.

## Wiki Structure

- Keep version-specific pages under `wiki/vNN/`.
- Keep genuinely cross-version concept theory under `wiki/shared/concepts/`.
- Use Obsidian-style links, such as `[[versions]]` and `[[v17/code-paths/simple-select-query]]`.
- Include the version segment for links into per-version directories.
- Prefer code-path pages over vague subsystem summaries.
- A page is born when the work justifies it. Do not create empty content stubs.
- A concept earns its own page when it is referenced from at least two other pages or repeatedly in conversation.

## Operating Mode

Operating rules:

- Trace one code path, subsystem slice, or question at a time.
- Prefer `rg`, `git grep`, and short source excerpts over loading entire directories into context.
- Do not ingest a large subsystem in one pass unless a stronger hosted model is being used.
- Treat generated pages as drafts until their source references are checked.
- Use active-version verification sparingly.
- Defer active-version verification explicitly on `wiki/vNN/index.md` when it exceeds the local context or latency budget.
- Escalate hard traces, such as planner internals, WAL, crash recovery, or MVCC visibility, when the local model cannot keep the call chain straight.
- Always use a Unicode/ASCII Tree for visual representation of directory trees.


## Bookkeeping

Do these after every meaningful wiki change:

- Update `wiki/index.md` whenever a page is created or substantially changed.
- Update `wiki/versions.md` whenever a supported version is added, removed, archived, re-pinned, or has a meaningful coverage change.
- Update the relevant `wiki/vNN/index.md` whenever version-local pages are created or substantially changed.
- Append an entry to `wiki/log.md` after each scaffold change, ingest, trace, lint pass, filed answer, or version lifecycle event.

Log entry prefix:

```md
## [YYYY-MM-DD] <kind> v<NN> | <subject>
```

For version-agnostic work:

```md
## [YYYY-MM-DD] <kind> | <subject>
```

## Core Workflows

### Add A Supported Version

1. Add the source checkout under `raw/postgres-NN/` using `scripts/source_update`.
2. Pin the checkout to an exact commit.
3. Add the version to `wiki/versions.md`.
4. Create `wiki/vNN/index.md`.
5. Create `wiki/vNN/subsystems/`, `wiki/vNN/concepts/`, `wiki/vNN/code-paths/`, `wiki/vNN/files/`, and `wiki/vNN/questions/`.
6. Update `wiki/index.md`.
7. Append to `wiki/log.md`.

### Ingest A Subsystem

1. Read `wiki/versions.md` and select the primary version unless the user specified another.
2. Read `wiki/vNN/index.md`.
3. Search relevant source files under `raw/postgres-NN/`.
4. Create or update `wiki/vNN/subsystems/<name>.md`.
5. Create concept pages only when justified by repeated use.
6. Update `wiki/vNN/index.md`, `wiki/index.md`, and `wiki/log.md`.

### Trace A Code Path

1. Start from the target version's pinned source checkout.
2. Use source search to follow calls through the engine.
3. Record the flow under `wiki/vNN/code-paths/`.
4. Link related subsystem and concept pages.
5. Mark uncertain behavior under `Open Questions`.
6. Update indexes and log.

### Answer And File

1. Assume the primary version unless the user specifies another.
2. Search `wiki/versions.md`, the relevant version landing page, and `wiki/index.md`.
3. Search source evidence under `raw/postgres-NN/`.
4. Answer with citations.
5. File durable answers as question pages or fold them into existing pages.
6. Update indexes and log.

### Report Generation And Review

A report here means any answer or wiki page produced from a user prompt — most commonly a question page under `wiki/vNN/questions/` with a `## Question` section.

During generation or review, when the user asks for a modification, clarification, narrowing, broadening, or follow-up, treat that ask as part of the question itself, not just guidance for the answer.

- Fold the user's modification ask into the report's `## Question` section before updating the answer body.
- Preserve the original question; extend or refine it in place so the section reflects the full scope of what is being asked.
- Rewrite for coherence rather than appending raw transcript fragments — the `## Question` section should read as a single, current statement of the question.
- Only after the `## Question` section is updated, revise the answer, citations, and any downstream sections to match.
- If the page has no `## Question` section yet (for example a freshly generated draft), add one and seed it from the user's original prompt plus the modification ask.
- This applies to every review round: each new ask is merged into the same `## Question` section, not stacked as a changelog.

### Lint The Wiki

Check for:

- Broken Obsidian links.
- Orphan pages.
- Pages without source references.
- Version-local pages with missing or stale `version:` / `pinned_commit:`.
- Shared concept pages with stale `verified_against:`.
- Pages citing source from the wrong version checkout.
- Version landing pages missing links to existing version-local pages.
- `wiki/versions.md` coverage notes that disagree with actual pages.
- Invalid or malformed `verified:` / `verified_by_agent:` fields.
- New reports and question pages missing `verified: false`.
- Managed pages missing verification fields (both `verified:` and `verified_by_agent:` absent).
- Question pages under `wiki/vNN/questions/` with front matter not in exact order: `type`, `version`, `pinned_commit`, `verified`, `verified_by_agent`.

Use the project-local scripts first:

```bash
scripts/recent_log --limit 20
scripts/wiki_lint
scripts/source_lookup --symbol ExecutorRun
scripts/source_lookup --path src/backend/executor/execMain.c
scripts/version_diff --from 18 --to 17 --path src/backend/executor/execMain.c
scripts/source_update --list
scripts/source_update --version 18
scripts/wiki_agent status
```

`scripts/source_lookup` defaults to the primary version in `wiki/versions.md`. `scripts/version_diff` requires both source checkouts to exist under `raw/postgres-NN/`. `scripts/source_update` clones or updates a checkout to the commit pinned in `wiki/versions.md`; pass `--branch` and `--commit` to override.
